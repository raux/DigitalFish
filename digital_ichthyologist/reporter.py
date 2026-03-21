"""Reporter – generates outputs from a completed fish population analysis."""

from __future__ import annotations

import io
import json
from typing import Dict, List, Optional, Tuple

from .fish import DigitalFish


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _alive(population: List[DigitalFish]) -> List[DigitalFish]:
    return [f for f in population if f.is_alive]


def _extinct(population: List[DigitalFish]) -> List[DigitalFish]:
    return [f for f in population if not f.is_alive]


def _bar(value: float, width: int = 20) -> str:
    """Return a simple ASCII progress bar."""
    filled = round(value * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

class Reporter:
    """Generates textual and structured reports from the fish population.

    Args:
        population: The full list of :class:`~digital_ichthyologist.DigitalFish`
            objects returned by :meth:`~digital_ichthyologist.Analyzer.run`.
        top_n: How many entries to show in ranked lists (default 20).
    """

    def __init__(
        self,
        population: List[DigitalFish],
        *,
        top_n: int = 20,
    ) -> None:
        self.population = population
        self.top_n = top_n

    # ------------------------------------------------------------------
    # 1. Survival Heatmap
    # ------------------------------------------------------------------

    def survival_heatmap(self) -> str:
        """Return an ASCII survival heatmap.

        Each row represents one fish, ordered from most stable (highest age)
        to most volatile (lowest age).  The bar length represents relative
        age and the mutation rate is shown alongside.

        Returns:
            A multi-line string suitable for printing to a terminal.
        """
        if not self.population:
            return "No fish found in population.\n"

        max_age = max((f.age for f in self.population), default=1) or 1
        sorted_fish = sorted(self.population, key=lambda f: f.age, reverse=True)
        top = sorted_fish[: self.top_n]

        buf = io.StringIO()
        buf.write("=== Survival Heatmap ===\n")
        buf.write(
            f"{'Fish Name':<60} {'Age':>5}  {'Stability':<22} {'Mut.Rate':>8}  {'Lines':>5}  Status\n"
        )
        buf.write("-" * 117 + "\n")
        for fish in top:
            bar = _bar(fish.age / max_age)
            status = "alive" if fish.is_alive else "extinct"
            name = fish.display_name[:58] + ".." if len(fish.display_name) > 60 else fish.display_name
            buf.write(
                f"{name:<60} {fish.age:>5}  {bar:<22} {fish.mutation_rate:>8.3f}  {fish.line_count:>5}  {status}\n"
            )
        if len(sorted_fish) > self.top_n:
            buf.write(
                f"... and {len(sorted_fish) - self.top_n} more fish not shown.\n"
            )
        return buf.getvalue()

    # ------------------------------------------------------------------
    # 2. Lazarus Report
    # ------------------------------------------------------------------

    def lazarus_report(self) -> str:
        """Return the Lazarus Report – code that was deleted and later reintroduced.

        Returns:
            A multi-line string listing all Lazarus fish and their resurrection
            counts, sorted from most resurrected to least.
        """
        lazarus_fish = [f for f in self.population if f.lazarus_count > 0]
        if not lazarus_fish:
            return "No Lazarus events detected.\n"

        lazarus_fish.sort(key=lambda f: f.lazarus_count, reverse=True)

        buf = io.StringIO()
        buf.write("=== The Lazarus Report ===\n")
        buf.write("Code that was deleted and later reintroduced:\n\n")
        buf.write(f"{'Fish Name':<60} {'Resurrections':>14}  {'Age':>5}  {'Lines':>5}  Status\n")
        buf.write("-" * 99 + "\n")
        for fish in lazarus_fish[: self.top_n]:
            name = fish.display_name[:58] + ".." if len(fish.display_name) > 60 else fish.display_name
            status = "alive" if fish.is_alive else "extinct"
            buf.write(
                f"{name:<60} {fish.lazarus_count:>14}  {fish.age:>5}  {fish.line_count:>5}  {status}\n"
            )
        return buf.getvalue()

    # ------------------------------------------------------------------
    # 3. Ecosystem Health
    # ------------------------------------------------------------------

    def ecosystem_health(self, total_commits: int) -> str:
        """Return an ecosystem health summary.

        Calculates births-per-100-commits, extinctions-per-100-commits, and a
        stability score.

        Args:
            total_commits: The total number of commits analysed.

        Returns:
            A multi-line string with key ecosystem health metrics.
        """
        if total_commits == 0:
            return "No commits analysed.\n"

        total_fish = len(self.population)
        alive_count = len(_alive(self.population))
        extinct_count = len(_extinct(self.population))
        lazarus_count = sum(f.lazarus_count for f in self.population)

        births_per_100 = (total_fish / total_commits) * 100
        extinctions_per_100 = (extinct_count / total_commits) * 100
        survival_ratio = alive_count / total_fish if total_fish else 0.0

        avg_age = (
            sum(f.age for f in self.population) / total_fish if total_fish else 0.0
        )
        avg_mutation = (
            sum(f.mutation_rate for f in self.population) / total_fish
            if total_fish
            else 0.0
        )

        buf = io.StringIO()
        buf.write("=== Ecosystem Health Report ===\n\n")
        buf.write(f"  Commits analysed        : {total_commits}\n")
        buf.write(f"  Total fish (ever)        : {total_fish}\n")
        buf.write(f"  Currently alive          : {alive_count}\n")
        buf.write(f"  Extinct                  : {extinct_count}\n")
        buf.write(f"  Lazarus events           : {lazarus_count}\n")
        buf.write(f"\n")
        buf.write(f"  Births per 100 commits   : {births_per_100:.1f}\n")
        buf.write(f"  Extinctions per 100      : {extinctions_per_100:.1f}\n")
        buf.write(f"  Survival ratio           : {survival_ratio:.1%}\n")
        buf.write(f"\n")
        buf.write(f"  Avg age (commits)        : {avg_age:.1f}\n")
        buf.write(f"  Avg mutation rate        : {avg_mutation:.3f}\n")
        return buf.getvalue()

    # ------------------------------------------------------------------
    # 4. JSON export
    # ------------------------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        """Serialise the full population to JSON.

        Returns:
            A JSON string representation of every fish.
        """
        data = [
            {
                "fish_id": fish.fish_id,
                "name": fish.name,
                "display_name": fish.display_name,
                "file_path": fish.file_path,
                "start_line": fish.start_line,
                "end_line": fish.end_line,
                "birth_commit": fish.birth_commit,
                "age": fish.age,
                "mutation_rate": fish.mutation_rate,
                "is_alive": fish.is_alive,
                "extinction_commit": fish.extinction_commit,
                "lazarus_count": fish.lazarus_count,
                "commit_hashes": fish.commit_hashes,
                "line_count": fish.line_count,
            }
            for fish in self.population
        ]
        return json.dumps(data, indent=indent)
