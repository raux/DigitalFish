"""Tests for the Reporter."""

from __future__ import annotations

import json

import pytest

from digital_ichthyologist.fish import DigitalFish
from digital_ichthyologist.reporter import Reporter


def _make_fish(name: str, age: int, alive: bool = True, lazarus: int = 0) -> DigitalFish:
    content = f"def {name}():\n    " + "\n    ".join([f"x{i} = {i}" for i in range(age + 2)])
    fish = DigitalFish(name, content, "c0")
    fish.age = age
    fish.is_alive = alive
    fish.lazarus_count = lazarus
    if not alive:
        fish.extinction_commit = "c_end"
    return fish


class TestSurvivalHeatmap:
    def test_empty_population(self):
        r = Reporter([])
        output = r.survival_heatmap()
        assert "No fish" in output

    def test_shows_fish_names(self):
        population = [_make_fish("alpha", 10), _make_fish("beta", 3, alive=False)]
        r = Reporter(population)
        output = r.survival_heatmap()
        assert "alpha" in output
        assert "beta" in output

    def test_shows_status(self):
        population = [_make_fish("alive_fish", 5), _make_fish("dead_fish", 2, alive=False)]
        r = Reporter(population)
        output = r.survival_heatmap()
        assert "alive" in output
        assert "extinct" in output

    def test_sorted_by_age_descending(self):
        population = [_make_fish("young", 1), _make_fish("old", 50)]
        r = Reporter(population)
        output = r.survival_heatmap()
        # "old" should appear before "young" in the output
        assert output.index("old") < output.index("young")

    def test_shows_line_count(self):
        population = [_make_fish("func", 5)]
        r = Reporter(population)
        output = r.survival_heatmap()
        assert "Lines" in output
        assert str(population[0].line_count) in output


class TestLazarusReport:
    def test_no_lazarus_events(self):
        population = [_make_fish("foo", 5)]
        r = Reporter(population)
        output = r.lazarus_report()
        assert "No Lazarus" in output

    def test_lazarus_fish_listed(self):
        population = [_make_fish("immortal", 10, lazarus=3)]
        r = Reporter(population)
        output = r.lazarus_report()
        assert "immortal" in output
        assert "3" in output

    def test_sorted_by_resurrection_count(self):
        pop = [_make_fish("twice", 5, lazarus=2), _make_fish("once", 3, lazarus=1)]
        r = Reporter(pop)
        output = r.lazarus_report()
        assert output.index("twice") < output.index("once")

    def test_shows_line_count(self):
        population = [_make_fish("phoenix", 4, lazarus=1)]
        r = Reporter(population)
        output = r.lazarus_report()
        assert "Lines" in output
        assert str(population[0].line_count) in output


class TestEcosystemHealth:
    def test_no_commits(self):
        r = Reporter([_make_fish("f", 1)])
        output = r.ecosystem_health(0)
        assert "No commits" in output

    def test_metrics_present(self):
        pop = [_make_fish("f1", 5), _make_fish("f2", 2, alive=False)]
        r = Reporter(pop)
        output = r.ecosystem_health(10)
        assert "Commits analysed" in output
        assert "Survival ratio" in output
        assert "Lazarus" in output

    def test_survival_ratio_all_alive(self):
        pop = [_make_fish("a", 3), _make_fish("b", 4)]
        r = Reporter(pop)
        output = r.ecosystem_health(5)
        assert "100.0%" in output


class TestToJson:
    def test_valid_json(self):
        pop = [_make_fish("bar", 3)]
        r = Reporter(pop)
        data = json.loads(r.to_json())
        assert isinstance(data, list)
        assert data[0]["name"] == "bar"

    def test_json_fields_present(self):
        pop = [_make_fish("baz", 2, alive=False)]
        r = Reporter(pop)
        data = json.loads(r.to_json())
        keys = data[0].keys()
        assert "fish_id" in keys
        assert "birth_commit" in keys
        assert "lazarus_count" in keys
        assert "commit_hashes" in keys
