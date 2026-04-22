import json

from cdk_linter.core.cfn.cfn_resource import CfnResource
from cdk_linter.core.cfn.resource_graph import ResourceGraph
from cdk_linter.core.cfn.resource_index import ResourceIndex
from cdk_linter.core.cfn.resource_type import ResourceType


class CfnTemplateParser:
    def __init__(self) -> None:
        self._resource_index = ResourceIndex()
        self._resource_graph: ResourceGraph = None
        self._supported_types = {t.value for t in ResourceType}

    def parse(self, path: str):
        with open(path, 'r') as f:
            data = json.load(f)
        resources = data["Resources"]
        for id, body in resources.items():
            type_str = body["Type"]
            if type_str not in self._supported_types:
                continue

            type = ResourceType(type_str)
            resource = CfnResource(id=id, type=type, properties=body["Properties"])
            self._resource_index.add(resource)

    def resource_index(self) -> ResourceIndex:
        if not self._resource_index:
            raise ValueError("no CFN template has been parsed yet")
        return self._resource_index

    def resource_graph(self) -> ResourceGraph:
        if not self._resource_graph:
            raise ValueError("no CFN template has been parsed yet")
        return self._resource_graph
