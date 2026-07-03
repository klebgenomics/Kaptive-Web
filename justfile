# Kaptive Project Justfile
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

# Clean Python virtual environments
clean:
    rm -f kaptive_web.db 
    rm -rf .venv
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -exec rm -rf {} +

# Run the local development server using uvicorn
serve: sync
    uv run uvicorn kaptive_web.main:app --reload --host 127.0.0.1 --port 8000

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
