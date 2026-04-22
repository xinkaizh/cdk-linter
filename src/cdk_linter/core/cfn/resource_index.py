from cdk_linter.core.cfn.cfn_resource import CfnResource
from cdk_linter.core.cfn.resource_type import ResourceType


class ResourceIndex:
    def __init__(self, resources: dict[str, CfnResource]):
        self.by_id = resources
        self.by_type: dict[str, list[CfnResource]] = {}
        for resource in resources.values():
            self.by_type.setdefault(resource.resource_type, []).append(resource)
    
    def get_by_id(self, id: str) -> CfnResource:
        return self.by_id.get(id, None)

    def get_by_type(self, type: ResourceType) -> list[CfnResource]:
        return self.by_type.get(type, [])
