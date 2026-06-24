FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the app source
COPY . /app/

# Install the app (uses pip to install pyproject.toml dependencies)
RUN pip install --no-cache-dir .

# Expose the standard FastAPI port
EXPOSE 8000

# Set the default entrypoint for the container
CMD ["uvicorn", "kaptive_web.main:app", "--host", "0.0.0.0", "--port", "8000"]
