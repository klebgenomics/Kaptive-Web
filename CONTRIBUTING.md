

## Project Structure Overview
```plaintext
kaptive-web/
├── pyproject.toml
├── README.md
├── src/
│   └── kaptive_web/
│       ├── __init__.py
│       ├── main.py               # The FastAPI app instance
│       ├── cli.py                # Command-line entry point
│       ├── api/
│       │   └── endpoints.py      # The routing logic
│       ├── core/
│       │   └── config.py         # Env vars and settings
│       ├── models/
│       │   └── database.py       # SQLAlchemy Job schemas
│       ├── services/
│       │   └── runner.py         # Kaptive CLI logic execution
│       └── frontend/             # The static HTML/JS/CSS
│           ├── index.html
│           └── js/
│               └── app.js
└── tests/
```
