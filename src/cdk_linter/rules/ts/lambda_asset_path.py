import logging
from pathlib import Path
from typing import Iterator

from cdk_linter.core.diagnostic import Diagnostic
from cdk_linter.core.ts.statement_tree import FileStatementTree, StatementTree
from cdk_linter.rules.rule import TsRule

logger = logging.getLogger(__name__)


def _walk_tree(node: StatementTree) -> Iterator[StatementTree]:
    yield node
    for child in node.children:
        yield from _walk_tree(child)


def _is_from_asset_call(node: StatementTree) -> bool:
    if node.type != "call_expression":
        return False

    if not node.children:
        return False

    function_node = node.children[0]
    if function_node.type != "member_expression" or not function_node.children:
        return False

    return function_node.children[-1].snippet == "fromAsset"


def _get_first_argument(node: StatementTree) -> StatementTree | None:
    if node.type != "call_expression":
        return None

    arguments_node = next((child for child in node.children if child.type == "arguments"), None)
    if arguments_node is None:
        return None

    for argument in arguments_node.children:
        if argument.type != "comment":
            return argument
    return None


def _check_statement(stmt: StatementTree, file: Path, violations: list[Diagnostic]) -> None:
    for node in _walk_tree(stmt):
        if not _is_from_asset_call(node):
            continue

        first_arg = _get_first_argument(node)
        if first_arg is None:
            continue
        if first_arg.type != "string":
            continue

        raw = first_arg.snippet
        if len(raw) < 2:
            continue
        value = raw[1:-1]  # strip surrounding quote character

        if not (value.endswith("/") or value.endswith(".zip")):
            line = node.start_line
            logger.debug("Violation at %s:%d - fromAsset path %r", file, line, value)
            violations.append(
                Diagnostic(
                    file=file,
                    line=line,
                    message=(
                        f"lambda.Code.fromAsset() path must be a directory "
                        f"(ending with /) or a .zip file, got: {repr(value)}"
                    ),
                )
            )


class LambdaAssetPath(TsRule):
    def check(self, files: list[FileStatementTree]) -> list[Diagnostic]:
        statement_count = sum(len(file_tree.statements) for file_tree in files)
        logger.debug(
            "Checking %d statement(s) across %d file(s) for lambda asset path issues",
            statement_count,
            len(files),
        )

        violations: list[Diagnostic] = []
        for file_tree in files:
            for stmt in file_tree.statements:
                _check_statement(stmt, file_tree.file, violations)

        logger.debug("lambda_asset_path: %d violation(s) found", len(violations))
        return violations
