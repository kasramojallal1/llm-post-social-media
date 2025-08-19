import json
from pathlib import Path
from typing import Dict, Iterable, List

from dotenv import load_dotenv
from pymongo import MongoClient
import os
import glob


def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> List[Dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main():
    load_dotenv()
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "postcraft")
    coll_name = os.getenv("MONGODB_COLLECTION", "raw_docs")

    client = MongoClient(uri)
    db = client[db_name]
    coll = db[coll_name]

    # overwrite behavior
    coll.drop()

    processed = Path("processed")
    docs: List[Dict] = []

    # Resume
    resume_path = processed / "resume.json"
    if resume_path.exists():
        r = load_json(resume_path)
        docs.append({
            "source": "resume",
            "doc_type": "pdf",
            "origin_path": str(resume_path),
            "metadata": {},
            "text": r.get("raw_text", "")
        })

    # LinkedIn
    linkedin_path = processed / "linkedin.json"
    if linkedin_path.exists():
        l = load_json(linkedin_path)
        docs.append({
            "source": "linkedin",
            "doc_type": "pdf",
            "origin_path": str(linkedin_path),
            "metadata": {},
            "text": l.get("raw_text", "")
        })

    # GitHub (all users)
    for p in processed.glob("github_*.jsonl"):
        rows = load_jsonl(p)
        for row in rows:
            docs.append({
                "source": "github",
                "doc_type": "jsonl",
                "origin_path": str(p),
                "metadata": {
                    "user": row.get("user"),
                    "repo_name": row.get("repo_name"),
                    "full_name": row.get("full_name"),
                    "root_items": row.get("root_items", []),
                },
                "text": row.get("readme_text", "")
            })

    # News
    news_path = processed / "news.jsonl"
    if news_path.exists():
        rows = load_jsonl(news_path)
        for row in rows:
            docs.append({
                "source": "news",
                "doc_type": "rss",
                "origin_path": str(news_path),
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
        print("⚠️ No processed files found to load.")

    client.close()


if __name__ == "__main__":
    main()