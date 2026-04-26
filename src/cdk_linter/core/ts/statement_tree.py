from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StatementTree:
    type: str
    start_line: int
    end_line: int
    snippet: str
    children: list[StatementTree] = field(default_factory=list)


@dataclass
class FileStatementTree:
    file: Path
    statements: list[StatementTree]
