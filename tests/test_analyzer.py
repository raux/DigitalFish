"""Tests for the Analyzer using a synthetic in-memory commit sequence."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from digital_ichthyologist.analyzer import Analyzer, _similarity, _meaningful_lines
from digital_ichthyologist.fish import DigitalFish


# ---------------------------------------------------------------------------
# Unit tests for small helpers
# ---------------------------------------------------------------------------

class TestSimilarityHelper:
    def test_identical_strings(self):
        assert _similarity("hello", "hello") == pytest.approx(1.0)

    def test_completely_different(self):
        sim = _similarity("aaa", "zzz")
        assert sim < 0.5

    def test_partial_overlap(self):
        sim = _similarity("def foo():\n    return 1\n", "def foo():\n    return 2\n")
        assert 0.5 < sim < 1.0


class TestMeaningfulLines:
    def test_counts_code_lines(self):
        code = "def f():\n    # comment\n    x = 1\n    return x\n"
        assert _meaningful_lines(code) == 3

    def test_empty_string(self):
        assert _meaningful_lines("") == 0

    def test_only_comments(self):
        assert _meaningful_lines("# foo\n# bar\n") == 0


# ---------------------------------------------------------------------------
# Integration-style tests using mocked PyDriller Repository
# ---------------------------------------------------------------------------

def _make_modified_file(filename: str, source_code: str) -> MagicMock:
    mf = MagicMock()
    mf.filename = filename
    mf.source_code = source_code
    return mf


def _make_commit(hash_: str, modified_files: list) -> MagicMock:
    commit = MagicMock()
    commit.hash = hash_
    commit.msg = "test commit"
    commit.modified_files = modified_files
    return commit


BIG_FUNC = """\
def process_data(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result
"""

MUTATED_FUNC = """\
def process_data(items):
    result = []
    for item in items:
        if item >= 0:
            result.append(item * 3)
    return result
"""

SMALL_FUNC = "def tiny():\n    pass\n"


class TestAnalyzerWithMockedRepo:
    def _run_analyzer(self, commits: list) -> Analyzer:
        """Run analyzer against a fake sequence of commits."""
        analyzer = Analyzer("fake/repo", similarity_threshold=0.7, size_threshold=3)

        with patch("pydriller.Repository") as MockRepo:
            MockRepo.return_value.traverse_commits.return_value = iter(commits)
            analyzer.run()

        return analyzer

    def test_new_fish_born_in_first_commit(self):
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        analyzer = self._run_analyzer([commit1])
        assert len(analyzer.population) == 1
        assert analyzer.population[0].name == "process_data"

    def test_fish_survives_similar_commit(self):
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        commit2 = _make_commit("c2", [_make_modified_file("a.py", MUTATED_FUNC)])
        analyzer = self._run_analyzer([commit1, commit2])
        # Still one fish (same identity survived)
        assert len(analyzer.population) == 1
        fish = analyzer.population[0]
        assert fish.age == 1
        assert fish.is_alive is True

    def test_fish_goes_extinct(self):
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        # Second commit removes the file / function
        commit2 = _make_commit("c2", [_make_modified_file("a.py", "")])
        analyzer = self._run_analyzer([commit1, commit2])
        assert len(analyzer.population) == 1
        assert analyzer.population[0].is_alive is False

    def test_small_function_below_threshold_ignored(self):
        commit1 = _make_commit("c1", [_make_modified_file("a.py", SMALL_FUNC)])
        analyzer = self._run_analyzer([commit1])
        assert len(analyzer.population) == 0

    def test_lazarus_event_detected(self):
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        commit2 = _make_commit("c2", [_make_modified_file("a.py", "")])
        commit3 = _make_commit("c3", [_make_modified_file("a.py", BIG_FUNC)])
        analyzer = self._run_analyzer([commit1, commit2, commit3])
        # Only one fish should exist (reborn as Lazarus)
        assert len(analyzer.population) == 1
        fish = analyzer.population[0]
        assert fish.lazarus_count == 1
        assert fish.is_alive is True

    def test_multiple_fish_tracked_independently(self):
        two_funcs = BIG_FUNC + "\n" + MUTATED_FUNC.replace("process_data", "other_func")
        commit1 = _make_commit("c1", [_make_modified_file("a.py", two_funcs)])
        analyzer = self._run_analyzer([commit1])
        names = {f.name for f in analyzer.population}
        assert "process_data" in names
        assert "other_func" in names

    def test_non_python_files_ignored(self):
        commit1 = _make_commit("c1", [_make_modified_file("data.txt", BIG_FUNC)])
        analyzer = self._run_analyzer([commit1])
        assert len(analyzer.population) == 0
