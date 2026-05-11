from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from cdk_linter.core.diagnostic import Diagnostic
from cdk_linter.core.ts.statement_tree import FileStatementTree, StatementTree
from cdk_linter.rules.rule import TsRule
from cdk_linter.rules.ts.ast_helpers import (
    constructor_props,
    duration_literal_seconds,
    is_constructor,
    object_property,
    walk_tree,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DurationRule:
    constructor: str
    property_name: str
    label: str
    min_seconds: int | None
    max_seconds: int | None


DURATION_RULES: tuple[DurationRule, ...] = (
    # Lambda: 1s to 15 min
    DurationRule("Function", "timeout", "Lambda timeout", 1, 900),
    # SQS: visibility 0s to 12h, delay 0s to 15min, receive wait 0s to 20s,
    # retention 60s to 14 days
    DurationRule("Queue", "visibilityTimeout", "SQS visibilityTimeout", 0, 43200),
    DurationRule("Queue", "deliveryDelay", "SQS deliveryDelay", 0, 900),
    DurationRule("Queue", "receiveMessageWaitTime", "SQS receiveMessageWaitTime", 0, 20),
    DurationRule("Queue", "retentionPeriod", "SQS retentionPeriod", 60, 1209600),
    # API Gateway integration: 50ms to 29s (we only catch >=1s here)
    DurationRule("Method", "timeout", "API Gateway Method timeout", 1, 29),
    DurationRule("LambdaIntegration", "timeout", "API Gateway integration timeout", 1, 29),
)


def _check_duration_rule(
    constructor: StatementTree,
    rule: DurationRule,
    file: Path,
    violations: list[Diagnostic],
) -> None:
    props = constructor_props(constructor)
    if props is None:
        return

    value_node = object_property(props, rule.property_name)
    if value_node is None:
        return

    seconds = duration_literal_seconds(value_node)
    if seconds is None:
        return

    problems: list[str] = []
    if rule.min_seconds is not None and seconds < rule.min_seconds:
        problems.append(f"must be at least {rule.min_seconds}s")
    if rule.max_seconds is not None and seconds > rule.max_seconds:
        problems.append(f"must be at most {rule.max_seconds}s")

    if not problems:
        return

    violations.append(
        Diagnostic(
            file=file,
            line=value_node.start_line,
            message=f"{rule.label} of {seconds}s is invalid: " + "; ".join(problems),
        )
    )


class AwsDurationLiteralRule(TsRule):
    description = "Checks literal CDK Duration values against AWS service min/max limits"

    def check(self, files: list[FileStatementTree]) -> list[Diagnostic]:
        violations: list[Diagnostic] = []

        for file_tree in files:
            for stmt in file_tree.statements:
                for node in walk_tree(stmt):
                    for rule in DURATION_RULES:
                        if is_constructor(node, rule.constructor):
                            _check_duration_rule(node, rule, file_tree.file, violations)

        logger.debug("aws_duration_literals: %d violation(s) found", len(violations))
        return violations
