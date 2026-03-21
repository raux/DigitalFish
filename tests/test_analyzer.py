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

OTHER_FUNC = """\
def other_func(data):
    result = []
    for d in data:
        if d > 0:
            result.append(d + 1)
    return result
"""

THIRD_FUNC = """\
def third_func(values):
    total = 0
    for v in values:
        total += v
    return total
"""

DISTINCT_FUNC = """\
def validate_config(config_path):
    import os
    if not os.path.exists(config_path):
        raise FileNotFoundError(config_path)
    with open(config_path) as fp:
        return fp.read()
"""


def _run_analyzer(commits: list) -> Analyzer:
    """Run an analyzer against a fake sequence of commits."""
    analyzer = Analyzer("fake/repo", similarity_threshold=0.7, size_threshold=3)

    with patch("pydriller.Repository") as MockRepo:
        MockRepo.return_value.traverse_commits.return_value = iter(commits)
        analyzer.run()

    return analyzer


class TestAnalyzerWithMockedRepo:
    def test_new_fish_born_in_first_commit(self):
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        analyzer = _run_analyzer([commit1])
        assert len(analyzer.population) == 1
        assert analyzer.population[0].name == "process_data"

    def test_fish_survives_similar_commit(self):
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        commit2 = _make_commit("c2", [_make_modified_file("a.py", MUTATED_FUNC)])
        analyzer = _run_analyzer([commit1, commit2])
        # Still one fish (same identity survived)
        assert len(analyzer.population) == 1
        fish = analyzer.population[0]
        assert fish.age == 1
        assert fish.is_alive is True

    def test_fish_goes_extinct(self):
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        # Second commit removes the file / function
        commit2 = _make_commit("c2", [_make_modified_file("a.py", "")])
        analyzer = _run_analyzer([commit1, commit2])
        assert len(analyzer.population) == 1
        assert analyzer.population[0].is_alive is False

    def test_small_function_below_threshold_ignored(self):
        commit1 = _make_commit("c1", [_make_modified_file("a.py", SMALL_FUNC)])
        analyzer = _run_analyzer([commit1])
        assert len(analyzer.population) == 0

    def test_lazarus_event_detected(self):
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        commit2 = _make_commit("c2", [_make_modified_file("a.py", "")])
        commit3 = _make_commit("c3", [_make_modified_file("a.py", BIG_FUNC)])
        analyzer = _run_analyzer([commit1, commit2, commit3])
        # Only one fish should exist (reborn as Lazarus)
        assert len(analyzer.population) == 1
        fish = analyzer.population[0]
        assert fish.lazarus_count == 1
        assert fish.is_alive is True

    def test_multiple_fish_tracked_independently(self):
        two_funcs = BIG_FUNC + "\n" + MUTATED_FUNC.replace("process_data", "other_func")
        commit1 = _make_commit("c1", [_make_modified_file("a.py", two_funcs)])
        analyzer = _run_analyzer([commit1])
        names = {f.name for f in analyzer.population}
        assert "process_data" in names
        assert "other_func" in names

    def test_non_python_files_ignored(self):
        commit1 = _make_commit("c1", [_make_modified_file("data.txt", BIG_FUNC)])
        analyzer = _run_analyzer([commit1])
        assert len(analyzer.population) == 0


# ---------------------------------------------------------------------------
# Fish-alive scenarios – fish should survive across commits
# ---------------------------------------------------------------------------

