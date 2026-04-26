import importlib
import inspect
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


def lint_ts(data_dir: str = "data/job_service", verbose: bool = False) -> None:
    """Lint all TypeScript CDK files under DATA_DIR.

    Args:
        data_dir: Root directory containing .ts CDK source files. Defaults to "data".
        verbose: Enable debug-level logging.
    """
    logger.info("Starting TypeScript lint on %s", data_dir)

    logger.info("Parsing TS files...")
    parsed_files: list[FileStatementTree] = parse_directory(Path(data_dir))

    rules: list[TsRule] = [r for r in _discover_rules() if isinstance(r, TsRule)]
    logger.info("Founds %d CFN rule(s)", len(rules))

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


def lint_cfn(cdk_app_root: str = "data/job_service", stack_name: str = "SampleStack") -> None:
    """Only supports linting a single stack for now"""
    path = Path(cdk_app_root) / "cdk.out" / f"{stack_name}.template.json"
    logger.info("Start linting CloudFormation template at %s", path)

    logger.info(f"Parsing CloudFormation template...")
    parser = CfnParser()
    parser.parse(path)
    graph = parser.get_resource_graph()
    index = parser.get_resource_index()

    visualize(graph)

    rules: list[CfnRule] = [r for r in _discover_rules() if isinstance(r, CfnRule)]
    logger.info("Founds %d CFN rule(s)", len(rules))

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
