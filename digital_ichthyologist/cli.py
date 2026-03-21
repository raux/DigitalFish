"""Command-line interface for the Digital Ichthyologist."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .analyzer import Analyzer
from .reporter import Reporter
from .vita import Vita


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="digital-ichthyologist",
        description=(
            "Digital Ichthyologist – track the survival, mutation, and "
            "extinction of code organisms (functions/classes) through Git history."
        ),
    )
    parser.add_argument(
        "repo",
        help="Local path or remote URL of the Git repository to analyse.",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.7,
        metavar="λ",
        help="Minimum similarity ratio (0–1) for a fish to survive (default: 0.7).",
    )
    parser.add_argument(
        "--size-threshold",
        type=int,
        default=5,
        metavar="σ",
        help="Minimum meaningful lines for a block to be tracked (default: 5).",
    )
    parser.add_argument(
        "--branch",
        default=None,
        help="Branch to traverse (default: repository default).",
    )
    parser.add_argument(
        "--from-commit",
        default=None,
        help="Start analysis from this commit SHA (inclusive).",
    )
    parser.add_argument(
        "--to-commit",
        default=None,
        help="Stop analysis at this commit SHA (inclusive).",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json", "vita"],
        default="text",
        help="Output format (default: text). 'vita' generates an interactive HTML dashboard.",
    )
    parser.add_argument(
        "--out-file",
        default=None,
        metavar="PATH",
        help="Write output to this file instead of stdout.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        metavar="N",
        help="Number of entries to show in ranked lists (default: 20).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    analyzer = Analyzer(
        repo_path=args.repo,
        similarity_threshold=args.similarity_threshold,
        size_threshold=args.size_threshold,
        branch=args.branch,
        from_commit=args.from_commit,
        to_commit=args.to_commit,
    )

    population = analyzer.run()
    total_commits = sum(1 for _ in _count_commits(analyzer))

    reporter = Reporter(population, top_n=args.top_n)

    if args.output == "json":
        output = reporter.to_json()
    elif args.output == "vita":
        vita = Vita(population, total_commits, top_n=args.top_n)
        output = vita.render()
        if not args.out_file:
            args.out_file = "vita_dashboard.html"
    else:
        output = "\n".join(
            [
                reporter.survival_heatmap(),
                reporter.lazarus_report(),
                reporter.ecosystem_health(total_commits),
            ]
        )

    if args.out_file:
        Path(args.out_file).write_text(output, encoding="utf-8")
        print(f"Report written to {args.out_file}", file=sys.stderr)
    else:
        print(output)

    return 0


def _count_commits(analyzer: Analyzer) -> range:
    """Return a proxy iterable whose length is the number of commits seen.

    We derive the count from the fish population commit hashes rather than
    re-traversing the repository, which avoids a second clone/fetch.
    """
    all_hashes: set = set()
    for fish in analyzer.population:
        all_hashes.update(fish.commit_hashes)
    return range(len(all_hashes))


if __name__ == "__main__":
    raise SystemExit(main())
