from dataclasses import dataclass, field
from typing import Any

from cdk_linter.core.cfn.resource_type import ResourceType


@dataclass
class CfnResource:
    id: str # logical ID
    type: ResourceType
    properties: dict[str, Any] = field(default_factory=dict)
    depends_on: set[str] = field(default_factory=set)
