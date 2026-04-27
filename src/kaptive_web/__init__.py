from importlib.metadata import metadata as importlib_metadata
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from kaptive_web.api import endpoints
from kaptive_web.models import database


# Constants ---
_METADATA = importlib_metadata('kaptive_web')
_KAPTIVE_METADATA = importlib_metadata("kaptive")

# Create the SQLite tables automatically on startup
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title=_METADATA["title"],
    description="High-performance backend for Kaptive bacterial genome typing.",
    version="0.1.0"
)

# logfire.configure()
# logfire.instrument_fastapi(app)

# Allow CORS if your frontend and backend end up on different ports during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the REST API routes
app.include_router(endpoints.router)

# Mount the static frontend
# This explicitly tells FastAPI to serve the HTML/JS from the `frontend` folder
FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
