from __future__ import annotations
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


class TsRule(BaseRule, ABC):
    kind = RuleType.TS

    @abstractmethod
    def check(self, files: list[FileStatementTree]) -> list[Diagnostic]: ...


class CfnRule(BaseRule, ABC):
    kind = RuleType.CFN

    @abstractmethod
    def check(self, graph: ResourceGraph, index: ResourceIndex) -> list[Diagnostic]: ...
