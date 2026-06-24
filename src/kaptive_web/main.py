from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kaptive_web.core.config import settings
from kaptive_web.core.responses import KaptiveORJSONResponse
from kaptive_web.core.state import state
from kaptive_web.db.repository import Repository
from kaptive_web.api.routes import auth, serotype

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite Database
    repo = Repository(settings.database_url.replace("sqlite+aiosqlite:///", ""))
    await repo.init_db()
    
    # 2. Pre-load Serotyper Pipelines into Memory
    print("Discovering and loading databases into memory...")
    state.init_all()
    print("Initialization complete.")
    
    yield
    
    # Clean up resources if necessary on shutdown
    print("Shutting down Kaptive-Web...")

app = FastAPI(
    title=settings.app_name,
    description="Web interface and API for Kaptive, the tool for in silico serotyping.",
    version="0.1.0",
    default_response_class=KaptiveORJSONResponse,
    lifespan=lifespan
)

from starlette.middleware.sessions import SessionMiddleware
import secrets

app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_hex(32)
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Should be restricted in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(serotype.router)

from kaptive_web._version import __version__

@app.get("/api/version")
def get_version():
    return {"version": __version__}

import os
from fastapi.staticfiles import StaticFiles

# Mount the static frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
