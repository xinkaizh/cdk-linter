import logging

from tree_sitter import Node

from cdk_linter.parsers.tsparser import Diagnostic, StatementTree
from cdk_linter.rules import TSRule

logger = logging.getLogger(__name__)


def _find_call_expressions(node: Node, out: list[Node]) -> None:
    if node.type == "call_expression":
        out.append(node)
    for child in node.children:
        _find_call_expressions(child, out)


def _check_statement(stmt: StatementTree, violations: list[Diagnostic]) -> None:
    calls: list[Node] = []
    _find_call_expressions(stmt.node, calls)

    for call in calls:
        if len(call.named_children) < 2:
            continue

        func_node = call.named_children[0]
        if func_node.type != "member_expression":
            continue

        prop = func_node.child_by_field_name("property")
        if prop is None or prop.text != b"fromAsset":
            continue

        args_node = call.named_children[1]
        if not args_node.named_children:
            continue

        first_arg = args_node.named_children[0]

        if first_arg.type != "string":
            continue

        raw = first_arg.text.decode("utf-8", errors="replace")
        value = raw[1:-1]  # strip surrounding quote character

        if not (value.endswith("/") or value.endswith(".zip")):
            line = call.start_point.row + 1
            logger.debug("Violation at %s:%d — fromAsset path %r", stmt.file, line, value)
            violations.append(Diagnostic(
                file=stmt.file,
                line=line,
                message=(
                    f"lambda.Code.fromAsset() path must be a directory "
                    f"(ending with /) or a .zip file, got: {repr(value)}"
                ),
            ))


class LambdaAssetPath(TSRule):
    def check(self, statements: list[StatementTree]) -> list[Diagnostic]:
        logger.debug("Checking %d statement(s) for lambda asset path issues", len(statements))
        violations: list[Diagnostic] = []
        for stmt in statements:
            _check_statement(stmt, violations)
        logger.debug("lambda_asset_path: %d violation(s) found", len(violations))
        return violations
