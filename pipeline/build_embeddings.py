"""
Offline Gold-zone vector index builder for Mood4Food.

Reads Silver-zone `data/dishes_v2.csv`, constructs a contextual culinary document for each
dish, embeds all 2,545 dishes with ONNXMiniLM_L6_V2 (384-dim, ONNX Runtime, no PyTorch),
and saves L2-normalized float16 vectors to `data/dish_embeddings.npz` (~1.9 MB).

Usage:
    python -m pipeline.build_embeddings
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

import numpy as np

from tier_2.semantic_index import (
    DEFAULT_CSV_PATH,
    DEFAULT_INDEX_PATH,
    SemanticIndex,
    dish_document,
)

BATCH_SIZE = 128


def build_embeddings(
    csv_path: Path = DEFAULT_CSV_PATH,
    out_path: Path = DEFAULT_INDEX_PATH,
) -> Path:
    t0 = time.perf_counter()
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    dish_ids = [r["dish_uid"] for r in rows]
    docs = [dish_document(r) for r in rows]

    idx = SemanticIndex(index_path=out_path)
    chunks = []
    for start in range(0, len(docs), BATCH_SIZE):
        batch = docs[start : start + BATCH_SIZE]
        chunks.append(idx.embed_texts(batch))

    vectors = np.vstack(chunks).astype(np.float16)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_path,
        dish_ids=np.asarray(dish_ids),
        vectors=vectors,
    )
    elapsed = time.perf_counter() - t0
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(
        f"Built {len(dish_ids)} dish embeddings ({vectors.shape[1]}-dim float16) "
        f"-> {out_path} ({size_mb:.2f} MB) in {elapsed:.1f}s"
    )
    return out_path


if __name__ == "__main__":
    build_embeddings()
