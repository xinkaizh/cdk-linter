from pathlib import Path
from typing import NamedTuple


class Diagnostic(NamedTuple):
    file: Path
    line: int
    message: str
