# cdk-linter
Final project for Programming Tools class at UCB.

# Development
This Python project uses UV for dependency management.

To sync environment: `uv sync`

To add dependency: `uv add <pkg>`

To regenerate lock file: `uv lock`

To execute linter: `uv run linter` (this runs `run()` in `src/cdk_linter/runner.py`)

To execute dev linter (as a playground): `uv run dev` (this runs `run()` in `src/cdk_linter/dev.py`)

To clean cache files: `uv run clean` (this runs `clean()` in `src/cdk_linter/dev.py`)
