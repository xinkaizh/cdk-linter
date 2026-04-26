from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from enum import Enum, auto

from cdk_linter.core.cfn.resource_graph import ResourceGraph
from cdk_linter.core.cfn.resource_index import ResourceIndex
from cdk_linter.core.diagnostic import Diagnostic
from cdk_linter.core.ts.statement_tree import FileStatementTree


class RuleType(Enum):
    TS = auto()
    CFN = auto()


class BaseRule(ABC):
    kind: RuleType
    description: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Skip abstract intermediate classes: TsRule, CfnRule
        if inspect.isabstract(cls):
            return
        if "description" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define 'description'")


class TsRule(BaseRule, ABC):
    kind = RuleType.TS

    @abstractmethod
    def check(self, files: list[FileStatementTree]) -> list[Diagnostic]: ...


class CfnRule(BaseRule, ABC):
    kind = RuleType.CFN

    @abstractmethod
    def check(self, graph: ResourceGraph, index: ResourceIndex) -> list[Diagnostic]: ...
