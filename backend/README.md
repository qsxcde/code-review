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

## GitHub PR API

Fetch pull request metadata and changed files:

```text
POST http://localhost:8000/api/v1/github/pr
Content-Type: application/json

{
  "url": "https://github.com/owner/repo/pull/123"
}
```

Private repositories require `GITHUB_TOKEN` in `.env`.

If your browser can access GitHub but the backend cannot, configure an HTTP proxy:

```env
GITHUB_API_PROXY=http://127.0.0.1:7890
```

## Mock Review Analysis API

Analyze a mock PR diff with the configured LLM:

```text
POST http://localhost:8000/api/v1/review/mock-analyze
Content-Type: application/json

{
  "prUrl": "https://github.com/owner/repo/pull/123",
  "title": "Add login validation",
  "description": "Validate user input before login",
  "author": "developer",
  "baseBranch": "main",
  "headBranch": "feature/login-validation",
  "files": [
    {
      "filename": "src/auth/login.ts",
      "status": "modified",
      "additions": 12,
      "deletions": 2,
      "patch": "@@ -10,6 +10,12 @@ ..."
    }
  ]
}
```

This endpoint requires `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env`. If you use an OpenAI-compatible provider, also configure `OPENAI_BASE_URL`.
