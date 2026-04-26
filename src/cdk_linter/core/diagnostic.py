from dataclasses import dataclass
from pathlib import Path


@dataclass
class Diagnostic:
    file: Path | None = None
    line: int | None = None
    message: str | None = None
