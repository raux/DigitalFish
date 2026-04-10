"""Bubbletea-style TUI for Digital Ichthyologist, powered by Textual."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

from .analyzer import Analyzer
from .fish import DigitalFish
from .reporter import Reporter
from .similarity import METHODS as SIMILARITY_METHODS
from .vita import Vita


# ---------------------------------------------------------------------------
# CSS stylesheet
# ---------------------------------------------------------------------------

CSS = """
SetupScreen {
    background: $surface;
}

#setup-container {
    align: center middle;
    height: auto;
    max-width: 80;
    padding: 1 2;
}

#setup-title {
    text-align: center;
    text-style: bold;
    color: $accent;
    margin-bottom: 1;
}

#setup-subtitle {
    text-align: center;
    color: $text-muted;
    margin-bottom: 2;
}

.form-label {
    margin-top: 1;
    color: $text;
    text-style: bold;
}

.form-hint {
    color: $text-muted;
    margin-bottom: 0;
}

#setup-container Input {
    margin-bottom: 0;
}

#setup-container Select {
    margin-bottom: 0;
}

.switch-row {
    height: 3;
    margin-top: 1;
}

.switch-row Label {
    padding: 1 1;
}

.switch-row Switch {
    width: auto;
}

#analyse-button {
    margin-top: 2;
    width: 100%;
}

#setup-error {
    color: $error;
    text-align: center;
    margin-top: 1;
}

LoadingScreen {
    background: $surface;
}

#loading-container {
    align: center middle;
    height: 100%;
}

#loading-title {
    text-align: center;
    text-style: bold;
    color: $accent;
    margin-bottom: 1;
}

#loading-repo {
    text-align: center;
    color: $text-muted;
    margin-bottom: 2;
}

#loading-bar {
    width: 60%;
    margin-bottom: 1;
}

#loading-status {
    text-align: center;
    color: $text-muted;
}

#loading-log {
    width: 60%;
    height: auto;
    max-height: 8;
    border: round $accent-darken-2;
    padding: 0 1;
    margin-top: 2;
}

ResultsScreen TabbedContent {
    height: 1fr;
}

ResultsScreen DataTable {
    height: 100%;
}

#ecosystem-scroll {
    padding: 1 2;
}

#ecosystem-content {
    padding: 1 2;
}

.stat-header {
    color: $accent;
    text-style: bold;
    margin-top: 1;
}

