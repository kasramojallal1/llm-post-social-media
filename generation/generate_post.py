# generation/generate_post.py
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from openai import OpenAI

DEFAULT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_HASHTAGS_SEED = ["#AI", "#MachineLearning", "#LLMs", "#Cybersecurity"]

from generation.prompts import SYSTEM_PROMPT, build_user_prompt

def embed_query(model: SentenceTransformer, text: str):
    return model.encode([text], normalize_embeddings=True)[0].tolist()

def fetch_snippets(client: QdrantClient, coll: str, query_vec, top_k: int = 6, per_source_cap: int = 3) -> List[Dict[str, Any]]:
    hits = client.search(collection_name=coll, query_vector=query_vec, limit=top_k*2, with_payload=True)
    buckets: Dict[str, int] = {}
    results: List[Dict[str, Any]] = []
    for h in hits:
        p = h.payload or {}
        src = p.get("source", "unknown")
        if buckets.get(src, 0) >= per_source_cap:
            continue
        text = (p.get("text") or "").strip()
        if not text:
            continue
        meta = p.get("metadata") or {}
        title = meta.get("title") or meta.get("repo_name") or ""
        url = meta.get("url") or meta.get("html_url") or meta.get("link") or ""
        results.append({
            "source": src,
            "title": title,
            "url": url,
            "meta": meta,
            "text": text[:700]
        })
        buckets[src] = buckets.get(src, 0) + 1
        if len(results) >= top_k:
            break
    return results

def snippets_to_block(snips: List[Dict[str, Any]]) -> str:
    lines = []
    for i, s in enumerate(snips, 1):
        meta = s.get("meta", {})
        title = s.get("title") or "(no-title)"
        url = s.get("url") or ""
        src = s.get("source")
        lines.append(f"[{i}] source={src} | title=\"{title}\" | url={url}\nmeta={json.dumps(meta, ensure_ascii=False)}\ntext=\"{s['text']}\"")
    return "\n\n".join(lines)

def validate_output(obj: Dict[str, Any]) -> None:
    # Minimal validation; raise on failure
    if not isinstance(obj, dict):
        raise ValueError("Model did not return a JSON object.")
    for k in ["topic", "style", "draft"]:
        if k not in obj:
            raise ValueError(f"Missing key: {k}")
    if not obj["draft"].get("body"):
        raise ValueError("draft.body is empty.")
    # Basic citation presence check
    cits = obj["draft"].get("citations", [])
    if isinstance(cits, list) and len(cits) == 0:
        # allow zero, but warn
        pass

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate a LinkedIn post draft with RAG.")
    parser.add_argument("--topic", required=True, help="Topic to write about, e.g., 'LLM security'")
    parser.add_argument("--tone", default="professional", choices=["professional", "friendly", "thought-leader"])
    parser.add_argument("--length", default="short", choices=["short", "medium", "long"])
    parser.add_argument("--emojis", action="store_true")
    parser.add_argument("--no-hashtags", action="store_true", help="Disable hashtags")
    parser.add_argument("--k", type=int, default=6, help="Top-k retrieval")
    args = parser.parse_args()

    hashtags_enabled = not args.no_hashtags

    # Qdrant
    q_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    q_coll = os.getenv("QDRANT_COLLECTION", "postcraft_chunks")
    qdrant = QdrantClient(url=q_url)

    # Embedding
    embedder = SentenceTransformer(EMBED_MODEL)
    qvec = embed_query(embedder, args.topic)

    # Retrieve context
    snippets = fetch_snippets(qdrant, q_coll, qvec, top_k=args.k)

    # Build prompt
    from generation.prompts import SYSTEM_PROMPT
    block = snippets_to_block(snippets)
    user_prompt = build_user_prompt(
        topic=args.topic, tone=args.tone, length=args.length,
        emojis=args.emojis, hashtags=hashtags_enabled, top_k=args.k,
        snippets_block=block
    )

    # LLM call
    model_name = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=model_name,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )
    text = resp.choices[0].message.content

    # Parse + inject retrieval + defaults
    obj = json.loads(text)
    obj.setdefault("topic", args.topic)
    obj.setdefault("audience", ["recruiters", "hiring managers", "ml engineers"])
    obj.setdefault("style", {"tone": args.tone, "length": args.length, "emojis": args.emojis, "hashtags": hashtags_enabled})
    obj.setdefault("retrieval", {"top_k": args.k, "snippets": snippets})
    if hashtags_enabled and "hashtags" not in (obj.get("draft") or {}):
        obj["draft"].setdefault("hashtags", DEFAULT_HASHTAGS_SEED)

    validate_output(obj)

    # Save
    out_dir = Path("drafts"); out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"draft_{ts}.json"
    out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Draft saved to {out_path}")

    # Also echo a short preview
    print("\n— Preview —")
    print(obj["draft"].get("one_liner", "")[:140])
    print()
    print((obj["draft"].get("body","")[:300] + ("…" if len(obj['draft'].get('body',''))>300 else "")))
    if hashtags_enabled:
        print("\nHashtags:", " ".join(obj["draft"].get("hashtags", [])[:8]))

if __name__ == "__main__":
    main()