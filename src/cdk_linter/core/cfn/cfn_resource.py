from dataclasses import dataclass, field
from typing import Any

from cdk_linter.core.cfn.resource_type import ResourceType


@dataclass
class CfnResource:
    id: str # logical ID
    type: ResourceType
    properties: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            "CfnResource(\n"
            f"  id={self.id!r},\n"
            f"  type={self.type.value!r},\n"
            f"  properties={self.properties!r},\n"
            ")"
        )
