# AI Project Builder

A full-stack starter application for turning a project specification into a downloadable codebase and optionally publishing it to GitHub.

## Features
- React + Vite frontend with topic entry, document upload, framework choice, generation progress, file explorer and code preview.
- FastAPI backend with real AI-provider integration (OpenAI-compatible Chat Completions API), project analysis/generation endpoints, safe ZIP downloads, and GitHub OAuth + repository publishing.
- PDF, DOCX, TXT, Markdown and common image uploads (image OCR requires Tesseract; PDF parsing uses PyMuPDF).
- Server-side secrets, OAuth state verification, signed session cookies, file/path validation, ZIP exclusions, and explicit publish confirmation in the UI.
- Generated projects stored in a local workspace directory; suitable for local development. Add persistent storage and deployment hardening before production.

## Requirements
- Python 3.11+
- Node.js 20+
- An AI provider API key compatible with the OpenAI Chat Completions API (optional until generation is used)
- GitHub OAuth App credentials (optional until GitHub publishing is used)

## Quick start

### 1. Configure backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Edit `backend/.env`. Set `SESSION_SECRET` to a long random value. Set `AI_API_KEY` and `AI_BASE_URL`/`AI_MODEL` for your provider. Defaults target OpenAI's API.

For GitHub:
1. Create a GitHub OAuth App in GitHub Developer Settings.
2. Set its callback URL to `http://localhost:8000/api/github/callback`.
3. Add `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and `GITHUB_CALLBACK_URL` to `.env`.
4. Set `FRONTEND_URL=http://localhost:5173`.
5. The OAuth scope is `repo` because publishing to private repositories requires it. If your use case is public repositories only, replace it with the narrower `public_repo` scope.

### 2. Start backend
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Start frontend
In another terminal:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`.

## API endpoints
- `POST /api/projects/analyze`
- `POST /api/projects/generate` (multipart form: `topic`, `framework`, optional `files`)
- `GET /api/projects/{project_id}/files`
- `GET /api/projects/{project_id}/download`
- `GET /api/github/login`
- `GET /api/github/callback`
- `GET /api/github/status`
- `GET /api/github/repositories`
- `POST /api/github/publish`

Interactive API docs: `http://localhost:8000/docs`.

## Safety and limitations
- AI generation requires a valid provider key and may incur provider charges.
- GitHub publishing requires OAuth app configuration and user authorization. The app never asks for a GitHub password or PAT.
- OAuth tokens are kept in the signed, HTTP-only session cookie in this development implementation. For production, store tokens server-side in an encrypted database/session store and keep only an opaque session ID in the cookie; set `COOKIE_SECURE=true` behind HTTPS.
- Local project storage is not multi-user isolated. Before deploying for multiple users, add authenticated users, per-user ownership checks, quotas, persistent storage, CSRF protection for state-changing endpoints, rate limiting, and a secrets scanner.
- Generated code is untrusted content. Review it before running or publishing.
- The GitHub publish endpoint requires `confirm: true`. Existing paths are created or updated on the selected branch; conflicting repository history or permissions are reported as errors.
- Image OCR requires system Tesseract. Install it separately and ensure `pytesseract` can find the executable.
- Upload size is capped at 10 MB per file; generation output is capped by provider response and server-side file validation.

## Tests
```bash
cd backend
pytest
```

## Production checklist
Use HTTPS, secure server-side sessions, CSRF protection, user authentication/ownership, rate limiting, audit logs, malware scanning, encrypted token storage, and a managed database/object store before public deployment.
