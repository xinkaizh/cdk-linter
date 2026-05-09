from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from cdk_linter.core.diagnostic import Diagnostic
from cdk_linter.core.ts.statement_tree import FileStatementTree, StatementTree
from cdk_linter.rules.rule import TsRule
from cdk_linter.rules.ts.ast_helpers import (
    argument,
    boolean_literal_value,
    constructor_props,
    is_constructor,
    object_property,
    string_literal_value,
    walk_tree,
)

logger = logging.getLogger(__name__)

Validator = Callable[[str, StatementTree], list[str]]


@dataclass(frozen=True)
class PropertyRule:
    constructor: str
    property_name: str
    label: str
    validator: Validator


IAM_ROLE_CHARS = re.compile(r"^[\w+=,.@-]+$")
RDS_CLUSTER_ID = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
LAMBDA_FUNCTION_NAME = re.compile(r"^[A-Za-z0-9-_]+$")
SQS_QUEUE_NAME = re.compile(r"^[A-Za-z0-9_-]+(?:\.fifo)?$")
SNS_TOPIC_NAME = re.compile(r"^[A-Za-z0-9_-]+(?:\.fifo)?$")
DYNAMODB_TABLE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
LOG_GROUP_NAME = re.compile(r"^[A-Za-z0-9._\-/#]+$")
KMS_ALIAS_NAME = re.compile(r"^alias/[A-Za-z0-9:/_-]+$")
ECR_REPOSITORY_NAME = re.compile(
    r"^(?:[a-z0-9]+(?:(?:[._-]|__|[-]*)[a-z0-9]+)*)(?:/[a-z0-9]+(?:(?:[._-]|__|[-]*)[a-z0-9]+)*)*$"
)


def _length_between(name: str, minimum: int, maximum: int) -> list[str]:
    if len(name) < minimum or len(name) > maximum:
        return [f"must be between {minimum} and {maximum} characters long"]
    return []


def _iam_role_name(name: str, _node: StatementTree) -> list[str]:
    problems = _length_between(name, 1, 64)
    if name and not IAM_ROLE_CHARS.fullmatch(name):
        problems.append("can only contain letters, numbers, and _+=,.@-")
    return problems


def _rds_cluster_identifier(name: str, _node: StatementTree) -> list[str]:
    problems = _length_between(name, 1, 63)
    if name and not RDS_CLUSTER_ID.fullmatch(name):
        problems.append("must start with a letter and contain only letters, numbers, and hyphens")
    if name.endswith("-"):
        problems.append("must not end with a hyphen")
    if "--" in name:
        problems.append("must not contain two consecutive hyphens")
    return problems


def _lambda_function_name(name: str, _node: StatementTree) -> list[str]:
    problems = _length_between(name, 1, 64)
    if name and not LAMBDA_FUNCTION_NAME.fullmatch(name):
        problems.append("can only contain letters, numbers, hyphens, and underscores")
    return problems


def _sqs_queue_name(name: str, constructor: StatementTree) -> list[str]:
    problems = _length_between(name, 1, 80)
    if name and not SQS_QUEUE_NAME.fullmatch(name):
        problems.append(
            "can only contain letters, numbers, hyphens, underscores, and optional .fifo suffix"
        )
    if _literal_bool_prop(constructor, ("fifo", "fifoQueue")) is True and not name.endswith(
        ".fifo"
    ):
        problems.append("FIFO queue names must end with .fifo")
    return problems


def _sns_topic_name(name: str, constructor: StatementTree) -> list[str]:
    problems = _length_between(name, 1, 256)
    if name and not SNS_TOPIC_NAME.fullmatch(name):
        problems.append(
            "can only contain ASCII letters, numbers, underscores, hyphens, and optional .fifo suffix"
        )
    if _literal_bool_prop(constructor, ("fifo", "fifoTopic")) is True and not name.endswith(
        ".fifo"
    ):
        problems.append("FIFO topic names must end with .fifo")
    return problems


def _dynamodb_table_name(name: str, _node: StatementTree) -> list[str]:
    problems = _length_between(name, 3, 255)
    if name and not DYNAMODB_TABLE_NAME.fullmatch(name):
        problems.append("can only contain letters, numbers, underscores, hyphens, and periods")
    return problems


def _log_group_name(name: str, _node: StatementTree) -> list[str]:
    problems = _length_between(name, 1, 512)
    if name and not LOG_GROUP_NAME.fullmatch(name):
        problems.append(
            "can only contain letters, numbers, periods, underscores, hyphens, slashes, and #"
        )
    return problems


