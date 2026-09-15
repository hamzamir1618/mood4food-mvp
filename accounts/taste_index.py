"""
Similar tastes: users' taste vectors in a ChromaDB collection, searched by cosine
similarity.

Neo4j is the source of truth and this index is derived from it: rebuilt at startup and
updated whenever a taste model changes, so it can live in memory on a host with no
persistent disk. Only tastes with evidence beyond the chosen persona are indexed, so two
users who merely picked the same persona don't count as similar.

Vectors are always passed in. Chroma is never asked to embed text, which would make it
download an embedding model, and its telemetry is switched off.
"""

import threading

from accounts.models import TasteModel

COLLECTION = "user_taste"

_client = None
_lock = threading.Lock()


def _collection():
    global _client
    with _lock:
        if _client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            _client = chromadb.EphemeralClient(settings=ChromaSettings(anonymized_telemetry=False))
        return _client.get_or_create_collection(
            COLLECTION, embedding_function=None, metadata={"hnsw:space": "cosine"}
        )


def _indexable(taste: TasteModel) -> bool:
    return taste.has_evidence() and any(taste.as_list())  # cosine is undefined at zero


def sync(user_id: str, taste: TasteModel) -> None:
    """Brings one user's entry in line with their taste model."""
    col = _collection()
    if _indexable(taste):
        col.upsert(ids=[user_id], embeddings=[taste.as_list()])
    else:
        col.delete(ids=[user_id])


def remove(user_id: str) -> None:
    _collection().delete(ids=[user_id])


def rebuild(models: list[tuple[str, TasteModel]]) -> int:
    """Replaces the whole index; returns how many users were indexed."""
    col = _collection()
    existing = col.get(include=[])["ids"]
    if existing:
        col.delete(ids=existing)
    usable = [(uid, t.as_list()) for uid, t in models if _indexable(t)]
    for i in range(0, len(usable), 500):
        batch = usable[i : i + 500]
        col.add(ids=[uid for uid, _ in batch], embeddings=[v for _, v in batch])
    return len(usable)


def similar(user_id: str, vector: list[float], k: int = 5) -> list[dict]:
    """The k indexed users closest to this vector by cosine similarity, excluding the user."""
    col = _collection()
    total = col.count()
    if total == 0 or not any(vector):
        return []
    res = col.query(
        query_embeddings=[list(vector)], n_results=min(k + 1, total), include=["distances"]
    )
    matches = [
        {"user_id": uid, "similarity": round(1.0 - dist, 4)}
        for uid, dist in zip(res["ids"][0], res["distances"][0])
        if uid != user_id
    ]
    return matches[:k]


def count() -> int:
    return _collection().count()
