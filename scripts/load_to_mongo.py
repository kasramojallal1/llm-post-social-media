# scripts/load_to_mongo.py
import json
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from pymongo import MongoClient


def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main():
    # --- Resolve repo root regardless of current working dir ---
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]   # repo/
    processed = repo_root / "processed"
    env_path = repo_root / ".env"

    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()  # fallback

    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "postcraft")
    coll_name = os.getenv("MONGODB_COLLECTION", "raw_docs")

    # Connect & ping early for a clear error if Mongo isn't running
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as e:
        print(f"❌ Could not connect to Mongo at {uri}. Is it running?")
        raise

    db = client[db_name]
    coll = db[coll_name]

    # overwrite behavior
    coll.drop()

    docs: List[Dict] = []

    # --- Collect files ---
    resume_path = processed / "resume.json"
    linkedin_path = processed / "linkedin.json"
    github_paths = sorted(processed.glob("github_*.jsonl"))
    news_path = processed / "news.jsonl"

    print(f"🔎 Looking in: {processed}")
    print(f"• resume.json exists: {resume_path.exists()}")
    print(f"• linkedin.json exists: {linkedin_path.exists()}")
    print(f"• github_*.jsonl found: {len(github_paths)}")
    print(f"• news.jsonl exists: {news_path.exists()}")

    # Resume
    if resume_path.exists():
        r = load_json(resume_path)
        docs.append({
            "source": "resume",
            "doc_type": "pdf",
            "origin_path": str(resume_path.relative_to(repo_root)),
            "metadata": {},
            "text": r.get("raw_text", "")
        })

    # LinkedIn
    if linkedin_path.exists():
        l = load_json(linkedin_path)
        docs.append({
            "source": "linkedin",
            "doc_type": "pdf",
            "origin_path": str(linkedin_path.relative_to(repo_root)),
            "metadata": {},
            "text": l.get("raw_text", "")
        })

    # GitHub
    for p in github_paths:
        rows = load_jsonl(p)
        for row in rows:
            docs.append({
                "source": "github",
                "doc_type": "jsonl",
                "origin_path": str(p.relative_to(repo_root)),
                "metadata": {
                    "user": row.get("user"),
                    "repo_name": row.get("repo_name"),
                    "full_name": row.get("full_name"),
                    "root_items": row.get("root_items", []),
                },
                "text": row.get("readme_text", "")
            })

    # News
    if news_path.exists():
        rows = load_jsonl(news_path)
        for row in rows:
            docs.append({
                "source": "news",
                "doc_type": "rss",
                "origin_path": str(news_path.relative_to(repo_root)),
                "metadata": {
                    "feed": row.get("feed"),
                    "url": row.get("url"),
                    "published": row.get("published"),
                },
                "text": row.get("summary", "")
            })

    if docs:
        coll.insert_many(docs)
        print(f"✅ Inserted {len(docs)} documents into {db_name}.{coll_name}")
    else:
        print("⚠️ No processed files found to load. Did you run `python main.py`?")

    client.close()


if __name__ == "__main__":
    main()