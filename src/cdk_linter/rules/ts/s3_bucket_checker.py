import logging
from pathlib import Path

from cdk_linter.core.diagnostic import Diagnostic
from cdk_linter.core.ts.statement_tree import FileStatementTree, StatementTree
from cdk_linter.rules.rule import TsRule
from cdk_linter.rules.ts.ast_helpers import (
    constructor_props,
    is_constructor,
    object_property,
    string_literal_value,
    walk_tree,
)

logger = logging.getLogger(__name__)


def _check_ip_address(name: str) -> bool:
    parts = name.split(".")

    if len(parts) != 4:
        return False

    for part in parts:
        if not part.isdigit():
            return False

        number = int(part)
        if number < 0 or number > 255:
            return False

    return True


def _validate_bucket_name(name: str) -> list[str]:
    problems: list[str] = []

    allowed_chars = "abcdefghijklmnopqrstuvwxyz0123456789.-"
    allowed_start_end_chars = "abcdefghijklmnopqrstuvwxyz0123456789"

    # bucket name length must be between 3 and 63 characters
    if len(name) < 3 or len(name) > 63:
        problems.append("must be between 3 and 63 characters long")

    # bucket name must be lowercase
    if name != name.lower():
        problems.append("must be lowercase")

    # bucket name cannot contain underscores
    if "_" in name:
        problems.append("must not contain underscores")

    # bucket name can only use lowercase letters, numbers, periods, and hyphens
    for char in name:
        if char not in allowed_chars:
            problems.append("can only contain lowercase letters, numbers, periods, and hyphens")
            break

    # bucket name must start with a lowercase letter or number
    if len(name) == 0 or name[0] not in allowed_start_end_chars:
        problems.append("must begin with a lowercase letter or number")

    # bucket name must end with a lowercase letter or number
    if len(name) == 0 or name[-1] not in allowed_start_end_chars:
        problems.append("must end with a lowercase letter or number")

    # bucket name cannot contain two periods next to each other
    if ".." in name:
        problems.append("must not contain two adjacent periods")

    # bucket name cannot look like an IP address
    if _check_ip_address(name):
        problems.append("must not be formatted like an IP address")

    return problems


def _check_statement(stmt: StatementTree, file: Path, violations: list[Diagnostic]) -> None:
    for node in walk_tree(stmt):
        if not is_constructor(node, "Bucket"):
            continue

        props_node = constructor_props(node)
        if props_node is None:
            continue

        bucket_name_node = object_property(props_node, "bucketName")
        if bucket_name_node is None:
            continue

        bucket_name = string_literal_value(bucket_name_node)
        if bucket_name is None:
            continue

        problems = _validate_bucket_name(bucket_name)

        if problems:
            line = bucket_name_node.start_line

            violations.append(
                Diagnostic(
                    file=file,
                    line=line,
                    message=(f"S3 bucketName {bucket_name!r} is invalid: " + "; ".join(problems)),
                )
            )


class S3BucketNameRule(TsRule):
    description = "Checks if S3 bucket names are valid in format"

    def check(self, files: list[FileStatementTree]) -> list[Diagnostic]:
        logger.debug(
            "Checking %d file(s) for S3 bucket name issues",
            len(files),
        )

        violations: list[Diagnostic] = []

        for file_tree in files:
            for stmt in file_tree.statements:
                _check_statement(stmt, file_tree.file, violations)

        logger.debug("s3_bucket_name: %d violation(s) found", len(violations))

        return violations