def _kms_alias_name(name: str, _node: StatementTree) -> list[str]:
    problems = _length_between(name, 1, 256)
    if not name.startswith("alias/"):
        problems.append("must start with alias/")
    if name.startswith("alias/aws/"):
        problems.append("must not start with reserved prefix alias/aws/")
    if name and not KMS_ALIAS_NAME.fullmatch(name):
        problems.append(
            "can only contain letters, numbers, colons, slashes, underscores, and hyphens"
        )
    return problems


def _ecr_repository_name(name: str, _node: StatementTree) -> list[str]:
    problems = _length_between(name, 2, 256)
    if name and not ECR_REPOSITORY_NAME.fullmatch(name):
        problems.append("must be a lowercase repository path")
    return problems


PROPERTY_RULES: tuple[PropertyRule, ...] = (
    PropertyRule("Role", "roleName", "IAM roleName", _iam_role_name),
    PropertyRule(
        "DatabaseCluster", "clusterIdentifier", "RDS clusterIdentifier", _rds_cluster_identifier
    ),
    PropertyRule(
        "DatabaseCluster", "dbClusterIdentifier", "RDS dbClusterIdentifier", _rds_cluster_identifier
    ),
    PropertyRule("Function", "functionName", "Lambda functionName", _lambda_function_name),
    PropertyRule("Queue", "queueName", "SQS queueName", _sqs_queue_name),
    PropertyRule("Topic", "topicName", "SNS topicName", _sns_topic_name),
    PropertyRule("Table", "tableName", "DynamoDB tableName", _dynamodb_table_name),
    PropertyRule("LogGroup", "logGroupName", "CloudWatch Logs logGroupName", _log_group_name),
    PropertyRule("Alias", "aliasName", "KMS aliasName", _kms_alias_name),
    PropertyRule("Repository", "repositoryName", "ECR repositoryName", _ecr_repository_name),
)


def _literal_bool_prop(constructor: StatementTree, names: tuple[str, ...]) -> bool | None:
    props = constructor_props(constructor)
    if props is None:
        return None

    for name in names:
        value_node = object_property(props, name)
        if value_node is None:
            continue
        value = boolean_literal_value(value_node)
        if value is not None:
            return value

    return None


def _check_property_rule(
    constructor: StatementTree,
    rule: PropertyRule,
    file: Path,
    violations: list[Diagnostic],
) -> None:
    props = constructor_props(constructor)
    if props is None:
        return

    value_node = object_property(props, rule.property_name)
    if value_node is None:
        return

    value = string_literal_value(value_node)
    if value is None:
        return

    problems = rule.validator(value, constructor)
    if not problems:
        return

    violations.append(
        Diagnostic(
            file=file,
            line=value_node.start_line,
            message=f"{rule.label} {value!r} is invalid: " + "; ".join(problems),
        )
    )


def _check_generated_iam_role_name(
    constructor: StatementTree,
    file: Path,
    violations: list[Diagnostic],
) -> None:
    props = constructor_props(constructor)
    if props is not None and object_property(props, "roleName") is not None:
        return

    construct_id_node = argument(constructor, 1)
    if construct_id_node is None:
        return

    construct_id = string_literal_value(construct_id_node)
    if construct_id is None or len(construct_id) <= 64:
        return

    violations.append(
        Diagnostic(
            file=file,
            line=construct_id_node.start_line,
            message=(
                f"IAM Role construct id {construct_id!r} is longer than IAM's 64-character "
                "role name limit; CDK-generated physical names are likely to exceed the limit"
            ),
        )
    )


class AwsNameLiteralRule(TsRule):
    description = "Checks literal CDK AWS resource names for common naming and length limits"

    def check(self, files: list[FileStatementTree]) -> list[Diagnostic]:
        violations: list[Diagnostic] = []

        for file_tree in files:
            for stmt in file_tree.statements:
                for node in walk_tree(stmt):
                    for rule in PROPERTY_RULES:
                        if is_constructor(node, rule.constructor):
                            _check_property_rule(node, rule, file_tree.file, violations)

                    if is_constructor(node, "Role"):
                        _check_generated_iam_role_name(node, file_tree.file, violations)

        logger.debug("aws_name_literals: %d violation(s) found", len(violations))
        return violations
