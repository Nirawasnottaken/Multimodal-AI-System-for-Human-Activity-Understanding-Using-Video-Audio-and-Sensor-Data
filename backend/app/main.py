import json, secrets, uuid, zipfile, io, re, time
from pathlib import Path
from urllib.parse import urlencode
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import httpx
from .config import settings, WORKSPACE
from .security import safe_project_dir, safe_relative_path, should_exclude
from .documents import extract_text
from .ai import generate_files
from .github_api import list_repositories, create_repository, publish_files, github_request

app = FastAPI(title="AI Project Builder API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_url], allow_credentials=True, allow_methods=["GET","POST"], allow_headers=["Content-Type"])
serializer = URLSafeTimedSerializer(settings.session_secret, salt="aipb-session")
oauth_states = {}  # local-development only; use a shared store in production
server_sessions = {}  # tokens remain server-side; use Redis/database in production

def session_id(request: Request) -> str | None:
    raw = request.cookies.get("aipb_session")
    if not raw: return None
    try: return serializer.loads(raw, max_age=60*60*24*7)
    except (BadSignature, SignatureExpired): return None

def session_data(request: Request) -> dict:
    sid = session_id(request)
    return server_sessions.get(sid, {}).copy() if sid else {}

def set_session(response, data: dict):
    # A random opaque identifier is signed into the cookie; OAuth tokens are never serialized into it.
    sid = secrets.token_urlsafe(32)
    server_sessions[sid] = data.copy()
    response.set_cookie("aipb_session", serializer.dumps(sid), httponly=True, secure=settings.cookie_secure,
                        samesite="lax", max_age=60*60*24*7, path="/")

@app.get("/api/health")
def health():
    return {"status":"ok", "ai_configured": bool(settings.ai_api_key), "github_configured": bool(settings.github_client_id and settings.github_client_secret)}

@app.post("/api/projects/analyze")
async def analyze(topic: str = Form(""), files: list[UploadFile] = File(default=[])):
    parts = [topic.strip()] if topic.strip() else []
    max_bytes = settings.max_upload_mb * 1024 * 1024
    for f in files:
        data = await f.read(max_bytes + 1)
        if len(data) > max_bytes: raise HTTPException(413, detail=f"{f.filename} exceeds {settings.max_upload_mb} MB.")
        try: extracted = extract_text(f.filename or "upload.txt", data)
        except ValueError as exc: raise HTTPException(400, detail=str(exc))
        if extracted: parts.append(f"\n--- Extracted from {f.filename} ---\n{extracted}")
    specification = "\n".join(parts).strip()
    if not specification: raise HTTPException(400, detail="Enter a project topic or upload a readable specification.")
    return {"specification": specification[:100_000], "summary": specification[:1200], "characters": len(specification)}

@app.post("/api/projects/generate")
async def generate(topic: str = Form(...), framework: str = Form("React + FastAPI"), files: list[UploadFile] = File(default=[])):
    parts = [topic.strip()] if topic.strip() else []
    max_bytes = settings.max_upload_mb * 1024 * 1024
    for f in files:
        data = await f.read(max_bytes + 1)
        if len(data) > max_bytes: raise HTTPException(413, detail=f"{f.filename} exceeds {settings.max_upload_mb} MB.")
        try: text = extract_text(f.filename or "upload.txt", data)
        except ValueError as exc: raise HTTPException(400, detail=str(exc))
        if text: parts.append(f"\n--- {f.filename} ---\n{text}")
    spec = "\n".join(parts).strip()
    if len(spec) < 8: raise HTTPException(400, detail="Provide a more detailed project topic.")
    if len(spec) > 100_000: spec = spec[:100_000]
    generated = await generate_files(spec, framework)
    project_id = uuid.uuid4().hex
    project_dir = (WORKSPACE / project_id).resolve()
    project_dir.mkdir(parents=True)
    for item in generated:
        rel = safe_relative_path(item["path"])
        target = (project_dir / rel).resolve()
        if project_dir not in target.parents: raise HTTPException(400, detail="Unsafe generated path")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item["content"], encoding="utf-8")
    meta = {"project_id": project_id, "topic": spec[:500], "framework": framework, "created_at": int(time.time())}
    (project_dir / "project-meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return {"project_id": project_id, "framework": framework, "files": [{"path":f["path"],"size":len(f["content"].encode())} for f in generated], "count":len(generated)}

@app.get("/api/projects/{project_id}/files")
def get_files(project_id: str):
    root = safe_project_dir(WORKSPACE, project_id)
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file(): continue
        rel = path.relative_to(root).as_posix()
        if rel == "project-meta.json" or should_exclude(rel): continue
        files.append({"path":rel,"size":path.stat().st_size})
    return {"project_id":project_id,"files":files}

@app.get("/api/projects/{project_id}/file")
def get_file(project_id: str, path: str):
    root = safe_project_dir(WORKSPACE, project_id)
    try: rel = safe_relative_path(path)
    except ValueError as exc: raise HTTPException(400, detail=str(exc))
    target = (root / rel).resolve()
    if root not in target.parents or not target.is_file() or should_exclude(rel): raise HTTPException(404, detail="File not found")
    if target.stat().st_size > 1_000_000: raise HTTPException(413, detail="File too large to preview")
    return {"path":rel,"content":target.read_text(encoding="utf-8", errors="replace")}

@app.get("/api/projects/{project_id}/download")
def download(project_id: str):
    root = safe_project_dir(WORKSPACE, project_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in root.rglob("*"):
            if not path.is_file(): continue
            rel = path.relative_to(root).as_posix()
            if rel == "project-meta.json" or should_exclude(rel): continue
            archive.write(path, arcname=f"generated-project/{rel}")
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition":f'attachment; filename="ai-project-{project_id[:8]}.zip"'})

@app.get("/api/github/login")
def github_login(request: Request):
    if not settings.github_client_id or not settings.github_client_secret: raise HTTPException(503, detail="GitHub OAuth is not configured.")
    state = secrets.token_urlsafe(32)
    oauth_states[state] = int(time.time())
    url = "https://github.com/login/oauth/authorize?" + urlencode({"client_id":settings.github_client_id,"redirect_uri":settings.github_callback_url,"scope":"repo","state":state})
    return RedirectResponse(url)

@app.get("/api/github/callback")
async def github_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error: return RedirectResponse(settings.frontend_url + "/?github_error=authorization_denied")
    created = oauth_states.pop(state, None)
    if not created or time.time() - created > 600: raise HTTPException(400, detail="Invalid or expired OAuth state. Please reconnect GitHub.")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post("https://github.com/login/oauth/access_token", headers={"Accept":"application/json"},
            json={"client_id":settings.github_client_id,"client_secret":settings.github_client_secret,"code":code,"redirect_uri":settings.github_callback_url})
    if response.status_code >= 400: raise HTTPException(502, detail="GitHub token exchange failed.")
    payload = response.json()
    if not payload.get("access_token"): raise HTTPException(502, detail="GitHub did not return an access token.")
    old = session_data(request)
    old.update({"github_token":payload["access_token"]})
    resp = RedirectResponse(settings.frontend_url + "/?github=connected")
    set_session(resp, old)
    return resp

@app.get("/api/github/status")
def github_status(request: Request):
    data = session_data(request)
    return {"connected": bool(data.get("github_token"))}

@app.get("/api/github/repositories")
async def github_repositories(request: Request):
    token = session_data(request).get("github_token")
    if not token: raise HTTPException(401, detail="Connect GitHub first.")
    return {"repositories": await list_repositories(token)}

@app.post("/api/github/publish")
async def github_publish(request: Request):
    token = session_data(request).get("github_token")
    if not token: raise HTTPException(401, detail="Connect GitHub first.")
    body = await request.json()
    if body.get("confirm") is not True: raise HTTPException(400, detail="Explicit publish confirmation is required.")
    project_id = body.get("project_id","")
    root = safe_project_dir(WORKSPACE, project_id)
    branch = body.get("branch","main").strip()
    if not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", branch) or ".." in branch: raise HTTPException(400, detail="Invalid branch name.")
    files = []
    for path in root.rglob("*"):
        if not path.is_file(): continue
        rel = path.relative_to(root).as_posix()
        if rel == "project-meta.json" or should_exclude(rel): continue
        try: rel = safe_relative_path(rel)
        except ValueError: continue
        content = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?i)(-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})", content):
            raise HTTPException(400, detail=f"Possible secret detected in {rel}; remove it before publishing.")
        files.append({"path":rel,"content":content})
    if not files: raise HTTPException(400, detail="No publishable files.")
    repo_name = body.get("repository","").strip()
    owner_repo = body.get("existing_repository","").strip()
    if repo_name:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", repo_name): raise HTTPException(400, detail="Invalid repository name.")
        repo = await create_repository(token, repo_name, body.get("description",""), bool(body.get("private",True)))
        full = repo["full_name"]
        owner, name = full.split("/",1)
        # Newly created repository may not yet have a branch; seed it via contents API then use publish API on next update.
        first = files[0]
        await github_request("PUT", f"https://api.github.com/repos/{owner}/{name}/contents/{first['path']}", token,
             json={"message":"Initial project files","content":__import__("base64").b64encode(first["content"].encode()).decode(),"branch":repo.get("default_branch","main")})
        rest = files[1:]
        if rest:
            result = await publish_files(token, owner, name, repo.get("default_branch","main"), rest, body.get("commit_message","Add generated project"))
            return {"url":repo["html_url"],"commit_url":result["commit_url"],"commit_sha":result["commit_sha"],"published_files":len(files)}
        return {"url":repo["html_url"],"commit_url":repo["html_url"]+"/commits/"+repo.get("default_branch","main"),"published_files":len(files)}
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", owner_repo): raise HTTPException(400, detail="Select a valid existing repository.")
    owner, name = owner_repo.split("/",1)
    result = await publish_files(token, owner, name, branch, files, body.get("commit_message","Add generated project"))
    return {"url":result["url"],"commit_url":result["commit_url"],"commit_sha":result["commit_sha"],"published_files":len(files)}

@app.post("/api/github/logout")
def github_logout(request: Request):
    sid = session_id(request)
    if sid: server_sessions.pop(sid, None)
    resp = JSONResponse({"connected":False})
    resp.delete_cookie("aipb_session", path="/")
    return resp
