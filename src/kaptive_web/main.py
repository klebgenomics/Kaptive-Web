"""Main application module."""

import argparse
import secrets
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import metadata as importlib_metadata
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from kaptive_web.api.routes import auth, serotype
from kaptive_web.core.config import settings
from kaptive_web.core.logging import setup_logging
from kaptive_web.core.responses import KaptiveORJSONResponse
from kaptive_web.core.state import AppState
from kaptive_web.db.repository import Repository

# Globals --------------------------------------------------------------------------------------------------------------
logger = structlog.get_logger(__name__)

# Call setup_logging at module level so it runs when uvicorn imports this file in worker processes
is_dev = "--reload" in sys.argv or "-r" in sys.argv or sys.stdout.isatty()
setup_logging(is_dev_mode=is_dev)

_DIST = settings.app_name.lower()
_METADATA = importlib_metadata(_DIST)
_VERSION = _METADATA["version"]
_SUMMARY = _METADATA["summary"]
_DESCRIPTION = _METADATA["description"]

try:
    _KAPTIVE_VERSION = importlib_metadata("kaptive")["version"]
except Exception:
    _KAPTIVE_VERSION = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan."""
    # 1. Initialize SQLite Database
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    await Repository.connect(db_path)
    repo = Repository(db_path)
    await repo.init_db()
    # 2. Pre-load Serotyper Pipelines into Memory
    AppState.load_databases()
    yield
    # Clean up resources if necessary on shutdown
    logger.info(f"Shutting down {settings.app_name}...")
    await Repository.close()


# App ------------------------------------------------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    summary=_SUMMARY,
    # description=_DESCRIPTION,
    version=_VERSION,
    default_response_class=KaptiveORJSONResponse,
    lifespan=lifespan,
    docs_url=None,  # Disable default docs
    middleware=[
        Middleware(GZipMiddleware, minimum_size=1000),
        Middleware(
            CORSMiddleware,
            allow_origins=getattr(settings, "cors_origins", ["http://localhost:8000", "http://127.0.0.1:8000"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        Middleware(SessionMiddleware, secret_key=getattr(settings, "secret_key", secrets.token_hex(32))),
    ],
    routes=[],
)

# Initialize Prometheus Metrics
Instrumentator().instrument(app).expose(app)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    logger.error("validation_error", errors=exc.errors(), body=exc.body)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


app.include_router(auth.router)
app.include_router(serotype.router)


@app.get("/api/version")
def get_version() -> dict[str, str | None]:
    """Get the application version."""
    return {
        "version": _VERSION,
        "kaptive_version": _KAPTIVE_VERSION,
    }


@app.get("/api/about")
def get_about() -> dict[str, str]:
    """Get the about information."""
    # Fix the logo path so the web frontend can load it correctly from the static mount
    return {"content": _DESCRIPTION.replace('src="src/kaptive_web/frontend/logo.png"', 'src="logo.png"')}


# Mount the static frontend
app.mount("/", StaticFiles(directory=Path(__file__).parent / "frontend", html=True), name="frontend")


# CLI entry point ------------------------------------------------------------------------------------------------------
def cli() -> None:
    """Run the CLI entry point."""
    parser = argparse.ArgumentParser(description=_SUMMARY)
    parser.add_argument("-H", "--host", default="127.0.0.1", metavar="STR")
    parser.add_argument("-p", "--port", type=int, default=8000, metavar="INT")
    parser.add_argument("-r", "--reload", action="store_true", default=False)
    parser.add_argument("-v", "--version", action="version", version=_VERSION, help="Show version number and exit")

    args = parser.parse_args()

    # Uvicorn requires an import string to use the reload feature
    app_target = "kaptive_web.main:app" if args.reload else app
    uvicorn.run(app_target, host=args.host, port=args.port, reload=args.reload, log_config=None)


if __name__ == "__main__":
    cli()
