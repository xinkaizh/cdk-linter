import importlib
import inspect
import json
import logging
import pkgutil
from pathlib import Path

import fire

import cdk_linter.rules as _rules_pkg
from cdk_linter.core.diagnostic import Diagnostic
from cdk_linter.core.ts.statement_tree import FileStatementTree
from cdk_linter.parsers.cfn_parser import CfnParser
from cdk_linter.parsers.ts_parser import parse_directory
from cdk_linter.rules.cfn.lambda_permission_rule import LambdaPermissionRule
from cdk_linter.rules.rule import BaseRule, CfnRule, TsRule
from cdk_linter.utils.pretty_logging import CHECK, CROSS, RED, RESET, ColorAdapter
from cdk_linter.utils.visualize_graph import visualize

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)7s | %(module)s | %(message)s",
)
logging.getLogger("cdk_linter.parsers.cfn_parser").setLevel(logging.ERROR)
logger = ColorAdapter(logging.getLogger(__name__), {})


def placeholder_emit_as_lsp_diagnostic(file: Path, line: int, message: str) -> None:
    # Placeholder for now. Ideally we'll send it out as a LSP message, but I
    # think that'll be the orchestrator's job
    locator = f"{file}:{line} " if file else ""
    logger.error(f"{RED}{CROSS} {locator}{message}{RESET}")


def _discover_rules() -> list[BaseRule]:
    rules: list[BaseRule] = []
    for _finder, module_name, _is_pkg in pkgutil.walk_packages(
        _rules_pkg.__path__,
        prefix="cdk_linter.rules.",
        onerror=lambda name: logger.warning("Could not import rule package %s", name),
    ):
        mod = importlib.import_module(module_name)
        for _attr, obj in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(obj, BaseRule)
                and obj is not BaseRule
                and obj is not TsRule
                and obj is not CfnRule
                and obj.__module__ == module_name
            ):
                logger.debug("Discovered rule: %s", obj.__name__)
                rules.append(obj())
    return rules


def lint_ts(data_dir: str = "data/good/job_service", verbose: bool = False) -> None:
    """Lint all TypeScript CDK files under DATA_DIR.

    Args:
        data_dir: Root directory containing .ts CDK source files.
        verbose: Enable debug-level logging.
    """
    logger.info("Starting TypeScript lint on %s", data_dir)

    logger.info("Parsing TS files...")
    parsed_files: list[FileStatementTree] = parse_directory(Path(data_dir))

    rules: list[TsRule] = [r for r in _discover_rules() if isinstance(r, TsRule)]
    logger.info("Found %d TS rule(s)", len(rules))

    total_diagnostics = 0
    for rule in rules:
        logger.info("Running rule: %s", rule.description)
        try:
            diagnostics: list[Diagnostic] = rule.check(parsed_files)
        except Exception:
            logger.error("Rule %s raised an exception", type(rule).__name__, exc_info=True)
            continue
        for diag in diagnostics:
            placeholder_emit_as_lsp_diagnostic(diag.file, diag.line, diag.message)
        total_diagnostics += len(diagnostics)

    if total_diagnostics == 0:
        logger.info(f"{CHECK} Lint complete: no issues found")
    else:
        logger.info("Lint complete: %d diagnostic(s) emitted", total_diagnostics)


def _order_cfn_stacks_from_manifest(cdk_app_root: str, stack_names: tuple[str, ...]) -> tuple[str, ...]:
    """
    topologically sort the stacks if there are dependencies
    """
    manifest_path = Path(cdk_app_root) / "cdk.out" / "manifest.json"
    if not manifest_path.exists():
        return stack_names

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    artifacts = manifest.get("artifacts", {})
    requested_stacks = set(stack_names)
    dependencies = {
        stack_name: [
            dependency
            for dependency in artifacts.get(stack_name, {}).get("dependencies", [])
            if dependency in requested_stacks
            and artifacts.get(dependency, {}).get("type") == "aws:cloudformation:stack"
        ]
        for stack_name in stack_names
    }

    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(stack_name: str) -> None:
        if stack_name in visited:
            return
        if stack_name in visiting:
            raise ValueError(f"Circular stack dependency found while ordering {stack_name}")

        visiting.add(stack_name)
        for dependency in dependencies[stack_name]:
            visit(dependency)
        visiting.remove(stack_name)
        visited.add(stack_name)
        ordered.append(stack_name)

    for stack_name in stack_names:
        visit(stack_name)

    return tuple(ordered)


def lint_cfn(cdk_app_root: str = "data/good/job_service", *stack_names: str) -> None:
    """Lint one or more CloudFormation stacks."""
    if not stack_names:
        stack_names = ("FullStack",)

    stack_names = _order_cfn_stacks_from_manifest(cdk_app_root, stack_names)
    paths = [Path(cdk_app_root) / "cdk.out" / f"{stack_name}.template.json" for stack_name in stack_names]
    logger.info("Start linting CloudFormation template at %s", paths)

    logger.info(f"Parsing CloudFormation template...")
    parser = CfnParser()
    parser.parse_all(paths)
    graph = parser.get_resource_graph()
    index = parser.get_resource_index()

    visualize(graph)

    rules: list[CfnRule] = [r for r in _discover_rules() if isinstance(r, CfnRule)]
    logger.info("Found %d CFN rule(s)", len(rules))

    total_diagnostics = 0
    for rule in rules:
        logger.info("Running rule: %s", rule.description)
        try:
            # temporary solution for taking in a spec
            if isinstance(rule, LambdaPermissionRule):
                rule.prime(Path(cdk_app_root) / "spec.txt")

            diagnostics: list[Diagnostic] = rule.check(graph, index)
        except Exception:
            logger.error("Rule %s raised an exception", type(rule).__name__, exc_info=True)
            continue

        for diag in diagnostics:
            placeholder_emit_as_lsp_diagnostic(diag.file, diag.line, diag.message)

        total_diagnostics += len(diagnostics)

    if total_diagnostics == 0:
        logger.info(f"{CHECK} Lint complete: no issues found")
    else:
        logger.info("Lint complete: %d diagnostic(s) emitted", total_diagnostics)


def run() -> None:
    """
    Main code entry point for CDK Linter.
    Usage: `uv run linter ts` or `uv run linter cfn`
    """
    fire.Fire(
        {
            "ts": lint_ts,
            "cfn": lint_cfn,
        }
    )
