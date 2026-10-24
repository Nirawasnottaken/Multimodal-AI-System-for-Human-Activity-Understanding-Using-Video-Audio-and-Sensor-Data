import json
import re
import httpx
from fastapi import HTTPException
from .config import settings
from .security import safe_relative_path

SYSTEM_PROMPT = '''You are a senior software engineer generating runnable starter applications.
Return ONLY valid JSON with shape {"files":[{"path":"relative/path","content":"complete file contents"}]}.
Generate coherent, useful files and setup docs. Do not include secrets, .env files, binaries, node_modules,
build outputs, or credentials. Use the requested stack. Keep paths relative and safe. Include README,
.gitignore, .env.example, dependency manifests, and tests where appropriate. Code should be real, not TODO-only.
Never claim external integrations are configured when credentials are absent.'''
def parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try: return json.loads(text[start:end+1])
            except json.JSONDecodeError: pass
        raise HTTPException(status_code=502, detail="AI provider returned invalid JSON. Try a more specific prompt.") from exc

async def generate_files(topic: str, framework: str) -> list[dict]:
    if not settings.ai_api_key:
        raise HTTPException(status_code=503, detail="AI_API_KEY is not configured. Add it to backend/.env.")
    payload = {
        "model": settings.ai_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Create a complete project. Preferred stack: {framework}.\nRequirements:\n{topic}\nReturn JSON only."}
        ],
        "response_format": {"type": "json_object"}
    }
    url = settings.ai_base_url.rstrip("/") + "/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {settings.ai_api_key}"}, json=payload)
            if response.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"AI provider error ({response.status_code}): {response.text[:500]}")
            result = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="AI provider timed out. Try again with smaller requirements.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach the AI provider.") from exc
    try:
        parsed = parse_json_response(result["choices"][0]["message"]["content"])
        raw_files = parsed.get("files", [])
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="AI provider response did not contain a files list.") from exc
    if not isinstance(raw_files, list) or not raw_files:
        raise HTTPException(status_code=502, detail="AI returned no project files.")
    files, seen = [], set()
    for item in raw_files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("content"), str):
            continue
        try: path = safe_relative_path(item["path"])
        except ValueError: continue
        if path in seen: continue
        seen.add(path)
        content = item["content"]
        if len(content.encode("utf-8")) > 1_000_000:
            continue
        files.append({"path": path, "content": content})
        if len(files) >= 100: break
    if not files:
        raise HTTPException(status_code=502, detail="AI returned no safe files.")
    return files
