"""Bubbletea-style TUI for Digital Ichthyologist, powered by Textual."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    ProgressBar,
    Static,
    TabbedContent,
    TabPane,
)

from .analyzer import Analyzer
from .fish import DigitalFish
from .reporter import Reporter
from .vita import Vita


# ---------------------------------------------------------------------------
# CSS stylesheet
# ---------------------------------------------------------------------------

CSS = """
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
    ) -> None:
        super().__init__()
        self._analyzer_kwargs = analyzer_kwargs
        self._top_n = top_n
        self._out_file = out_file

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
    ) -> None:
        super().__init__()
        self._population = population
        self._total_commits = total_commits
        self._top_n = top_n
        self._out_file = out_file
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
    """Bubbletea-style TUI for the Digital Ichthyologist."""

    CSS = CSS
    TITLE = "Digital Ichthyologist"
    SUB_TITLE = "Evolutionary Code Analyst"

    def __init__(self, *, analyzer_kwargs: dict, top_n: int, out_file: Optional[str]) -> None:
        super().__init__()
        self._analyzer_kwargs = analyzer_kwargs
        self._top_n = top_n
        self._out_file = out_file

    def on_mount(self) -> None:
        self.push_screen(
            LoadingScreen(
                analyzer_kwargs=self._analyzer_kwargs,
                top_n=self._top_n,
                out_file=self._out_file,
            )
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_tui(
    *,
    analyzer_kwargs: dict,
    top_n: int,
    out_file: Optional[str],
) -> None:
    """Launch the Textual TUI application."""
    app = DigitalIchthyologistApp(
        analyzer_kwargs=analyzer_kwargs,
        top_n=top_n,
        out_file=out_file,
    )
    app.run()
