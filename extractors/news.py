import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

import feedparser

# Minimal MVP feeds (expanded for AI/ML/DL papers)
FEEDS = {
    # Core ML / AI
    "arxiv-cs.LG": "https://arxiv.org/rss/cs.LG",  # Machine Learning
    "arxiv-stat.ML": "https://arxiv.org/rss/stat.ML",
    "arxiv-cs.AI": "https://arxiv.org/rss/cs.AI",
    "arxiv-cs.CL": "https://arxiv.org/rss/cs.CL",  # Computation & Language (NLP)
    "arxiv-cs.CV": "https://arxiv.org/rss/cs.CV",  # Computer Vision
    "arxiv-cs.IR": "https://arxiv.org/rss/cs.IR",  # Information Retrieval (RAG-ish topics)
    "arxiv-cs.RO": "https://arxiv.org/rss/cs.RO",  # Robotics (often relevant)
}

MAX_AGE_DAYS = 7  # keep at most 1 week old


def _to_datetime(struct_time) -> datetime | None:
    if not struct_time:
        return None
    # feedparser returns time.struct_time in UTC
    return datetime(*struct_time[:6], tzinfo=timezone.utc)


def collect_recent_articles() -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    records: list[dict] = []

    for feed_name, url in FEEDS.items():
        parsed = feedparser.parse(url)

        for entry in parsed.entries:
            published_dt = _to_datetime(getattr(entry, "published_parsed", None)) \
                           or _to_datetime(getattr(entry, "updated_parsed", None))
            if not published_dt or published_dt < cutoff:
                continue

            rec = {
                "source": "rss",
                "feed": feed_name,
                "title": getattr(entry, "title", "").strip(),
                "url": getattr(entry, "link", "").strip(),
                "published": published_dt.isoformat(),
                "summary": getattr(entry, "summary", getattr(entry, "description", "")).strip(),
            }
            records.append(rec)

    return records


def main():
    out_path = Path("processed") / "news.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    articles = collect_recent_articles()

    with out_path.open("w", encoding="utf-8") as f:
        for a in articles:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    print(f"✅ Wrote {len(articles)} recent articles to {out_path}")


if __name__ == "__main__":
    main()