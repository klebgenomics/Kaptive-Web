import uvicorn

def start_server():
    """Entry point for the command line."""
    # This points to the 'app' object inside src/kaptive_web/__main__.py
    uvicorn.run("kaptive_web.main:app", host="127.0.0.1", port=8000, reload=False)