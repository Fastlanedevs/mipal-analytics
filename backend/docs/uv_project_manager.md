# UV Project Manager

### Install the uv project manager

`curl -LsSf https://astral.sh/uv/install.sh | sh`

### Pin .python-version to `3.11`

`uv python pin 3.11`

### Creating a virtual environment

`uv venv`

`source .venv/bin/activate`

### Installing Ruff linter

`uv tool install ruff@latest`

`uvx ruff check ` # Lint all files in the current directory.

`uvx ruff format ` # Format all files in the current directory.
