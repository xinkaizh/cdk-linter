from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DiagnosticSeverity(Enum):
    # Missing permissions remain errors by default; broader IAM findings can
    # opt into warning or critical severity when a rule has more context.
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Diagnostic:
    file: Path | None = None
    line: int | None = None
    message: str | None = None
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
