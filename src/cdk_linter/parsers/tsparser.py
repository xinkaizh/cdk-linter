from dataclasses import dataclass, field
import logging
from os import PathLike
from pathlib import Path
from typing import NamedTuple
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


class Diagnostic(NamedTuple):
    file: Path
    line: int
    message: str


@dataclass
class StatementTree:
    node: Node
    file: Path
    source: bytes
    children: list["StatementTree"] = field(default_factory=list)

    @property
    def start_line(self) -> int:
        return self.node.start_point.row + 1


def _collect_inner(
    node: Node, file: Path, source: bytes, seen: set[int]
) -> list[StatementTree]:
    results: list[StatementTree] = []
    for child in node.children:
        if child.type in STATEMENT_TYPES:
            if child.id not in seen:
                seen.add(child.id)
                inner = _collect_inner(child, file, source, seen)
                results.append(StatementTree(node=child, file=file, source=source, children=inner))
        else:
            results.extend(_collect_inner(child, file, source, seen))
    return results


def _collect_statements(
    node: Node, results: list[StatementTree], file: Path, source: bytes, seen: set[int]
) -> None:
    node_type = node.type

    if node_type in STATEMENT_TYPES:
        if node.id not in seen:
            seen.add(node.id)
            children = _collect_inner(node, file, source, seen)
            results.append(StatementTree(node=node, file=file, source=source, children=children))
        return

    if node_type in STRUCTURAL_CONTAINERS:
        for child in node.children:
            _collect_statements(child, results, file, source, seen)


def parse_file(file: PathLike) -> list[StatementTree]:
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
    seen: set[int] = set()
    _collect_statements(tree.root_node, statements, file_path, source, seen)

    logger.debug("Found %d statement(s) in %s", len(statements), file_path)
    return statements


def parse_directory(root: PathLike) -> list[StatementTree]:
    logger.info("Scanning %s for TypeScript files", root)
    root_file = Path(root)
    ts_files = sorted(root_file.rglob("*.ts"))
    logger.debug("Found %d .ts file(s): %s", len(ts_files), [str(f) for f in ts_files])

    all_statements: list[StatementTree] = []
    for ts_file in ts_files:
        all_statements.extend(parse_file(ts_file))

    logger.info(
        "Parsed %d statement(s) from %d file(s) in %s",
        len(all_statements),
        len(ts_files),
        root,
    )
    return all_statements


def main():
    fire.Fire(parse_file)
