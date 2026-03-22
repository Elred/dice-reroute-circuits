# API Layer — drc_stat_engine

## Overview

The Flask API wraps the existing `report.py` functions and exposes them over HTTP so the Vue.js front-end can call them. It lives inside `drc_stat_engine/` alongside the existing stats engine.

## Structure

```
drc_stat_engine/
├── stats/
│   ├── profiles.py
│   ├── dice.py
│   └── report.py
├── api/
│   ├── app.py          # Flask application factory + route registration
│   └── routes.py       # All route handlers
├── tests/
│   └── dice_stat_report/
└── ...
```

## Tech Stack

- **Flask** — lightweight Python web framework
- **flask-cors** — enables CORS so the Vue dev server can call the API
- **Python 3** — same virtualenv as the stat engine

## Dependencies

Add to `requirements.txt`:
```
flask
flask-cors
```

## Running

```bash
source ~/.virtualenvs/drc/bin/activate
cd drc_stat_engine/api
python app.py          # starts on http://localhost:5000
```

## Conventions

- All routes are prefixed with `/api/v1/`
- Request and response bodies are JSON
- Errors return `{"error": "<message>"}` with an appropriate HTTP status code
- The API is stateless — every request carries the full dice pool + pipeline + strategies
- Route handlers import from `drc_stat_engine.stats.report` using absolute package imports; no business logic lives in routes
- CORS is enabled for `http://localhost:5173` (Vite dev server) in development
