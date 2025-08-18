import json
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests
import yaml


GITHUB_API = "https://api.github.com"


def load_config(path: str = "config.yaml") -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get(url: str, params: Optional[Dict] = None) -> requests.Response:
    """Unauthenticated GET with basic error handling and tiny backoff."""
    resp = requests.get(url, params=params or {}, timeout=30)
    # Respect secondary rate limits gently
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        time.sleep(2)
        resp = requests.get(url, params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp


def fetch_all_repos(user: str) -> List[Dict]:
    """List all public repos for a user (owner + member are both public-facing via /users/:user/repos)."""
    repos: List[Dict] = []
    page = 1
    while True:
        resp = _get(f"{GITHUB_API}/users/{user}/repos", params={"per_page": 100, "page": page, "type": "owner", "sort": "full_name"})
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
        # tiny delay to be nice
        time.sleep(0.1)
    return repos


def fetch_root_items(owner: str, repo: str) -> List[str]:
    """Return names of items in the repository root (files & directories)."""
    try:
        resp = _get(f"{GITHUB_API}/repos/{owner}/{repo}/contents/")
        items = resp.json()
        names = [item.get("name", "") for item in items if isinstance(item, dict)]
        return names
    except requests.HTTPError as e:
        # Repo might be empty or inaccessible; return empty list
        return []


def fetch_readme_text(owner: str, repo: str) -> str:
    """Fetch README via the special endpoint; returns decoded text or empty string."""
    try:
        resp = _get(f"{GITHUB_API}/repos/{owner}/{repo}/readme", params={"accept": "application/vnd.github.v3.raw"})
        # If we didn't get raw, GitHub returns JSON with base64 content. Try both.
        if resp.headers.get("Content-Type", "").startswith("text/"):
            return resp.text or ""
        data = resp.json()
        if isinstance(data, dict) and "content" in data and data.get("encoding") == "base64":
            import base64
            return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return ""
    except requests.HTTPError:
        return ""


def write_jsonl(records: Iterable[Dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def extract_github_for_user(user: str, out_dir: Path) -> Path:
    repos = fetch_all_repos(user)
    lines: List[Dict] = []

    for r in repos:
        repo_name = r.get("name", "")
        full_name = r.get("full_name", f"{user}/{repo_name}")
        root_items = fetch_root_items(user, repo_name)
        readme_text = fetch_readme_text(user, repo_name)

        lines.append({
            "source": "github",
            "user": user,
            "repo_name": repo_name,
            "full_name": full_name,
            "root_items": root_items,
            "readme_text": (readme_text or "").strip()
        })

        # tiny delay to stay well within unauthenticated limits
        time.sleep(0.1)

    out_path = out_dir / f"github_{user}.jsonl"
    write_jsonl(lines, out_path)
    return out_path


def main():
    cfg = load_config("config.yaml")
    users = cfg.get("github_usernames", [])
    if not users:
        print("No github_usernames found in config.yaml")
        return

    out_dir = Path("processed")
    for u in users:
        print(f"🔎 Crawling GitHub for {u} …")
        out_path = extract_github_for_user(u, out_dir)
        print(f"✅ Wrote {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()