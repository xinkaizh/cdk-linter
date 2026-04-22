import json

from cdk_linter.core.cfn.resource_graph import ResourceGraph
from cdk_linter.core.cfn.resource_index import ResourceIndex


class CfnTemplateParser:
    def __init__(self) -> None:
        self._resource_index: ResourceIndex = None
        self._resource_graph: ResourceGraph = None

    def parse(self, path: str):
        with open(path, 'r') as f:
            data = json.load(f)
        resources = data["Resources"]
        for id, body in resources.items():
            type = body["Type"]
            print(type)

    def resource_index(self) -> ResourceIndex:
        if not self._resource_index:
            raise ValueError("no CFN template has been parsed yet")
        return self._resource_index

    def resource_graph(self) -> ResourceGraph:
        if not self._resource_graph:
            raise ValueError("no CFN template has been parsed yet")
        return self._resource_graph
