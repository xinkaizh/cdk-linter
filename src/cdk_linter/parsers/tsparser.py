from dataclasses import dataclass, field
import logging
import os.path
from os import PathLike
from pathlib import Path
from typing import NamedTuple, Any
import msgspec

import fire
from tree_sitter import Language, Node, Parser
import tree_sitter_typescript as tstypescript

logger = logging.getLogger(__name__)

TS_LANGUAGE = Language(tstypescript.language_typescript())

STATEMENT_TYPES: frozenset[str] = frozenset(
    {
        "import_statement",
        "lexical_declaration",
        "variable_declaration",
        "expression_statement",
        "if_statement",
        "return_statement",
        "throw_statement",
        "for_statement",
        "while_statement",
    }
)

STRUCTURAL_CONTAINERS: frozenset[str] = frozenset(
    {
        "program",
        "export_statement",
        "class_declaration",
        "function_declaration",
        "statement_block",
        "class_body",
        "method_definition",
    }
)

EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {
        "cdk.out",
        "node_modules",
        "dist",
        "build",
        ".git",
        ".venv",
        "venv",
        "__pycache__",
    }
)


class Diagnostic(NamedTuple):
    file: Path
    line: int
    message: str


@dataclass
class StatementTree:
    type: str
    start_line: int
    end_line: int
    snippet: str
    children: list["StatementTree"] = field(default_factory=list)


@dataclass
class FileStatementTree:
    file: Path
    statements: list[StatementTree]


def _decode_snippet(source: bytes, node: Node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _build_statement_tree(node: Node, source: bytes) -> StatementTree:
    children = [_build_statement_tree(child, source) for child in node.named_children]
    return StatementTree(
        type=node.type,
        start_line=node.start_point.row + 1,
        end_line=node.end_point.row + 1,
        snippet=_decode_snippet(source, node),
        children=children,
    )


def _collect_statements(
    node: Node,
    results: list[StatementTree],
    source: bytes,
) -> None:
    if node.type in STATEMENT_TYPES:
        results.append(_build_statement_tree(node, source))
        return

    if node.type in STRUCTURAL_CONTAINERS:
        for child in node.named_children:
            _collect_statements(child, results, source)


def _is_relevant_ts_file(file: Path) -> bool:
    if file.suffix != ".ts":
        return False
    return not any(part in EXCLUDED_DIR_NAMES for part in file.parts)


def parse_file(file: PathLike) -> FileStatementTree:
    logger.debug("Parsing %s", file)
    file_path = Path(file)
    try:
        source = file_path.read_bytes()
    except OSError as exc:
        logger.error("Cannot read %s: %s", file, exc)
        raise

    parser = Parser(TS_LANGUAGE)
    tree = parser.parse(source)

    statements: list[StatementTree] = []
    _collect_statements(tree.root_node, statements, source)

    logger.debug("Found %d statement(s) in %s", len(statements), file_path)
    return FileStatementTree(file=file_path, statements=statements)


def parse_directory(root: PathLike) -> list[FileStatementTree]:
    logger.info("Scanning %s for TypeScript files", root)
    root_path = Path(root)
    ts_files = sorted(
        file for file in root_path.rglob("*.ts") if _is_relevant_ts_file(file)
    )
    logger.debug(
        "Found %d relevant .ts file(s): %s", len(ts_files), [str(f) for f in ts_files]
    )

    parsed_files = [parse_file(ts_file) for ts_file in ts_files]
    total_statements = sum(len(parsed.statements) for parsed in parsed_files)

    logger.info(
        "Parsed %d statement(s) from %d file(s) in %s",
        total_statements,
        len(parsed_files),
        root,
    )
    return parsed_files


def _main_parse_file_entrypoint(path: PathLike) -> str | None:
    """Parses a file and dumps the FileStatementTree object"""

    def enc_hook(obj: Any) -> Any:
        if isinstance(obj, Path):
            return str(obj)
        return None

    if not os.path.exists(path):
        logger.error("Path %s does not exist.", path)
        return None

    result = parse_file(path)
    return msgspec.json.encode(result, enc_hook=enc_hook).decode()


def main() -> None:
    fire.Fire(_main_parse_file_entrypoint)