class TestFishStaysAlive:
    """Cases where fish must remain alive across commits."""

    def test_fish_survives_when_other_file_modified(self):
        """Fish in an untouched file must not go extinct."""
        commit1 = _make_commit("c1", [
            _make_modified_file("a.py", BIG_FUNC),
            _make_modified_file("b.py", OTHER_FUNC),
        ])
        # Only a.py is modified in the second commit
        commit2 = _make_commit("c2", [_make_modified_file("a.py", MUTATED_FUNC)])
        analyzer = _run_analyzer([commit1, commit2])

        alive_fish = [f for f in analyzer.population if f.is_alive]
        names = {f.name for f in alive_fish}
        assert len(alive_fish) == 2
        assert "process_data" in names
        assert "other_func" in names

    def test_fish_survives_multiple_unrelated_commits(self):
        """Fish survives through several commits that only touch other files."""
        commit1 = _make_commit("c1", [
            _make_modified_file("a.py", BIG_FUNC),
            _make_modified_file("b.py", OTHER_FUNC),
        ])
        commit2 = _make_commit("c2", [_make_modified_file("a.py", MUTATED_FUNC)])
        commit3 = _make_commit("c3", [_make_modified_file("a.py", BIG_FUNC)])
        analyzer = _run_analyzer([commit1, commit2, commit3])

        other = [f for f in analyzer.population if f.name == "other_func"][0]
        assert other.is_alive is True

    def test_all_fish_alive_when_no_deletions(self):
        """All fish should be alive when no functions are removed."""
        commit1 = _make_commit("c1", [
            _make_modified_file("a.py", BIG_FUNC),
            _make_modified_file("b.py", OTHER_FUNC),
            _make_modified_file("c.py", THIRD_FUNC),
        ])
        commit2 = _make_commit("c2", [_make_modified_file("a.py", MUTATED_FUNC)])
        analyzer = _run_analyzer([commit1, commit2])

        assert all(f.is_alive for f in analyzer.population)
        assert len(analyzer.population) == 3

    def test_fish_survives_identical_content(self):
        """Fish with unchanged content still survives."""
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        commit2 = _make_commit("c2", [_make_modified_file("a.py", BIG_FUNC)])
        analyzer = _run_analyzer([commit1, commit2])

        fish = analyzer.population[0]
        assert fish.is_alive is True
        assert fish.age == 1
        assert fish.mutation_rate == 0.0


# ---------------------------------------------------------------------------
# Lazarus event scenarios – fish that go extinct and come back
# ---------------------------------------------------------------------------

class TestLazarusEvents:
    """Cases where fish go extinct and are later resurrected."""

    def test_lazarus_after_file_deleted_and_recreated(self):
        """Fish reappearing in a re-created file counts as a Lazarus event."""
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        commit2 = _make_commit("c2", [_make_modified_file("a.py", "")])
        commit3 = _make_commit("c3", [_make_modified_file("a.py", BIG_FUNC)])
        analyzer = _run_analyzer([commit1, commit2, commit3])

        fish = analyzer.population[0]
        assert fish.lazarus_count == 1
        assert fish.is_alive is True

    def test_multiple_lazarus_events_on_same_fish(self):
        """A fish can be resurrected more than once."""
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        commit2 = _make_commit("c2", [_make_modified_file("a.py", "")])
        commit3 = _make_commit("c3", [_make_modified_file("a.py", BIG_FUNC)])
        commit4 = _make_commit("c4", [_make_modified_file("a.py", "")])
        commit5 = _make_commit("c5", [_make_modified_file("a.py", BIG_FUNC)])
        analyzer = _run_analyzer([commit1, commit2, commit3, commit4, commit5])

        fish = analyzer.population[0]
        assert fish.lazarus_count == 2
        assert fish.is_alive is True

    def test_lazarus_does_not_affect_other_fish(self):
        """A Lazarus event on one fish leaves others alive and unaffected."""
        commit1 = _make_commit("c1", [
            _make_modified_file("a.py", BIG_FUNC),
            _make_modified_file("b.py", DISTINCT_FUNC),
        ])
        commit2 = _make_commit("c2", [_make_modified_file("a.py", "")])
        commit3 = _make_commit("c3", [_make_modified_file("a.py", BIG_FUNC)])
        analyzer = _run_analyzer([commit1, commit2, commit3])

        lazarus_fish = [f for f in analyzer.population if f.name == "process_data"][0]
        other_fish = [f for f in analyzer.population if f.name == "validate_config"][0]

        assert lazarus_fish.lazarus_count == 1
        assert lazarus_fish.is_alive is True
        assert other_fish.lazarus_count == 0
        assert other_fish.is_alive is True

    def test_lazarus_fish_keeps_original_identity(self):
        """A resurrected fish keeps the same fish_id as before extinction."""
        commit1 = _make_commit("c1", [_make_modified_file("a.py", BIG_FUNC)])
        commit2 = _make_commit("c2", [_make_modified_file("a.py", "")])
        commit3 = _make_commit("c3", [_make_modified_file("a.py", BIG_FUNC)])
        analyzer = _run_analyzer([commit1, commit2, commit3])

        assert len(analyzer.population) == 1
        fish = analyzer.population[0]
        assert fish.birth_commit == "c1"
        assert fish.fish_id == hash("process_data" + "c1")
