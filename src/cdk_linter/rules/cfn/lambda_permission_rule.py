from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import override

from cdk_linter.core.cfn.cfn_resource import CfnResource
from cdk_linter.core.cfn.resource_graph import GraphEdgeType, GraphNode, ResourceGraph
from cdk_linter.core.cfn.resource_index import ResourceIndex
from cdk_linter.core.cfn.resource_type import ResourceType
from cdk_linter.core.diagnostic import Diagnostic, DiagnosticSeverity
from cdk_linter.rules.rule import CfnRule


@dataclass
class PermissionSpec:
    lambda_function_id: str
    target_id: str
    access: str

    def __repr__(self) -> str:
        return f"{self.lambda_function_id} {self.access} {self.target_id}"


class LambdaPermissionRule(CfnRule):
    description = "Checks if lambda function has correct IAM permission"

    # IAM actions are very granular. Here we define some commonly used actions for
    # read/write/delete operations. They are not meant to be comprehensive. Users
    # may need more permissions than what's defined below.
    COMMON_MAPPING = {
        "r": {
            ResourceType.DDB: ["dynamodb:GetItem", "dynamodb:Query"],
            ResourceType.S3: ["s3:GetObject"],
            ResourceType.SQS: ["sqs:ReceiveMessage"],
        },
        "w": {
            ResourceType.DDB: ["dynamodb:PutItem", "dynamodb:UpdateItem"],
            ResourceType.S3: ["s3:PutObject"],
            ResourceType.SQS: ["sqs:SendMessage"],
        },
        "d": {
            ResourceType.DDB: ["dynamodb:DeleteItem"],
            ResourceType.S3: ["s3:DeleteObject"],
            ResourceType.SQS: ["sqs:DeleteMessage"],
        },
    }

    def prime(self, spec_path: str | Path):
        self.specs: list[PermissionSpec] = []

        with open(spec_path, "r") as f:
            spec_str = f.read()

        lines = [line.strip() for line in spec_str.strip().splitlines()]
        for line in lines:
            if not line:
                continue
            parts = line.split()
            if len(parts) != 3:
                continue
            lambda_function_id = parts[0]
            accesses = parts[1].split(",")
            target_ids = parts[2].split(",")
            for target_id in target_ids:
                for access in accesses:
                    spec = PermissionSpec(lambda_function_id, target_id, access)
                    self.specs.append(spec)

    @override
    def check(self, graph: ResourceGraph, index: ResourceIndex) -> list[Diagnostic]:
        if not hasattr(self, "specs"):
            raise RuntimeError("Must call prime() before calling check()")

        diagnostics = []
        expected_permissions: dict[tuple[str, str], set[str]] = {}
        for spec in self.specs:
            lambda_resource = index.find_resource_by_prefix(
                spec.lambda_function_id, include_types=[ResourceType.LAMBDA]
            )
            target_resource = index.find_resource_by_prefix(
                spec.target_id, exclude_types=[ResourceType.ROLE, ResourceType.POLICY]
            )
            access = spec.access

            if lambda_resource is None:
                diagnostics.append(
                    Diagnostic(message=f"Lambda function {spec.lambda_function_id} is not defined")
                )
                continue

            if target_resource is None:
                diagnostics.append(
                    Diagnostic(message=f"Target resource {spec.target_id} is not defined")
                )
                continue

            # Save the actions implied by spec.txt so we can later spot grants
            # that go beyond what the user declared.
            expected_permissions.setdefault((lambda_resource.id, target_resource.id), set()).update(
                self._get_required_actions(target_resource, access)
            )

            # find execution role among all outgoing edges
            role = self._find_execution_role(graph, lambda_resource)

            # checks if execution role offers enough permission
            if not self._check_execution_role(role, target_resource, access):
                missing_permission = self._form_missing_permission(target_resource, access)
                message = f"Lambda function {spec.lambda_function_id} lacks {missing_permission} to resource {spec.target_id}"
                diagnostics.append(Diagnostic(message=message))
        diagnostics.extend(self._check_extra_permissions(graph, index, expected_permissions))
        return diagnostics

    def _check_execution_role(self, role: GraphNode, target_resource: CfnResource, access: str):
        target_id = target_resource.id
        required_actions = self._get_required_actions(target_resource, access)

        if isinstance(required_actions, str):
            required_actions = [required_actions]

        policy_edges = role.outgoing_edges
        for policy_edge in policy_edges:
            policy = policy_edge.destination
            allowed_resources_edges = policy.outgoing_edges

            for allowed_resources_edge in allowed_resources_edges:
                allowed_resource = allowed_resources_edge.destination

                if allowed_resource.resource.id != target_id:
                    continue

                allowed_actions = allowed_resources_edge.metadata["actions"]

                if all(
                    any(
                        fnmatchcase(required_action, allowed_action)
                        for allowed_action in allowed_actions
                    )
                    for required_action in required_actions
                ):
                    return True
        return False

    def _check_extra_permissions(
        self,
        graph: ResourceGraph,
        index: ResourceIndex,
        expected_permissions: dict[tuple[str, str], set[str]],
    ) -> list[Diagnostic]:
        # Collect by Lambda/resource first. one grouped diagnostic is easier to
        # read than one line per IAM action.
        extra_permissions: dict[tuple[str, str], set[str]] = {}
        wildcard_permissions: dict[tuple[str, str], set[str]] = {}
        for lambda_resource in index.get_resources_by_type(ResourceType.LAMBDA):
            role = self._find_execution_role(graph, lambda_resource)
            policy_edges = role.outgoing_edges
            for policy_edge in policy_edges:
                policy = policy_edge.destination
                allowed_resources_edges = policy.outgoing_edges

                for allowed_resources_edge in allowed_resources_edges:
                    allowed_resource = allowed_resources_edge.destination.resource
                    expected_actions = expected_permissions.get(
                        (lambda_resource.id, allowed_resource.id), set()
                    )

                    for allowed_action in allowed_resources_edge.metadata["actions"]:
                        # Wildcards are broader than normal extra permissions,
                        # so keep them separate and report them as critical.
                        if self._is_wildcard_permission(allowed_action, allowed_resource):
                            wildcard_permissions.setdefault(
                                (lambda_resource.id, allowed_resource.id), set()
                            ).add(allowed_action)
                            continue

                        if self._is_expected_action(allowed_action, expected_actions):
                            continue

                        extra_permissions.setdefault(
                            (lambda_resource.id, allowed_resource.id), set()
                        ).add(allowed_action)

        diagnostics = []
        for (lambda_id, resource_id), actions in wildcard_permissions.items():
            actions_str = ", ".join(sorted(actions))
            message = (
                f"Lambda function {lambda_id} has wildcard IAM permission(s) "
                f"to resource {resource_id}: {actions_str}"
            )
            diagnostics.append(Diagnostic(message=message, severity=DiagnosticSeverity.CRITICAL))

        for (lambda_id, resource_id), actions in extra_permissions.items():
            actions_str = ", ".join(sorted(actions))
            message = (
                f"Lambda function {lambda_id} has {len(actions)} extra IAM permission(s) "
                f"to resource {resource_id}: {actions_str}"
            )
            diagnostics.append(Diagnostic(message=message, severity=DiagnosticSeverity.WARNING))
        return diagnostics

    def _find_execution_role(self, graph: ResourceGraph, lambda_resource: CfnResource) -> GraphNode:
        edges = graph.get_node_by_rid(lambda_resource.id).outgoing_edges
        for edge in edges:
            if getattr(edge, "type", None) == GraphEdgeType.LAMBDA_EXECUTION_ROLE:
                return edge.destination
        raise RuntimeError("Lambda function has no execution role")

    def _get_required_actions(self, target_resource: CfnResource, access: str) -> list[str]:
        return self.COMMON_MAPPING[access][target_resource.type]

    def _is_expected_action(self, allowed_action: str, expected_actions: set[str]) -> bool:
        return any(
            fnmatchcase(expected_action, allowed_action) for expected_action in expected_actions
        )

    def _is_wildcard_permission(self, allowed_action: str, allowed_resource: CfnResource) -> bool:
        return "*" in allowed_action or allowed_resource.type == ResourceType.ALL

    def _form_missing_permission(self, target_resource: CfnResource, access: str) -> str:
        required_actions = self._get_required_actions(target_resource, access)
        required_actions_str = ", ".join(required_actions)
        match access:
            case "r":
                return f"IAM read permission (e.g., {required_actions_str})"
            case "w":
                return f"IAM write permission (e.g., {required_actions_str})"
            case "d":
                return f"IAM delete permission (e.g., {required_actions_str})"
