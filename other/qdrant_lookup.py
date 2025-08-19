# scripts/qdrant_peek.py
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
import os

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLL = os.getenv("QDRANT_COLLECTION", "postcraft_chunks")

client = QdrantClient(url=QDRANT_URL)

# 1) Count points
print("count:", client.count(COLL, exact=True).count)

# 2) Peek a few points (filter by source if you want)
hits = client.scroll(
    collection_name=COLL,
    limit=3,
    with_payload=True,
    with_vectors=False,
)[0]

for h in hits:
    p = h.payload
    print("— id:", h.id, "| source:", p.get("source"), "| chunk_index:", p.get("chunk_index"))
    print("  text:", (p.get("text","")[:160] + "…"))