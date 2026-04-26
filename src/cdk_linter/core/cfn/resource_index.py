from cdk_linter.core.cfn.cfn_resource import CfnResource
from cdk_linter.core.cfn.resource_type import ResourceType


class ResourceIndex:
    def __init__(self):
        self._by_id: dict[str, CfnResource] = {}
        self._by_type: dict[ResourceType, list[CfnResource]] = {}

    def add(self, resource: CfnResource):
        self._by_id[resource.id] = resource
        self._by_type.setdefault(resource.type, []).append(resource)

    def get_resource_by_id(self, id: str) -> CfnResource:
        return self._by_id.get(id, None)

    def get_resources_by_type(self, type: ResourceType) -> list[CfnResource]:
        return self._by_type.get(type, [])

    def get_all_resources(self) -> list[CfnResource]:
        return self._by_id.values()

    def __repr__(self) -> str:
        id_and_type = "\n".join(
            f"  {resource.id}: {resource.type.name}" for resource in self._by_id.values()
        )
        return f"ResourceIndex(\n{id_and_type}\n)"
