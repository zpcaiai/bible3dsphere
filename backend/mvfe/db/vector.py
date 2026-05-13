"""
Vector embedding utilities.
Provides embedding generation function using available APIs.
"""
import os
import logging
import hashlib
from typing import List, Optional

logger = logging.getLogger(__name__)

# In-memory cache for embeddings
_embedding_cache: dict = {}


def get_embedding_fn():
    """
    Returns an embedding function based on available API keys.
    Priority: OpenAI > Gemini text-embedding > fallback hash-based.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return _openai_embed_fn(openai_key)

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        return _gemini_embed_fn(gemini_key)

    logger.warning("[vector] No embedding API key found, using hash-based fallback")
    return _hash_embed_fn


def _openai_embed_fn(api_key: str):
    """OpenAI text-embedding-3-small."""
    import requests

    def embed(text: str) -> List[float]:
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in _embedding_cache:
            return _embedding_cache[cache_key]

        resp = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"input": text[:8000], "model": "text-embedding-3-small"},
            timeout=30,
        )
        resp.raise_for_status()
        embedding = resp.json()["data"][0]["embedding"]
        _embedding_cache[cache_key] = embedding
        return embedding

    return embed


def _gemini_embed_fn(api_key: str):
    """Gemini text-embedding."""
    import requests

    def embed(text: str) -> List[float]:
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in _embedding_cache:
            return _embedding_cache[cache_key]

        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={"model": "models/text-embedding-004", "content": {"parts": [{"text": text[:8000]}]}},
            timeout=30,
        )
        resp.raise_for_status()
        embedding = resp.json()["embedding"]["values"]
        # Pad or truncate to 1536
        if len(embedding) < 1536:
            embedding = embedding + [0.0] * (1536 - len(embedding))
        elif len(embedding) > 1536:
            embedding = embedding[:1536]
        _embedding_cache[cache_key] = embedding
        return embedding

    return embed


def _hash_embed_fn(text: str) -> List[float]:
    """Deterministic hash-based pseudo-embedding for testing without API."""
    import struct
    h = hashlib.sha512(text.encode()).digest()
    # Generate 1536 floats from repeated hashes
    result = []
    seed = h
    while len(result) < 1536:
        seed = hashlib.sha512(seed).digest()
        floats = struct.unpack(f"{len(seed)//4}f", seed[:len(seed)//4*4])
        result.extend(floats)
    # Normalize to [-1, 1]
    result = result[:1536]
    norm = max(abs(v) for v in result) or 1.0
    return [v / norm for v in result]
