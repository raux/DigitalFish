"""Tests for the Vita HTML dashboard generator."""

from __future__ import annotations

import json

import pytest

from digital_ichthyologist.fish import DigitalFish
from digital_ichthyologist.vita import Vita


def _make_fish(name: str, age: int, alive: bool = True, lazarus: int = 0) -> DigitalFish:
    content = f"def {name}():\n    " + "\n    ".join([f"x{i} = {i}" for i in range(age + 2)])
    fish = DigitalFish(name, content, "c0")
    fish.age = age
    fish.is_alive = alive
    fish.lazarus_count = lazarus
    if not alive:
        fish.extinction_commit = "c_end"
    return fish


class TestVitaRender:
    def test_returns_html_string(self):
        pop = [_make_fish("alpha", 10)]
        v = Vita(pop, total_commits=5)
        html = v.render()
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_contains_chart_js_script(self):
        pop = [_make_fish("alpha", 10)]
        v = Vita(pop, total_commits=5)
        html = v.render()
        assert "chart.js" in html.lower() or "Chart" in html

    def test_contains_fish_names(self):
        pop = [_make_fish("process_data", 10), _make_fish("parse_config", 5)]
        v = Vita(pop, total_commits=20)
        html = v.render()
        assert "process_data" in html
        assert "parse_config" in html

    def test_contains_ecosystem_metrics(self):
        pop = [_make_fish("f1", 5), _make_fish("f2", 2, alive=False)]
        v = Vita(pop, total_commits=10)
        html = v.render()
        assert "Ecosystem Health" in html
        assert "Survival Ratio" in html
        assert "Alive" in html
        assert "Extinct" in html

    def test_contains_dashboard_sections(self):
        pop = [_make_fish("func", 3)]
        v = Vita(pop, total_commits=5)
        html = v.render()
        assert "Survival Heatmap" in html
        assert "Lazarus" in html
        assert "Population Status" in html
        assert "Age Distribution" in html
        assert "Mutation Rate" in html

    def test_empty_population(self):
        v = Vita([], total_commits=0)
        html = v.render()
        assert "<!DOCTYPE html>" in html
        assert "Total Fish" in html

    def test_vita_title_in_output(self):
        pop = [_make_fish("f", 1)]
        v = Vita(pop, total_commits=1)
        html = v.render()
        assert "Vita" in html


class TestVitaEcosystemMetrics:
    def test_metrics_with_population(self):
        pop = [_make_fish("a", 5), _make_fish("b", 3, alive=False)]
        v = Vita(pop, total_commits=10)
        metrics = v._ecosystem_metrics()
        assert metrics["total_commits"] == 10
        assert metrics["total_fish"] == 2
        assert metrics["alive"] == 1
        assert metrics["extinct"] == 1
        assert metrics["survival_ratio"] == 50.0

    def test_metrics_zero_commits(self):
        pop = [_make_fish("a", 5)]
        v = Vita(pop, total_commits=0)
        metrics = v._ecosystem_metrics()
        assert metrics["births_per_100"] == 0.0
        assert metrics["extinctions_per_100"] == 0.0

    def test_metrics_empty_population(self):
        v = Vita([], total_commits=10)
        metrics = v._ecosystem_metrics()
        assert metrics["total_fish"] == 0
        assert metrics["survival_ratio"] == 0.0
        assert metrics["avg_age"] == 0.0
        assert metrics["avg_mutation"] == 0.0

    def test_lazarus_events_counted(self):
        pop = [_make_fish("a", 5, lazarus=2), _make_fish("b", 3, lazarus=1)]
        v = Vita(pop, total_commits=10)
        metrics = v._ecosystem_metrics()
        assert metrics["lazarus_events"] == 3

    def test_births_and_extinctions_per_100(self):
        pop = [_make_fish("a", 5), _make_fish("b", 3, alive=False)]
        v = Vita(pop, total_commits=50)
        metrics = v._ecosystem_metrics()
        assert metrics["births_per_100"] == 4.0
        assert metrics["extinctions_per_100"] == 2.0


class TestVitaFishData:
    def test_fish_data_valid_json(self):
        pop = [_make_fish("func", 7)]
        v = Vita(pop, total_commits=10)
        data = json.loads(v._fish_data_json())
        assert isinstance(data, list)
        assert len(data) == 1

    def test_fish_data_fields(self):
        pop = [_make_fish("func", 7, alive=False, lazarus=2)]
        v = Vita(pop, total_commits=10)
        data = json.loads(v._fish_data_json())
        fish = data[0]
        assert fish["name"] == "func"
        assert fish["age"] == 7
        assert fish["is_alive"] is False
        assert fish["lazarus_count"] == 2
        assert "mutation_rate" in fish
        assert "line_count" in fish
        assert "birth_commit" in fish

    def test_top_n_respected_in_render(self):
        pop = [_make_fish(f"f{i}", i) for i in range(30)]
        v = Vita(pop, total_commits=50, top_n=5)
        html = v.render()
        assert "Top 5" in html


class TestVitaAllAlive:
    def test_survival_ratio_100(self):
        pop = [_make_fish("a", 3), _make_fish("b", 4)]
        v = Vita(pop, total_commits=5)
        metrics = v._ecosystem_metrics()
        assert metrics["survival_ratio"] == 100.0
        assert metrics["extinct"] == 0
