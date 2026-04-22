from pathlib import Path
import shutil

from cdk_linter.parsers.cfn_template_parser import CfnTemplateParser


def run():
    """
    A convenient playground for testing code.
    Usage: `uv run dev`
    """
    print("Running CDK linter in dev mode...")
    parser = CfnTemplateParser()
    parser.parse("data/cdk.out/SampleStack.template.json")


def clean():
    """
    Utility function to clean all cache files.
    Usage: `uv run clean`
    """
    root = Path(".")

    # __pycache__
    for p in root.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)

    # .pyc files
    for p in root.rglob("*.pyc"):
        p.unlink(missing_ok=True)

    # .egg-info directories
    for p in root.rglob("*.egg-info"):
        shutil.rmtree(p, ignore_errors=True)

    # pytest cache
    shutil.rmtree(".pytest_cache", ignore_errors=True)

    print("Cleaned Python cache + egg-info")
