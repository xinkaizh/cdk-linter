import json
import logging
from typing import Any

from cdk_linter.core.cfn.cfn_resource import CfnResource
from cdk_linter.core.cfn.resource_graph import GraphEdgeType, ResourceGraph
from cdk_linter.core.cfn.resource_index import ResourceIndex
from cdk_linter.core.cfn.resource_type import ResourceType

logger = logging.getLogger(__name__)


class CfnTemplateParser:
    def __init__(self) -> None:
        self._resource_index = ResourceIndex()
        self._resource_graph = ResourceGraph()
        self._supported_types = {t.value for t in ResourceType}

    def parse(self, path: str):
        with open(path, 'r') as f:
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

        # build up connections in dependency graph
        for res in self._resource_index.get_all_resources():
            match res.type:
                case ResourceType.POLICY:
                    self._handle_iam_policy(res)
                case ResourceType.LAMBDA:
                    self._handle_lambda_function(res)
                case _:
                    logger.warning(f"{res.id}: handling of {res.type.name} hasn't been implemented")

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
                type=GraphEdgeType.ROLE_CONTAINS_POLICY
            )

        # add policy -> allowed_resource edges:
        # TODO

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
            type=GraphEdgeType.LAMBDA_EXECUTION_ROLE
        )        
