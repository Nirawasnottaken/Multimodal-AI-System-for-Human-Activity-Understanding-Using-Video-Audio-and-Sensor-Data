from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4.1-mini"
    ai_timeout_seconds: float = 120
    github_client_id: str = ""
    github_client_secret: str = ""
    github_callback_url: str = "http://localhost:8000/api/github/callback"
    frontend_url: str = "http://localhost:5173"
    session_secret: str = "development-only-change-me"
    cookie_secure: bool = False
    max_upload_mb: int = 10
    workspace_dir: str = "workspace"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE = (BASE_DIR / settings.workspace_dir).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)
