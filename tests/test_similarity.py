"""Tests for the similarity module."""

from __future__ import annotations

import pytest

from digital_ichthyologist.similarity import (
    METHODS,
    cosine,
    get_similarity_func,
    hamming,
    jaccard,
    levenshtein,
)


# ---------------------------------------------------------------------------
# Levenshtein
# ---------------------------------------------------------------------------

class TestLevenshtein:
    def test_identical(self):
        assert levenshtein("hello", "hello") == pytest.approx(1.0)

    def test_completely_different(self):
        assert levenshtein("aaa", "zzz") < 0.5

    def test_empty_strings(self):
        assert levenshtein("", "") == pytest.approx(1.0)

    def test_partial_overlap(self):
        sim = levenshtein("def foo():\n    return 1\n", "def foo():\n    return 2\n")
        assert 0.5 < sim < 1.0


# ---------------------------------------------------------------------------
# Hamming
# ---------------------------------------------------------------------------

class TestHamming:
    def test_identical(self):
        assert hamming("hello", "hello") == pytest.approx(1.0)

    def test_completely_different(self):
        assert hamming("aaa", "zzz") < 0.5

    def test_empty_strings(self):
        assert hamming("", "") == pytest.approx(1.0)

    def test_different_lengths(self):
        """Shorter string is padded; similarity should still be meaningful."""
        sim = hamming("hello", "hello world")
        assert 0.0 < sim < 1.0

    def test_single_char_difference(self):
        sim = hamming("abc", "aXc")
        assert sim == pytest.approx(2.0 / 3.0)


# ---------------------------------------------------------------------------
# Jaccard
# ---------------------------------------------------------------------------

class TestJaccard:
    def test_identical(self):
        assert jaccard("hello world", "hello world") == pytest.approx(1.0)

    def test_completely_different(self):
        assert jaccard("aaa", "zzz") == pytest.approx(0.0)

    def test_empty_strings(self):
        assert jaccard("", "") == pytest.approx(1.0)

    def test_partial_overlap(self):
        sim = jaccard("def foo bar", "def baz bar")
        # tokens: {def, foo, bar} vs {def, baz, bar} → intersection 2, union 4
        assert sim == pytest.approx(2.0 / 4.0)

    def test_subset(self):
        sim = jaccard("a b", "a b c")
        # {a, b} vs {a, b, c} → 2/3
        assert sim == pytest.approx(2.0 / 3.0)


# ---------------------------------------------------------------------------
# Cosine
# ---------------------------------------------------------------------------

class TestCosine:
    def test_identical(self):
        assert cosine("hello world", "hello world") == pytest.approx(1.0)

    def test_completely_different(self):
        assert cosine("aaa", "zzz") == pytest.approx(0.0)

    def test_empty_strings(self):
        assert cosine("", "") == pytest.approx(1.0)

    def test_partial_overlap(self):
        sim = cosine("def foo bar", "def baz bar")
        assert 0.0 < sim < 1.0

    def test_repeated_tokens(self):
        """Cosine considers term frequency, not just presence."""
        sim = cosine("a a a b", "a b b b")
        assert 0.0 < sim < 1.0


# ---------------------------------------------------------------------------
# Registry / get_similarity_func
# ---------------------------------------------------------------------------

class TestGetSimilarityFunc:
    @pytest.mark.parametrize("method", METHODS)
    def test_known_methods_return_callable(self, method):
        func = get_similarity_func(method)
        assert callable(func)
        # Sanity: identical strings → 1.0
        assert func("hello", "hello") == pytest.approx(1.0)

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="Unknown similarity method"):
            get_similarity_func("unknown_metric")

    def test_methods_tuple_complete(self):
        assert set(METHODS) == {"levenshtein", "hamming", "jaccard", "cosine"}
