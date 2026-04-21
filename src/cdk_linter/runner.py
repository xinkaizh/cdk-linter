import importlib
import inspect
import logging
import pkgutil
from pathlib import Path

import fire

import cdk_linter.rules as _rules_pkg
from cdk_linter.rules import BaseRule, TSRule
from cdk_linter.parsers.tsparser import Diagnostic, StatementTree, parse_directory

logger = logging.getLogger(__name__)


def placeholder_emit_as_lsp_diagnostic(file: Path, line: int, message: str) -> None:
    # Placeholder for now. Ideally we'll send it out as a LSP message, but I
    # think that'll be the orchestrator's job
    print(f"{file}:{line}: {message}")


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
                and obj is not TSRule
                # and obj is not CFNRule
                and obj.__module__ == module_name
            ):
                logger.debug("Discovered rule: %s", obj.__name__)
                rules.append(obj())
    return rules


def lint_ts(data_dir: str = "data", verbose: bool = False) -> None:
    """Lint all TypeScript CDK files under DATA_DIR.

    Args:
        data_dir: Root directory containing .ts CDK source files. Defaults to "data".
        verbose: Enable debug-level logging.
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    logger.info("Starting TypeScript lint on %s", data_dir)

    rules: list[TSRule] = [r for r in _discover_rules() if isinstance(r, TSRule)]
    logger.info("Running %d TS rule(s)", len(rules))

    statements: list[StatementTree] = parse_directory(Path(data_dir))

    total_diagnostics = 0
    for rule in rules:
        try:
            diagnostics: list[Diagnostic] = rule.check(statements)
        except Exception:
            logger.error("Rule %s raised an exception", type(rule).__name__, exc_info=True)
            continue
        for diag in diagnostics:
            placeholder_emit_as_lsp_diagnostic(diag.file, diag.line, diag.message)
        total_diagnostics += len(diagnostics)

    logger.info("Lint complete: %d diagnostic(s) emitted", total_diagnostics)


def lint_cfn() -> None:
    """Lint all CloudFormation templates.
    """
    raise NotImplementedError("Not implemented yet")


def run() -> None:
    """
    Main code entry point for CDK Linter.
    Usage: `uv run linter`
    """
    fire.Fire({
        'ts': lint_ts,
        'cfn': lint_cfn,
    })
