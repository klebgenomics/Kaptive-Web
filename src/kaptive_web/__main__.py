from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import logfire

from kaptive_web.models import database
from kaptive_web.api import endpoints

# Create the SQLite tables automatically on startup
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Kaptive Web API",
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

def main():
    import uvicorn
    uvicorn.run("kaptive_web.__main__:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == '__main__':
    main()
