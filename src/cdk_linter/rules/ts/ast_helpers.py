from __future__ import annotations

from collections.abc import Iterator

from cdk_linter.core.ts.statement_tree import StatementTree


def walk_tree(node: StatementTree) -> Iterator[StatementTree]:
    yield node
    for child in node.children:
        yield from walk_tree(child)


def constructor_name(node: StatementTree) -> str | None:
    if node.type != "new_expression" or not node.children:
        return None

    constructor_node = node.children[0]
    return (
        constructor_node.children[-1].snippet
        if constructor_node.children
        else constructor_node.snippet
    )


def is_constructor(node: StatementTree, final_name: str) -> bool:
    return constructor_name(node) == final_name


def arguments_node(node: StatementTree) -> StatementTree | None:
    if node.type not in {"call_expression", "new_expression"}:
        return None
    return next((child for child in node.children if child.type == "arguments"), None)


def arguments(node: StatementTree) -> list[StatementTree]:
    args_node = arguments_node(node)
    if args_node is None:
        return []
    return [child for child in args_node.children if child.type != "comment"]


def argument(node: StatementTree, index: int) -> StatementTree | None:
    args = arguments(node)
    return args[index] if index < len(args) else None


def first_argument(node: StatementTree) -> StatementTree | None:
    return argument(node, 0)


def constructor_props(node: StatementTree) -> StatementTree | None:
    third_arg = argument(node, 2)
    return third_arg if third_arg is not None and third_arg.type == "object" else None


def object_property(object_node: StatementTree, property_name: str) -> StatementTree | None:
    if object_node.type != "object":
        return None

    for child in object_node.children:
        if child.type != "pair" or len(child.children) < 2:
            continue
        key_node = child.children[0]
        if _property_key_name(key_node) == property_name:
            return child.children[-1]

    return None


def string_literal_value(node: StatementTree) -> str | None:
    if node.type == "string":
        return _strip_quotes(node.snippet)

    if node.type == "template_string":
        if any(child.type != "string_fragment" for child in node.children):
            return None
        return "".join(child.snippet for child in node.children)

    return None


def boolean_literal_value(node: StatementTree) -> bool | None:
    if node.type == "true":
        return True
    if node.type == "false":
        return False
    return None


_DURATION_UNIT_SECONDS: dict[str, int] = {
    "millis": 0,  # treated as <1s; see duration_literal_seconds
    "seconds": 1,
    "minutes": 60,
    "hours": 3600,
    "days": 86400,
}


def duration_literal_seconds(node: StatementTree) -> int | None:
    """Resolve a literal ``Duration.<unit>(<number>)`` call to whole seconds.

    Returns ``None`` if the node is not such a call, the argument is not a
    plain numeric literal, or the unit is sub-second (``millis``).
    """
    if node.type != "call_expression" or len(node.children) < 2:
        return None

    callee = node.children[0]
    if callee.type != "member_expression" or len(callee.children) < 2:
        return None

    # Accept both `Duration.<unit>(...)` and `<ns>.Duration.<unit>(...)` (e.g. `cdk.Duration`).
    object_node = callee.children[0]
    object_final = (
        object_node.children[-1].snippet
        if object_node.type == "member_expression" and object_node.children
        else object_node.snippet
    )
    if object_final != "Duration":
        return None

    unit = callee.children[-1].snippet
    multiplier = _DURATION_UNIT_SECONDS.get(unit)
    if not multiplier:
        return None

    arg = first_argument(node)
    if arg is None or arg.type != "number":
        return None
    try:
        amount = int(arg.snippet)
    except ValueError:
        return None
    return amount * multiplier


def member_expression_final_name(node: StatementTree) -> str | None:
    if node.type != "member_expression" or not node.children:
        return None
    return node.children[-1].snippet


def is_member_call(node: StatementTree, final_name: str) -> bool:
    if node.type != "call_expression" or not node.children:
        return False
    return member_expression_final_name(node.children[0]) == final_name


def _property_key_name(node: StatementTree) -> str:
    literal = string_literal_value(node)
    return literal if literal is not None else node.snippet


def _strip_quotes(raw: str) -> str:
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"', "`"}:
        return raw[1:-1]
    return raw