.stat-value {
    color: $text;
}
"""


# ---------------------------------------------------------------------------
# Custom messages
# ---------------------------------------------------------------------------

class AnalysisComplete(Message):
    """Posted when analysis finishes successfully."""

    def __init__(self, population: List[DigitalFish], total_commits: int) -> None:
        super().__init__()
        self.population = population
        self.total_commits = total_commits


class AnalysisFailed(Message):
    """Posted when analysis raises an exception."""

    def __init__(self, error: str) -> None:
        super().__init__()
        self.error = error


# ---------------------------------------------------------------------------
# Setup Screen – interactive configuration form
# ---------------------------------------------------------------------------

_SIMILARITY_OPTIONS = [(m, m) for m in SIMILARITY_METHODS]
_OUTPUT_OPTIONS = [
    ("text", "text"),
    ("json", "json"),
    ("vita", "vita"),
]


class SetupScreen(Screen):
    """Interactive configuration form displayed before analysis begins."""

    BINDINGS = [Binding("q", "quit_app", "Quit")]

    def __init__(
        self,
        *,
        repo: str = "",
        similarity_threshold: float = 0.7,
        similarity_method: str = "levenshtein",
        size_threshold: int = 5,
        branch: Optional[str] = None,
        from_commit: Optional[str] = None,
        to_commit: Optional[str] = None,
        output: str = "text",
        top_n: int = 20,
        out_file: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._defaults = dict(
            repo=repo,
            similarity_threshold=similarity_threshold,
            similarity_method=similarity_method,
            size_threshold=size_threshold,
            branch=branch or "",
            from_commit=from_commit or "",
            to_commit=to_commit or "",
            output=output,
            top_n=top_n,
            out_file=out_file or "",
        )

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll(id="setup-container"):
            yield Label("🐟  Digital Ichthyologist  🐟", id="setup-title")
            yield Label(
                "Track the survival, mutation, and extinction of code organisms.",
                id="setup-subtitle",
            )

            # Repository path
            yield Label("Repository path or URL", classes="form-label")
            yield Input(
                value=self._defaults["repo"],
                placeholder="/path/to/repo or https://…",
                id="repo-input",
            )

            # Branch
            yield Label("Branch (leave empty for default)", classes="form-label")
            yield Input(
                value=self._defaults["branch"],
                placeholder="main",
                id="branch-input",
            )

            # Commit range
            yield Label("From commit SHA (optional)", classes="form-label")
            yield Input(
                value=self._defaults["from_commit"],
                placeholder="e.g. abc1234",
                id="from-commit-input",
            )
            yield Label("To commit SHA (optional)", classes="form-label")
            yield Input(
                value=self._defaults["to_commit"],
                placeholder="e.g. def5678",
                id="to-commit-input",
            )

            # Similarity method
            yield Label("Similarity method", classes="form-label")
            yield Select(
                _SIMILARITY_OPTIONS,
                value=self._defaults["similarity_method"],
                id="similarity-method-select",
            )

            # Similarity threshold
            yield Label("Similarity threshold (0.0–1.0)", classes="form-label")
            yield Input(
                value=str(self._defaults["similarity_threshold"]),
                placeholder="0.7",
                id="similarity-threshold-input",
            )

            # Size threshold
            yield Label("Minimum lines to track (size threshold)", classes="form-label")
            yield Input(
                value=str(self._defaults["size_threshold"]),
                placeholder="5",
                id="size-threshold-input",
            )

            # Output format
            yield Label("Output format", classes="form-label")
            yield Select(
                _OUTPUT_OPTIONS,
                value=self._defaults["output"],
                id="output-select",
            )

            # Top N
            yield Label("Top N entries to display", classes="form-label")
            yield Input(
                value=str(self._defaults["top_n"]),
                placeholder="20",
                id="top-n-input",
            )

            # Output file
            yield Label("Output file (optional)", classes="form-label")
            yield Input(
                value=self._defaults["out_file"],
                placeholder="Leave empty for stdout / default",
                id="out-file-input",
            )

            yield Static("", id="setup-error")
            yield Button("🐟  Analyse", variant="primary", id="analyse-button")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "analyse-button":
            self._start_analysis()

    def _start_analysis(self) -> None:
        """Validate form and transition to the loading screen."""
        error_widget = self.query_one("#setup-error", Static)

        repo = self.query_one("#repo-input", Input).value.strip()
        if not repo:
            error_widget.update("❌  Repository path is required.")
            return

        try:
            sim_thresh = float(
                self.query_one("#similarity-threshold-input", Input).value.strip()
            )
            if not (0.0 <= sim_thresh <= 1.0):
                raise ValueError
        except ValueError:
            error_widget.update("❌  Similarity threshold must be a number between 0 and 1.")
            return

        try:
            size_thresh = int(
                self.query_one("#size-threshold-input", Input).value.strip()
            )
            if size_thresh < 1:
                raise ValueError
        except ValueError:
            error_widget.update("❌  Size threshold must be a positive integer.")
            return

        try:
            top_n = int(self.query_one("#top-n-input", Input).value.strip())
            if top_n < 1:
                raise ValueError
        except ValueError:
            error_widget.update("❌  Top N must be a positive integer.")
            return

        sim_method_select = self.query_one("#similarity-method-select", Select)
        sim_method = (
            sim_method_select.value
            if sim_method_select.value != Select.BLANK
            else "levenshtein"
        )

        output_select = self.query_one("#output-select", Select)
        output = (
            output_select.value
            if output_select.value != Select.BLANK
            else "text"
        )

        branch = self.query_one("#branch-input", Input).value.strip() or None
        from_commit = self.query_one("#from-commit-input", Input).value.strip() or None
        to_commit = self.query_one("#to-commit-input", Input).value.strip() or None
        out_file = self.query_one("#out-file-input", Input).value.strip() or None

        error_widget.update("")

        analyzer_kwargs = dict(
            repo_path=repo,
            similarity_threshold=sim_thresh,
            size_threshold=size_thresh,
            similarity_method=sim_method,
            branch=branch,
            from_commit=from_commit,
            to_commit=to_commit,
        )

        self.app.push_screen(
            LoadingScreen(
                analyzer_kwargs=analyzer_kwargs,
                top_n=top_n,
                out_file=out_file,
                output_format=output,
            )
        )

    def action_quit_app(self) -> None:
        self.app.exit()


# ---------------------------------------------------------------------------
# Loading Screen
# ---------------------------------------------------------------------------

class LoadingScreen(Screen):
    """Displayed while the analysis worker runs in the background."""

    BINDINGS = [Binding("q", "quit_app", "Quit")]

    def __init__(
        self,
        *,
        analyzer_kwargs: dict,
        top_n: int,
        out_file: Optional[str],
        output_format: str = "text",
    ) -> None:
        super().__init__()
        self._analyzer_kwargs = analyzer_kwargs
        self._top_n = top_n
        self._out_file = out_file
        self._output_format = output_format

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="loading-container"):
            yield Label(
                "🐟  Digital Ichthyologist  🐟",
                id="loading-title",
            )
            yield Label(
                f"Analysing: {self._analyzer_kwargs['repo_path']}",
                id="loading-repo",
            )
            yield ProgressBar(id="loading-bar", total=None)
            yield Label("Initialising...", id="loading-status")
            yield Static("", id="loading-log")
        yield Footer()

    def on_mount(self) -> None:
        self._run_analysis()

    @work(thread=True, name="analysis")
    def _run_analysis(self) -> None:
        """Run the Analyzer in a background thread."""
        log_widget = self.query_one("#loading-log", Static)
        status_widget = self.query_one("#loading-status", Label)

        def update_status(msg: str) -> None:
            self.app.call_from_thread(status_widget.update, msg)

        def append_log(msg: str) -> None:
            current = str(log_widget.renderable)
            lines = current.splitlines() if current.strip() else []
            lines.append(f"▸ {msg}")
            # Keep last 6 lines
            lines = lines[-6:]
            self.app.call_from_thread(log_widget.update, "\n".join(lines))

        try:
            update_status("Starting analysis…")
            append_log(f"Repository: {self._analyzer_kwargs['repo_path']}")

            analyzer = Analyzer(**self._analyzer_kwargs)

            update_status("Traversing Git history…")
            append_log("Walking commits and tracking code organisms…")

            population = analyzer.run()

            all_hashes: set = set()
            for fish in population:
                all_hashes.update(fish.commit_hashes)
            total_commits = len(all_hashes)

            append_log(
                f"Done – {len(population)} fish tracked across {total_commits} commits."
            )
            update_status("Analysis complete.")

            self.post_message(AnalysisComplete(population, total_commits))
        except Exception as exc:  # pragma: no cover
            self.post_message(AnalysisFailed(str(exc)))

    def on_analysis_complete(self, message: AnalysisComplete) -> None:
        self.app.push_screen(
            ResultsScreen(
                population=message.population,
                total_commits=message.total_commits,
                top_n=self._top_n,
                out_file=self._out_file,
                output_format=self._output_format,
            )
        )

    def on_analysis_failed(self, message: AnalysisFailed) -> None:
        self.app.push_screen(ErrorScreen(message.error))

    def action_quit_app(self) -> None:
        self.app.exit()


# ---------------------------------------------------------------------------
# Results Screen
# ---------------------------------------------------------------------------

class ResultsScreen(Screen):
    """Interactive results view with tabbed panels."""

    BINDINGS = [
        Binding("q", "quit_app", "Quit"),
        Binding("j", "export_json", "Export JSON"),
        Binding("v", "open_vita", "Vita Dashboard"),
    ]

    def __init__(
        self,
        *,
        population: List[DigitalFish],
        total_commits: int,
        top_n: int,
        out_file: Optional[str],
        output_format: str = "text",
    ) -> None:
        super().__init__()
        self._population = population
        self._total_commits = total_commits
        self._top_n = top_n
        self._out_file = out_file
        self._output_format = output_format
        self._reporter = Reporter(population, top_n=top_n)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("🐟  Heatmap", id="tab-heatmap"):
                yield DataTable(id="heatmap-table", zebra_stripes=True)
            with TabPane("⚰️  Lazarus", id="tab-lazarus"):
                yield DataTable(id="lazarus-table", zebra_stripes=True)
            with TabPane("🌍  Ecosystem", id="tab-ecosystem"):
                with VerticalScroll(id="ecosystem-scroll"):
                    yield Static(id="ecosystem-content")
        yield Footer()

    def on_mount(self) -> None:
        self._populate_heatmap()
        self._populate_lazarus()
        self._populate_ecosystem()
        # Execute the matching export action when a non-text format was chosen
        if self._output_format == "json":
            self.action_export_json()
        elif self._output_format == "vita":
            self.action_open_vita()

    # ------------------------------------------------------------------
    # Table builders
    # ------------------------------------------------------------------

    def _populate_heatmap(self) -> None:
        table: DataTable = self.query_one("#heatmap-table", DataTable)
        table.add_columns(
            "Fish", "Age", "Stability", "Mut. Rate", "Lines", "Status"
        )

        if not self._population:
            return

        max_age = max((f.age for f in self._population), default=1) or 1
        sorted_fish = sorted(self._population, key=lambda f: f.age, reverse=True)

        for fish in sorted_fish[: self._top_n]:
            bar_width = 18
            filled = round((fish.age / max_age) * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            name = (
                fish.display_name[:55] + "…"
                if len(fish.display_name) > 56
                else fish.display_name
            )
            status = "alive" if fish.is_alive else "extinct"
            table.add_row(
                name,
                str(fish.age),
                bar,
                f"{fish.mutation_rate:.3f}",
                str(fish.line_count),
                status,
            )

    def _populate_lazarus(self) -> None:
        table: DataTable = self.query_one("#lazarus-table", DataTable)
        table.add_columns("Fish", "Resurrections", "Age", "Lines", "Status")

        lazarus_fish = sorted(
            [f for f in self._population if f.lazarus_count > 0],
            key=lambda f: f.lazarus_count,
            reverse=True,
        )

        if not lazarus_fish:
            table.add_row("No Lazarus events detected.", "", "", "", "")
            return

        for fish in lazarus_fish[: self._top_n]:
            name = (
                fish.display_name[:55] + "…"
                if len(fish.display_name) > 56
                else fish.display_name
            )
            status = "alive" if fish.is_alive else "extinct"
            table.add_row(
                name,
                str(fish.lazarus_count),
                str(fish.age),
                str(fish.line_count),
                status,
            )

    def _populate_ecosystem(self) -> None:
        content: Static = self.query_one("#ecosystem-content", Static)
        text = self._reporter.ecosystem_health(self._total_commits)
        content.update(text)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_export_json(self) -> None:
        output = self._reporter.to_json()
        out_path = self._out_file or "digital_ichthyologist_results.json"
        Path(out_path).write_text(output, encoding="utf-8")
        self.notify(f"JSON exported → {out_path}", title="Export")

    def action_open_vita(self) -> None:
        vita = Vita(self._population, self._total_commits, top_n=self._top_n)
        out_path = self._out_file or "vita_dashboard.html"
        Path(out_path).write_text(vita.render(), encoding="utf-8")
        self.notify(f"Vita dashboard → {out_path}", title="Export")


# ---------------------------------------------------------------------------
# Error Screen
# ---------------------------------------------------------------------------

class ErrorScreen(Screen):
    """Displayed when analysis raises an exception."""

    BINDINGS = [Binding("q", "quit_app", "Quit")]

    def __init__(self, error: str) -> None:
        super().__init__()
        self._error = error

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="loading-container"):
            yield Label("❌  Analysis Failed", id="loading-title")
            yield Static(self._error, id="loading-log")
        yield Footer()

    def action_quit_app(self) -> None:
        self.app.exit()


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

class DigitalIchthyologistApp(App):
    """Bubbletea-style TUI for the Digital Ichthyologist.

    Follows the Elm Architecture (Model-View-Update) pattern: each screen
    owns its own model (state), renders a view via ``compose``, and handles
    updates through Textual's message system.
    """

    CSS = CSS
    TITLE = "Digital Ichthyologist"
    SUB_TITLE = "Evolutionary Code Analyst"

    def __init__(
        self,
        *,
        analyzer_kwargs: Optional[dict] = None,
        top_n: int = 20,
        out_file: Optional[str] = None,
        output_format: str = "text",
        setup_defaults: Optional[dict] = None,
    ) -> None:
        super().__init__()
        self._analyzer_kwargs = analyzer_kwargs
        self._top_n = top_n
        self._out_file = out_file
        self._output_format = output_format
        self._setup_defaults = setup_defaults or {}

    def on_mount(self) -> None:
        if self._analyzer_kwargs is not None:
            # Skip setup – go directly to loading (backwards-compatible path)
            self.push_screen(
                LoadingScreen(
                    analyzer_kwargs=self._analyzer_kwargs,
                    top_n=self._top_n,
                    out_file=self._out_file,
                    output_format=self._output_format,
                )
            )
        else:
            # Show the interactive setup form (bubbletea-style entry)
            self.push_screen(SetupScreen(**self._setup_defaults))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_tui(
    *,
    analyzer_kwargs: Optional[dict] = None,
    top_n: int = 20,
    out_file: Optional[str] = None,
    output_format: str = "text",
    setup_defaults: Optional[dict] = None,
) -> None:
    """Launch the Textual TUI application.

    When *analyzer_kwargs* is provided the app skips straight to the loading
    screen and runs the analysis.  When omitted the app starts with an
    interactive setup form where the user can configure all parameters –
    following the bubbletea model of a fully-interactive TUI.
    """
    app = DigitalIchthyologistApp(
        analyzer_kwargs=analyzer_kwargs,
        top_n=top_n,
        out_file=out_file,
        output_format=output_format,
        setup_defaults=setup_defaults or {},
    )
    app.run()
