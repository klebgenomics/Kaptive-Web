import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from kaptive_web._version import __version__
from kaptive_web.core.config import settings
from kaptive_web.core.responses import KaptiveORJSONResponse
from kaptive_web.core.state import state
from kaptive_web.db.repository import Repository
from kaptive_web.api.routes import auth, serotype

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite Database
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    await Repository.connect(db_path)
    repo = Repository(db_path)
    await repo.init_db()
    
    # 2. Pre-load Serotyper Pipelines into Memory
    print("Discovering and loading databases into memory...")
    state.init_all()
    print("Initialization complete.")
    
    yield
    
    # Clean up resources if necessary on shutdown
    print("Shutting down Kaptive-Web...")
    await Repository.close()

import fastapi_swagger_dark

app = FastAPI(
    title=settings.app_name,
    description="Web interface and API for Kaptive, the tool for in silico serotyping.",
    version=__version__,
    default_response_class=KaptiveORJSONResponse,
    lifespan=lifespan,
    docs_url=None  # Disable default docs to use fastapi_swagger_dark
)

fastapi_swagger_dark.install(app)

from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print("VALIDATION ERROR:", exc.errors())
    print("BODY:", exc.body)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

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

@app.get("/api/version")
def get_version():
    return {"version": __version__}

@app.get("/api/about")
def get_about():
    from importlib.metadata import metadata
    import os
    
    content = ""
    readme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        try:
            content = metadata("kaptive-web").get("Description", "")
        except Exception:
            content = "# About\nNo information found."
            
    # Fix the logo path so the web frontend can load it correctly from the static mount
    content = content.replace('src="docs/assets/logo.png"', 'src="logo.png"')
    content = content.replace('src="src/kaptive_web/frontend/logo.png"', 'src="logo.png"')
    
    return {"content": content}

# Mount the static frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


def cli():
    from argparse import ArgumentParser


    # Define args ------------------------------------------------------------------------------------------------------
    parser = ArgumentParser(description='Web interface for Kaptive, the tool for in silico serotyping.', prog='kaptive-web')
    parser.add_argument('-H', '--host', default='127.0.0.1', metavar='STR')
    parser.add_argument('-p', '--port', type=int, default=8000, metavar='INT')
    parser.add_argument('-r', '--reload', action='store_true', default=False)
    parser.add_argument("-v", "--version", action="version", version=__version__, help="Show version number and exit")

    # Parse args -------------------------------------------------------------------------------------------------------
    args = parser.parse_args()

    # Run app ----------------------------------------------------------------------------------------------------------
    import uvicorn
    
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
