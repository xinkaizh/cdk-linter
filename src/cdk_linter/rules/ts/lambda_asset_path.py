import logging
from pathlib import Path

from cdk_linter.core.diagnostic import Diagnostic
from cdk_linter.core.ts.statement_tree import FileStatementTree, StatementTree
from cdk_linter.rules.rule import TsRule
from cdk_linter.rules.ts.ast_helpers import (
    first_argument,
    is_member_call,
    string_literal_value,
    walk_tree,
)

logger = logging.getLogger(__name__)


def _check_statement(stmt: StatementTree, file: Path, violations: list[Diagnostic]) -> None:
    for node in walk_tree(stmt):
        if not is_member_call(node, "fromAsset"):
            continue

        first_arg = first_argument(node)
        if first_arg is None:
            continue

        value = string_literal_value(first_arg)
        if value is None:
            continue

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
    description = "Checks if asset path for Lambda function is properly configured"

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
