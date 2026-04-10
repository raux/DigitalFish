"""Tests for the bubbletea-style TUI module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from digital_ichthyologist.tui import (
    DigitalIchthyologistApp,
    SetupScreen,
    LoadingScreen,
    ResultsScreen,
    ErrorScreen,
    run_tui,
    _SIMILARITY_OPTIONS,
    _OUTPUT_OPTIONS,
)
from digital_ichthyologist.fish import DigitalFish
from digital_ichthyologist.similarity import METHODS as SIMILARITY_METHODS


# ---------------------------------------------------------------------------
# SetupScreen unit tests
# ---------------------------------------------------------------------------

class TestSetupScreenDefaults:
    """Verify the SetupScreen stores and exposes its default values."""

    def test_default_values(self):
        screen = SetupScreen()
        assert screen._defaults["repo"] == ""
        assert screen._defaults["similarity_threshold"] == 0.7
        assert screen._defaults["similarity_method"] == "levenshtein"
        assert screen._defaults["size_threshold"] == 5
        assert screen._defaults["branch"] == ""
        assert screen._defaults["from_commit"] == ""
        assert screen._defaults["to_commit"] == ""
        assert screen._defaults["output"] == "text"
        assert screen._defaults["top_n"] == 20
        assert screen._defaults["out_file"] == ""

    def test_custom_defaults(self):
        screen = SetupScreen(
            repo="/my/repo",
            similarity_threshold=0.9,
            similarity_method="jaccard",
            size_threshold=10,
            branch="develop",
            from_commit="abc",
            to_commit="def",
            output="json",
            top_n=50,
            out_file="out.json",
        )
        assert screen._defaults["repo"] == "/my/repo"
        assert screen._defaults["similarity_threshold"] == 0.9
        assert screen._defaults["similarity_method"] == "jaccard"
        assert screen._defaults["size_threshold"] == 10
        assert screen._defaults["branch"] == "develop"
        assert screen._defaults["from_commit"] == "abc"
        assert screen._defaults["to_commit"] == "def"
        assert screen._defaults["output"] == "json"
        assert screen._defaults["top_n"] == 50
        assert screen._defaults["out_file"] == "out.json"

    def test_none_branch_converted_to_empty_string(self):
        screen = SetupScreen(branch=None)
        assert screen._defaults["branch"] == ""

    def test_none_out_file_converted_to_empty_string(self):
        screen = SetupScreen(out_file=None)
        assert screen._defaults["out_file"] == ""


# ---------------------------------------------------------------------------
# Similarity / output options
# ---------------------------------------------------------------------------

class TestFormOptions:
    """Verify the dropdown options match the registered similarity methods."""

    def test_similarity_options_match_registry(self):
        option_values = [v for _, v in _SIMILARITY_OPTIONS]
        for method in SIMILARITY_METHODS:
            assert method in option_values

    def test_output_options_present(self):
        option_values = [v for _, v in _OUTPUT_OPTIONS]
        assert "text" in option_values
        assert "json" in option_values
        assert "vita" in option_values


# ---------------------------------------------------------------------------
# LoadingScreen unit tests
# ---------------------------------------------------------------------------

class TestLoadingScreen:
    """Verify the LoadingScreen stores its configuration."""

    def test_stores_analyzer_kwargs(self):
        kwargs = {"repo_path": "/some/path", "similarity_threshold": 0.8}
        screen = LoadingScreen(
            analyzer_kwargs=kwargs,
            top_n=10,
            out_file="test.txt",
            output_format="json",
        )
        assert screen._analyzer_kwargs == kwargs
        assert screen._top_n == 10
        assert screen._out_file == "test.txt"
        assert screen._output_format == "json"

    def test_default_output_format(self):
        screen = LoadingScreen(
            analyzer_kwargs={"repo_path": "/x"},
            top_n=20,
            out_file=None,
        )
        assert screen._output_format == "text"


# ---------------------------------------------------------------------------
# ResultsScreen unit tests
# ---------------------------------------------------------------------------

def _make_fish(name: str, alive: bool = True, age: int = 3) -> DigitalFish:
    fish = DigitalFish(name, "def f(): pass\n  x=1\n  y=2\n  z=3\n  return\n", "c1")
    for i in range(age):
        fish.survive(f"content_{i}", f"c{i+2}", 0.9)
    if not alive:
        fish.go_extinct("cx")
    return fish


class TestResultsScreen:
    """Verify the ResultsScreen stores its configuration."""

    def test_stores_population_and_format(self):
        pop = [_make_fish("alpha")]
        screen = ResultsScreen(
            population=pop,
            total_commits=5,
            top_n=10,
            out_file=None,
            output_format="vita",
        )
        assert screen._population == pop
        assert screen._total_commits == 5
        assert screen._top_n == 10
        assert screen._output_format == "vita"

    def test_default_output_format(self):
        screen = ResultsScreen(
            population=[],
            total_commits=0,
            top_n=20,
            out_file=None,
        )
        assert screen._output_format == "text"


# ---------------------------------------------------------------------------
# ErrorScreen unit tests
# ---------------------------------------------------------------------------

class TestErrorScreen:
    """Verify the ErrorScreen stores its error message."""

    def test_stores_error(self):
        screen = ErrorScreen("something went wrong")
        assert screen._error == "something went wrong"


# ---------------------------------------------------------------------------
# App construction tests
# ---------------------------------------------------------------------------

class TestDigitalIchthyologistApp:
    """Verify the App routes to the correct initial screen."""

    def test_app_with_analyzer_kwargs(self):
        app = DigitalIchthyologistApp(
            analyzer_kwargs={"repo_path": "/test"},
            top_n=15,
            out_file="out.txt",
            output_format="json",
        )
        assert app._analyzer_kwargs is not None
        assert app._top_n == 15
        assert app._output_format == "json"

    def test_app_without_analyzer_kwargs(self):
        app = DigitalIchthyologistApp(
            setup_defaults={"repo": "/prefilled"},
        )
        assert app._analyzer_kwargs is None
        assert app._setup_defaults == {"repo": "/prefilled"}

    def test_app_defaults(self):
        app = DigitalIchthyologistApp()
        assert app._analyzer_kwargs is None
        assert app._top_n == 20
        assert app._output_format == "text"
        assert app._setup_defaults == {}


# ---------------------------------------------------------------------------
# run_tui function tests
# ---------------------------------------------------------------------------

class TestRunTui:
    """Verify run_tui constructs and runs the App correctly."""

    @patch("digital_ichthyologist.tui.DigitalIchthyologistApp")
    def test_run_tui_with_analyzer_kwargs(self, MockApp):
        kwargs = {"repo_path": "/test"}
        run_tui(analyzer_kwargs=kwargs, top_n=5, out_file="x.json", output_format="json")
        MockApp.assert_called_once_with(
            analyzer_kwargs=kwargs,
            top_n=5,
            out_file="x.json",
            output_format="json",
            setup_defaults={},
        )
        MockApp.return_value.run.assert_called_once()

    @patch("digital_ichthyologist.tui.DigitalIchthyologistApp")
    def test_run_tui_with_setup_defaults(self, MockApp):
        defaults = {"repo": "/prefilled", "top_n": 30}
        run_tui(setup_defaults=defaults)
        MockApp.assert_called_once_with(
            analyzer_kwargs=None,
            top_n=20,
            out_file=None,
            output_format="text",
            setup_defaults=defaults,
        )
        MockApp.return_value.run.assert_called_once()

    @patch("digital_ichthyologist.tui.DigitalIchthyologistApp")
    def test_run_tui_defaults(self, MockApp):
        run_tui()
        MockApp.assert_called_once_with(
            analyzer_kwargs=None,
            top_n=20,
            out_file=None,
            output_format="text",
            setup_defaults={},
        )
        MockApp.return_value.run.assert_called_once()


# ---------------------------------------------------------------------------
# CLI integration – TUI path
# ---------------------------------------------------------------------------

class TestCliTuiIntegration:
    """Verify the CLI routes to the TUI correctly."""

    @patch("digital_ichthyologist.tui.DigitalIchthyologistApp")
    @patch("sys.stdout")
    def test_cli_no_repo_launches_setup(self, mock_stdout, MockApp):
        mock_stdout.isatty.return_value = True
        from digital_ichthyologist.cli import main
        result = main([])
        assert result == 0
        # Should have been called with no analyzer_kwargs (setup form mode)
        call_kwargs = MockApp.call_args[1]
        assert call_kwargs["analyzer_kwargs"] is None
        assert "setup_defaults" in call_kwargs

    @patch("digital_ichthyologist.tui.DigitalIchthyologistApp")
    @patch("sys.stdout")
    def test_cli_with_repo_skips_setup(self, mock_stdout, MockApp):
        mock_stdout.isatty.return_value = True
        from digital_ichthyologist.cli import main
        result = main(["/some/repo"])
        assert result == 0
        call_kwargs = MockApp.call_args[1]
        assert call_kwargs["analyzer_kwargs"] is not None
        assert call_kwargs["analyzer_kwargs"]["repo_path"] == "/some/repo"

    def test_cli_no_tui_no_repo_errors(self):
        from digital_ichthyologist.cli import main
        with pytest.raises(SystemExit):
            main(["--no-tui"])
