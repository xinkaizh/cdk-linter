from cdk_linter.core.cfn.cfn_resource import CfnResource
from cdk_linter.core.cfn.resource_type import ResourceType


class ResourceIndex:
    def __init__(self):
        self._by_id: dict[str, CfnResource] = {}
        self._by_type: dict[ResourceType, list[CfnResource]] = {}

    def add(self, resource: CfnResource):
        self._by_id[resource.id] = resource
        self._by_type.setdefault(resource.type, []).append(resource)

    def get_resource_by_id(self, id: str) -> CfnResource | None:
        return self._by_id.get(id, None)

    def get_resources_by_type(self, type: ResourceType) -> list[CfnResource]:
        return self._by_type.get(type, [])

    def find_resource_by_prefix(
        self,
        id_prefix: str,
        include_types: list[ResourceType] = [],
        exclude_types: list[ResourceType] = [],
    ) -> CfnResource | None:
        if include_types and exclude_types:
            raise ValueError("Only allowed to specify either include_types or exclude_types")
        for k, v in self._by_id.items():
            if k.startswith(id_prefix):
                if include_types and v.type in include_types:
                    return v
                if exclude_types and v.type not in exclude_types:
                    return v
        return None

    def get_all_resources(self) -> list[CfnResource]:
        return self._by_id.values()

    def __repr__(self) -> str:
        id_and_type = "\n".join(
            f"  {resource.id}: {resource.type.name}" for resource in self._by_id.values()
        )
        return f"ResourceIndex(\n{id_and_type}\n)"
