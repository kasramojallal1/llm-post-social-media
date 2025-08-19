from __future__ import annotations
import os
import uuid
from dataclasses import dataclass
from typing import Iterable, List

from dotenv import load_dotenv
from pymongo import MongoClient
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


# ------------------------------
# Config
# ------------------------------
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim


@dataclass
class Doc:
    _id: str
    source: str
    text: str
    metadata: dict


# ------------------------------
# Helpers
# ------------------------------
def chunk_text(text: str, size: int, overlap: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


def iter_docs(mongo_uri: str, db: str, coll: str) -> Iterable[Doc]:
    client = MongoClient(mongo_uri)
    for row in client[db][coll].find({"text": {"$ne": ""}}, projection={"text": 1, "source": 1, "metadata": 1}):
        yield Doc(
            _id=str(row.get("_id")),
            source=str(row.get("source", "")),
            text=str(row.get("text", "")),
            metadata=row.get("metadata", {}) or {},
        )
    client.close()


# ------------------------------
# Main
# ------------------------------
def main():
    load_dotenv()

    # env
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongo_db = os.getenv("MONGODB_DB", "postcraft")
    mongo_coll = os.getenv("MONGODB_COLLECTION", "raw_docs")

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    collection = os.getenv("QDRANT_COLLECTION", "postcraft_chunks")

    # clients
    qdrant = QdrantClient(url=qdrant_url, prefer_grpc=False)
    model = SentenceTransformer(EMBED_MODEL)

    # recreate collection (overwrite behavior)
    qdrant.recreate_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=model.get_sentence_embedding_dimension(), distance=Distance.COSINE),
    )

    print(f"📥 Pulling docs from Mongo: {mongo_db}.{mongo_coll}")
    docs = list(iter_docs(mongo_uri, mongo_db, mongo_coll))
    print(f"Found {len(docs)} docs with non-empty text")

    total_chunks = 0
    batch_points: List[PointStruct] = []
    BATCH = 256

    for d in tqdm(docs, desc="Chunk + embed"):
        chunks = chunk_text(d.text, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            continue

        embeds = model.encode(chunks, show_progress_bar=False, normalize_embeddings=True)

        for idx, (chunk, vec) in enumerate(zip(chunks, embeds)):
            pid = str(uuid.uuid4())
            payload = {
                "doc_id": d._id,
                "chunk_index": idx,
                "source": d.source,
                "metadata": d.metadata,
                "text": chunk,
            }
            batch_points.append(PointStruct(id=pid, vector=vec.tolist(), payload=payload))
            total_chunks += 1

            if len(batch_points) >= BATCH:
                qdrant.upsert(collection_name=collection, points=batch_points)
                batch_points.clear()

    if batch_points:
        qdrant.upsert(collection_name=collection, points=batch_points)
        batch_points.clear()

    print(f"✅ Indexed {total_chunks} chunks into Qdrant collection '{collection}'")


if __name__ == "__main__":
    main()