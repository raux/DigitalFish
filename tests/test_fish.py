"""Tests for the DigitalFish model."""

import pytest

from digital_ichthyologist.fish import DigitalFish


SIMPLE_CONTENT = "def foo():\n    pass\n    pass\n    pass\n    pass\n"
UPDATED_CONTENT = "def foo():\n    x = 1\n    return x\n    pass\n    pass\n"


class TestDigitalFishCreation:
    def test_basic_attributes(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        assert fish.name == "foo"
        assert fish.content == SIMPLE_CONTENT
        assert fish.birth_commit == "abc123"
        assert fish.age == 0
        assert fish.mutation_rate == 0.0
        assert fish.is_alive is True
        assert fish.lazarus_count == 0
        assert fish.extinction_commit is None

    def test_fish_id_is_deterministic(self):
        f1 = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        f2 = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        assert f1.fish_id == f2.fish_id

    def test_fish_id_differs_for_different_birth(self):
        f1 = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        f2 = DigitalFish("foo", SIMPLE_CONTENT, "def456")
        assert f1.fish_id != f2.fish_id

    def test_birth_commit_added_to_history(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        assert "abc123" in fish.commit_hashes


class TestDigitalFishSurvive:
    def test_age_increments(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        fish.survive(UPDATED_CONTENT, "commit2", 0.85)
        assert fish.age == 1

    def test_content_updated(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        fish.survive(UPDATED_CONTENT, "commit2", 0.85)
        assert fish.content == UPDATED_CONTENT

    def test_mutation_rate_accumulates(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        fish.survive(UPDATED_CONTENT, "commit2", 0.85)
        assert fish.mutation_rate == pytest.approx(0.15)

    def test_no_mutation_when_content_unchanged(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        fish.survive(SIMPLE_CONTENT, "commit2", 1.0)
        assert fish.mutation_rate == 0.0

    def test_commit_hash_appended(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        fish.survive(UPDATED_CONTENT, "commit2", 0.9)
        assert "commit2" in fish.commit_hashes

    def test_is_alive_remains_true(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        fish.go_extinct("commit2")
        fish.survive(UPDATED_CONTENT, "commit3", 0.9)
        assert fish.is_alive is True


class TestDigitalFishExtinction:
    def test_is_alive_set_false(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        fish.go_extinct("commit2")
        assert fish.is_alive is False

    def test_extinction_commit_recorded(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        fish.go_extinct("commit2")
        assert fish.extinction_commit == "commit2"


class TestDigitalFishResurrect:
    def test_is_alive_after_resurrection(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        fish.go_extinct("commit2")
        fish.resurrect(UPDATED_CONTENT, "commit5")
        assert fish.is_alive is True

    def test_lazarus_count_increments(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        fish.go_extinct("commit2")
        fish.resurrect(UPDATED_CONTENT, "commit5")
        assert fish.lazarus_count == 1

    def test_extinction_commit_cleared(self):
        fish = DigitalFish("foo", SIMPLE_CONTENT, "abc123")
        fish.go_extinct("commit2")
        fish.resurrect(UPDATED_CONTENT, "commit5")
        assert fish.extinction_commit is None


class TestDigitalFishLineCount:
    def test_counts_non_empty_non_comment_lines(self):
        content = "def foo():\n    # comment\n    x = 1\n    return x\n"
        fish = DigitalFish("foo", content, "abc")
        # 'def foo():' + '    x = 1' + '    return x' = 3
        assert fish.line_count == 3

    def test_empty_content(self):
        fish = DigitalFish("empty", "", "abc")
        assert fish.line_count == 0
