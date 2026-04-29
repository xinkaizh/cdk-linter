import logging
from pathlib import Path
from typing import Iterator

from cdk_linter.parsers.tsparser import Diagnostic, FileStatementTree, StatementTree
from cdk_linter.rules import TSRule

logger = logging.getLogger(__name__)


def _walk_tree(node: StatementTree) -> Iterator[StatementTree]:
    yield node
    for child in node.children:
        yield from _walk_tree(child)


# Check if the constructor format is right or not
def _is_s3_bucket_constructor(node: StatementTree) -> bool:
    if node.type != "new_expression":
        return False

    if not node.children:
        return False

    constructor_node = node.children[0]

    # new s3.Bucket
    if constructor_node.type == "member_expression":
        if not constructor_node.children:
            return False

        return constructor_node.children[-1].snippet == "Bucket"

    # Case: new Bucket()
    if constructor_node.snippet == "Bucket":
        return True

    return False


def _strip_quotes(raw: str) -> str:
    if len(raw) >= 2:
        first_char = raw[0]
        last_char = raw[-1]

        if first_char == last_char and first_char in {"'", '"', "`"}:
            return raw[1:-1]

    return raw


def _find_bucket_name_property(node: StatementTree) -> StatementTree | None:
    for current in _walk_tree(node):
        if current.type != "pair":
            continue

        if len(current.children) < 2:
            continue

        key_node = current.children[0]
        value_node = current.children[-1]

        if key_node.snippet == "bucketName":
            return value_node

    return None


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


def _check_statement(
    stmt: StatementTree, file: Path, violations: list[Diagnostic]
) -> None:
    for node in _walk_tree(stmt):
        if not _is_s3_bucket_constructor(node):
            continue

        bucket_name_node = _find_bucket_name_property(node)

        if bucket_name_node is None:
            continue

        if bucket_name_node.type != "string":
            continue

        bucket_name = _strip_quotes(bucket_name_node.snippet)
        problems = _validate_bucket_name(bucket_name)

        if problems:
            line = bucket_name_node.start_line

            violations.append(
                Diagnostic(
                    file=file,
                    line=line,
                    message=(
                        f"S3 bucketName {bucket_name!r} is invalid: "
                        + "; ".join(problems)
                    ),
                )
            )


class S3BucketName(TSRule):
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