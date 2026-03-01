"""
Local embedding generation using sentence-transformers.
Model: paraphrase-multilingual-MiniLM-L12-v2 (384 dimensions, 50+ languages including Greek).
The model is loaded once at module level and reused across requests.
"""

from functools import lru_cache
from typing import Optional

from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load model once, cache it."""
    return SentenceTransformer(MODEL_NAME)


def generate_embedding(text: str) -> Optional[list[float]]:
    """
    Generate a 384-dimensional embedding for the given text.
    Returns a list of floats, or None if text is empty.
    """
    if not text or not text.strip():
        return None
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()
