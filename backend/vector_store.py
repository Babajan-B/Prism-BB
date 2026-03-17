import os
import pickle

import faiss
import numpy as np

FAISS_INDEX_PATH = "data/faiss_index.bin"
FAISS_IDS_PATH = "data/faiss_ids.pkl"


def _ensure_data_dir():
    os.makedirs("data", exist_ok=True)


def create_index(dimension: int = 3072) -> faiss.Index:
    """Create a new FAISS flat inner-product index (cosine similarity after L2 norm)."""
    index = faiss.IndexFlatIP(dimension)
    return index


def load_or_create_index(dimension: int = 3072) -> tuple[faiss.Index, list[str]]:
    """Load a persisted index from disk, or create a fresh one."""
    if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(FAISS_IDS_PATH):
        index = faiss.read_index(FAISS_INDEX_PATH)
        with open(FAISS_IDS_PATH, "rb") as f:
            ids: list[str] = pickle.load(f)
        return index, ids
    return create_index(dimension), []


def save_index(index: faiss.Index, ids: list[str]):
    """Persist the FAISS index and image-ID list to disk."""
    _ensure_data_dir()
    faiss.write_index(index, FAISS_INDEX_PATH)
    with open(FAISS_IDS_PATH, "wb") as f:
        pickle.dump(ids, f)


def add_embedding(
    index: faiss.Index,
    ids: list[str],
    embedding: list[float],
    image_id: str,
) -> tuple[faiss.Index, list[str]]:
    """Normalise and add a single embedding vector to the index."""
    vec = np.array([embedding], dtype=np.float32)
    faiss.normalize_L2(vec)
    index.add(vec)
    ids.append(image_id)
    return index, ids


def search_similar(
    index: faiss.Index,
    ids: list[str],
    query_embedding: list[float],
    top_k: int = 8,
    min_score: float = 0.10,
) -> list[dict]:
    """
    Return the top-k most similar image IDs with their cosine-similarity scores.
    Results with a score below min_score (0-1 scale) are filtered out.
    """
    if index.ntotal == 0:
        print(f"[FAISS] Index is empty!")
        return []

    vec = np.array([query_embedding], dtype=np.float32)
    faiss.normalize_L2(vec)

    # Search for more candidates initially
    search_k = min(top_k * 3, index.ntotal)  # Search more to account for filtering
    distances, indices = index.search(vec, search_k)
    
    print(f"[FAISS] Searched {search_k}, raw distances: {distances[0][:5]}")

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx != -1 and float(dist) >= min_score:
            results.append({"image_id": ids[idx], "score": float(dist)})
    
    print(f"[FAISS] After filtering (min_score={min_score}): {len(results)} results")
    
    # Return only top_k after filtering
    return results[:top_k]
