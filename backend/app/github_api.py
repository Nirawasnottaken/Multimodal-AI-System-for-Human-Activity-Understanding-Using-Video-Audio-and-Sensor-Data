import httpx
from fastapi import HTTPException
API = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

async def github_request(method: str, url: str, token: str, **kwargs):
    headers = {**HEADERS, "Authorization": f"Bearer {token}", **kwargs.pop("headers", {})}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(method, url, headers=headers, **kwargs)
    if response.status_code == 429 or response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
        raise HTTPException(status_code=429, detail="GitHub rate limit reached. Wait and retry.")
    if response.status_code >= 400:
        try: detail = response.json().get("message", response.text[:300])
        except Exception: detail = response.text[:300]
        raise HTTPException(status_code=response.status_code, detail=f"GitHub API: {detail}")
    if response.status_code == 204: return {}
    return response.json()

async def list_repositories(token: str):
    data = await github_request("GET", API + "/user/repos?per_page=100&sort=updated", token)
    return [{"full_name": r["full_name"], "name": r["name"], "private": r["private"], "default_branch": r["default_branch"], "html_url": r["html_url"]} for r in data]

async def create_repository(token: str, name: str, description: str, private: bool):
    return await github_request("POST", API + "/user/repos", token, json={"name": name, "description": description[:350], "private": private, "auto_init": True})

async def publish_files(token: str, owner: str, repo: str, branch: str, files: list[dict], message: str):
    # Git data API creates one commit containing all files. Existing files are replaced by their paths.
    ref = await github_request("GET", f"{API}/repos/{owner}/{repo}/git/ref/heads/{branch}", token)
    base_commit = await github_request("GET", ref["object"]["url"], token)
    base_tree = await github_request("GET", base_commit["tree"]["url"], token)
    tree_items = []
    for item in files:
        blob = await github_request("POST", f"{API}/repos/{owner}/{repo}/git/blobs", token,
                                    json={"content": item["content"], "encoding": "utf-8"})
        tree_items.append({"path": item["path"], "mode": "100644", "type": "blob", "sha": blob["sha"]})
    tree = await github_request("POST", f"{API}/repos/{owner}/{repo}/git/trees", token,
                                json={"base_tree": base_tree["sha"], "tree": tree_items})
    commit = await github_request("POST", f"{API}/repos/{owner}/{repo}/git/commits", token,
                                  json={"message": message[:200], "tree": tree["sha"], "parents": [base_commit["sha"]]})
    await github_request("PATCH", f"{API}/repos/{owner}/{repo}/git/refs/heads/{branch}", token,
                         json={"sha": commit["sha"], "force": False})
    return {"commit_sha": commit["sha"], "url": f"https://github.com/{owner}/{repo}", "commit_url": commit["html_url"]}
