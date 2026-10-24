import re
from pathlib import Path
from fastapi import HTTPException

PROJECT_ID_RE = re.compile(r"^[a-f0-9]{32}$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._/-]+$")

EXCLUDED_PARTS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
    "dist", "build", ".next", ".idea", ".vscode"
}
EXCLUDED_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}

def safe_project_dir(workspace: Path, project_id: str) -> Path:
    if not PROJECT_ID_RE.fullmatch(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    path = (workspace / project_id).resolve()
    if path.parent != workspace.resolve():
        raise HTTPException(status_code=400, detail="Invalid project path")
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Project not found")
    return path

def safe_relative_path(name: str) -> str:
    if not name or len(name) > 240 or "\\" in name or name.startswith("/"):
        raise ValueError("Unsafe file path")
    p = Path(name)
    if any(part in ("", ".", "..") for part in p.parts):
        raise ValueError("Unsafe file path")
    if not SAFE_NAME_RE.fullmatch(name):
        raise ValueError("File path contains unsupported characters")
    if any(part in EXCLUDED_PARTS for part in p.parts) or p.name in EXCLUDED_NAMES:
        raise ValueError("Excluded path")
    if p.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
        raise ValueError("Credential files cannot be generated or published")
    return p.as_posix()

def should_exclude(rel: str) -> bool:
    p = Path(rel)
    return (p.name in EXCLUDED_NAMES or any(part in EXCLUDED_PARTS for part in p.parts)
            or p.name.lower().endswith((".pem", ".key", ".p12", ".pfx"))
            or p.name.lower() in {".ds_store", "thumbs.db"})
