# Backend

FastAPI backend for the AI code review tool.

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```text
GET http://localhost:8000/api/v1/health
```

