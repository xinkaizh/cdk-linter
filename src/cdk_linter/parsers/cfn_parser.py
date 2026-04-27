import json
import logging
from pathlib import Path
from typing import Any

from cdk_linter.core.cfn.cfn_resource import CfnResource
from cdk_linter.core.cfn.resource_graph import GraphEdgeType, ResourceGraph
from cdk_linter.core.cfn.resource_index import ResourceIndex
from cdk_linter.core.cfn.resource_type import ResourceType

logger = logging.getLogger(__name__)

"""
For simplicity, we currently don't support:

- hardcoded ARN values
- referencing parameter values
"""


class CfnParser:
    def __init__(self) -> None:
        self._resource_index = ResourceIndex()
        self._resource_graph = ResourceGraph()
        self._supported_types = {t.value for t in ResourceType}

    def parse(self, path: str | Path):
        with open(path, "r") as f:
            data = json.load(f)
        resources = data["Resources"]

        # add all supported resources to both index and dependency graph
        for id, body in resources.items():
            type_str = body["Type"]
            if type_str not in self._supported_types:
                continue
            type = ResourceType(type_str)
            resource = CfnResource(id=id, type=type, properties=body["Properties"])
            self._resource_index.add(resource)
            self._resource_graph.add_resource(resource)
        # Treat Resource: "*" as a real graph target so IAM rules can flag it
        # instead of losing the statement during parsing.
        wildcard_resource = CfnResource(id="*", type=ResourceType.ALL)
        self._resource_index.add(wildcard_resource)
        self._resource_graph.add_resource(wildcard_resource)

        # build up connections in dependency graph
        for res in self._resource_index.get_all_resources():
            match res.type:
                case ResourceType.POLICY:
                    self._handle_iam_policy(res)
                case ResourceType.LAMBDA:
                    self._handle_lambda_function(res)
                case (
                    ResourceType.ALL
                    | ResourceType.DDB
                    | ResourceType.SQS
                    | ResourceType.S3
                    | ResourceType.ROLE
                ):
                    pass  # no-op for now

    def get_resource_index(self) -> ResourceIndex:
        if not self._resource_index:
            raise ValueError("no CFN template has been parsed yet")
        return self._resource_index

    def get_resource_graph(self) -> ResourceGraph:
        if not self._resource_graph:
            raise ValueError("no CFN template has been parsed yet")
        return self._resource_graph

    def _handle_iam_policy(self, policy_resource: CfnResource):
        roles = policy_resource.properties.get("Roles")
        if not roles:
            logger.warning(f"IAM Policy {policy_resource.id} isn't attached to any Roles")

        # add role -> policy edges:
        for role in roles:
            role_id = role["Ref"]
            role_resource = self._resource_index.get_resource_by_id(role_id)
            self._resource_graph.connect_resources(
                source=role_resource,
                destination=policy_resource,
                type=GraphEdgeType.ROLE_CONTAINS_POLICY,
            )

        # add policy -> allowed_resource edges:
        statements = policy_resource.properties["PolicyDocument"]["Statement"]
        for statement in statements:
            action: str | list[str] = statement["Action"]
            effect: str = statement["Effect"]
            resource: str | list | dict = statement["Resource"]

            if effect != "Allow":
                logger.warning(f"Ignored unsupported policy effect: {effect}")
                continue

            # normalize action and resource
            if isinstance(action, str):
                action = [action]
            if isinstance(resource, str):
                if resource != "*":
                    logger.warning(f"Ignored unsupported policy resource format: {resource}")
                    continue
                # Keep the wildcard in the same reference-shaped flow as other
                # resources so edge creation can stay simple below.
                resource = [{"Ref": "*"}]
            if isinstance(resource, dict):
                resource = [resource]

            for res in resource:
                if res == "*":
                    rid = "*"
                elif isinstance(res, dict) and "Fn::GetAtt" in res:
                    rid = res["Fn::GetAtt"][0]
                elif isinstance(res, dict) and res.get("Ref") == "*":
                    rid = "*"
                else:
                    logger.warning(f"Ignored unsupported way for resource reference {res}")
                    continue
                self._resource_graph.connect_resources(
                    source=policy_resource,
                    destination=self._resource_index.get_resource_by_id(rid),
                    type=GraphEdgeType.POLICY_ALLOWs_ACTION,
                    metadata={"actions": action},
                )

    def _handle_lambda_function(self, lambda_resource: CfnResource):
        def _extract_id(data: Any):
            # hardcoded ARN - e.g., "arn:aws:iam::123456789012:role/MyRole"
            if isinstance(data, str):
                raise NotImplementedError("Don't support hardcoded ARN for now")
            # GetAtt function - e.g., { "Fn::GetAtt": ["<ID>", "Arn"] }
            elif isinstance(data, dict) and "Fn::GetAtt" in data:
                return data["Fn::GetAtt"][0]
            # Ref to ID - e.g., { "Ref": "<ID>" }
            elif isinstance(data, dict) and "Ref" in data:
                raise NotImplementedError("Don't support referencing parameter for now")
            else:
                raise NotImplementedError("Unknown way to specify execution role")

        execution_role = lambda_resource.properties["Role"]
        role_id = _extract_id(execution_role)
        role_resource = self._resource_index.get_resource_by_id(role_id)
        self._resource_graph.connect_resources(
            source=lambda_resource,
            destination=role_resource,
            type=GraphEdgeType.LAMBDA_EXECUTION_ROLE,
        )
