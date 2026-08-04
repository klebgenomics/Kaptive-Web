# Kaptive-Web Project Justfile
# Run `just` to see all available commands

set shell := ["bash", "-c"]

# Show available commands
default:
    @just --list

# Sync python dependencies and create the virtual environment using `uv`
sync:
    uv sync

# Run Python pytest suite
test: sync
    uv run pytest tests/

# Update dependencies and lockfile
update:
    uv lock --upgrade
    uv sync

# Clean caches and temporary files
clean:
    rm -rf .ruff_cache
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete

# Deep clean including the virtual environment and database
clean-all: clean
    rm -f kaptive_web.db 
    rm -rf .venv

# Format all Python code
fmt:
    uvx ruff format .

# Check if code is formatted without modifying files
fmt-check:
    uvx ruff format --check .

# Lint Python code and auto-fix safe errors
lint:
    uvx ruff check --fix .

# Static type-check Python code
type-check:
    uv sync --all-groups
    uvx ty check .

# Run all quality checks at once (ideal for local pre-commit testing)
check-all: fmt-check lint type-check

# Run the full CI pipeline locally
ci: check-all test

# Run the local development server using uvicorn
serve: sync
    uv run python -m kaptive_web.main --reload --host 127.0.0.1 --port 8000

# Build the standalone Docker image
docker-build:
    docker build -t kaptive-web:latest .

# Spin up Kaptive-Web and Caddy using Docker Compose in detached mode
docker-serve:
    docker compose up -d

# Spin down the Docker Compose stack
docker-stop:
    docker compose down

# Build the Singularity (.sif) image
singularity-build:
    sudo singularity build kaptive-web.sif Singularity.def

# Build the Apptainer (.sif) image
apptainer-build:
    sudo apptainer build kaptive-web.sif Apptainer.def

# Build the Python package
build: clean
    uv build

# Publish the Python package to PyPI
publish: build
    uv publish
