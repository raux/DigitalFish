"""Similarity metrics for comparing source-code strings."""

from __future__ import annotations

import math
from collections import Counter
from typing import Callable

from rapidfuzz import fuzz
from rapidfuzz.distance import Hamming

# ---------------------------------------------------------------------------
# Available similarity method names
# ---------------------------------------------------------------------------

METHODS = ("levenshtein", "hamming", "jaccard", "cosine")


# ---------------------------------------------------------------------------
# Individual similarity functions – all return a float in [0, 1]
# ---------------------------------------------------------------------------

def levenshtein(a: str, b: str) -> float:
    """Levenshtein-based similarity via *rapidfuzz*."""
    return fuzz.ratio(a, b) / 100.0


def hamming(a: str, b: str) -> float:
    """Hamming similarity (normalised).

    Hamming distance is defined only for equal-length strings, so the shorter
    string is right-padded with null characters to match the longer one.
    """
    if not a and not b:
        return 1.0
    max_len = max(len(a), len(b))
    padded_a = a.ljust(max_len, "\0")
    padded_b = b.ljust(max_len, "\0")
    return Hamming.normalized_similarity(padded_a, padded_b)


def _tokenise(text: str) -> list[str]:
    """Split *text* into whitespace-delimited tokens."""
    return text.split()


def jaccard(a: str, b: str) -> float:
    """Jaccard similarity over whitespace tokens."""
    set_a = set(_tokenise(a))
    set_b = set(_tokenise(b))
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def cosine(a: str, b: str) -> float:
    """Cosine similarity over whitespace-token frequency vectors."""
    vec_a = Counter(_tokenise(a))
    vec_b = Counter(_tokenise(b))
    if not vec_a and not vec_b:
        return 1.0
    intersection = set(vec_a) & set(vec_b)
    dot = sum(vec_a[t] * vec_b[t] for t in intersection)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Registry / look-up
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, Callable[[str, str], float]] = {
    "levenshtein": levenshtein,
    "hamming": hamming,
    "jaccard": jaccard,
    "cosine": cosine,
}


def get_similarity_func(method: str) -> Callable[[str, str], float]:
    """Return the similarity function for *method*.

    Raises ``ValueError`` if *method* is not recognised.
    """
    try:
        return _REGISTRY[method]
    except KeyError:
        raise ValueError(
            f"Unknown similarity method {method!r}. "
            f"Choose from: {', '.join(METHODS)}"
        ) from None
