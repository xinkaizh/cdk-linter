from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cdk_linter.parsers.tsparser import Diagnostic, FileStatementTree


class RuleKind(Enum):
    TS = auto()
    CFN = auto()


class BaseRule(ABC):
    kind: RuleKind


class TSRule(BaseRule, ABC):
    kind = RuleKind.TS

    @abstractmethod
    def check(self, files: "list[FileStatementTree]") -> "list[Diagnostic]": ...


# NOTE: Uncomment once CFNRules exists
# class CFNRule(BaseRule, ABC):
#     kind = RuleKind.CFN

#     @abstractmethod
#     def check(self, rdg: Any) -> "list[Diagnostic]": ...
