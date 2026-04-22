from cdk_linter.core.cfn.cfn_resource import CfnResource
from cdk_linter.core.cfn.resource_type import ResourceType


class ResourceIndex:
    def __init__(self):
        self.by_id: dict[str, CfnResource] = {}
        self.by_type: dict[ResourceType, list[CfnResource]] = {}

    def add(self, resource: CfnResource):
        self.by_id[resource.id] = resource
        self.by_type.setdefault(resource.type, []).append(resource)

    def get_by_id(self, id: str) -> CfnResource:
        return self.by_id.get(id, None)

    def get_by_type(self, type: ResourceType) -> list[CfnResource]:
        return self.by_type.get(type, [])

    def __repr__(self) -> str:
        id_and_type = "\n".join(
            f"  {resource.id}: {resource.type.name}" for resource in self.by_id.values()
        )
        return f"ResourceIndex(\n{id_and_type}\n)"
