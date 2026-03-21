"""Survival Analyzer – core logic that walks Git commits and tracks fish."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional, Tuple

from rapidfuzz import fuzz

from .extractor import get_functions_and_classes
from .fish import DigitalFish

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
BlockMap = Dict[str, str]  # qualified_name -> source_text


# ---------------------------------------------------------------------------
# Helper: fuzzy similarity between two source strings
# ---------------------------------------------------------------------------

def _similarity(a: str, b: str) -> float:
    """Return a similarity ratio in [0, 1] between two source strings."""
    return fuzz.ratio(a, b) / 100.0


# ---------------------------------------------------------------------------
# Helper: count meaningful lines
# ---------------------------------------------------------------------------

def _meaningful_lines(content: str) -> int:
    """Count non-empty, non-comment lines."""
    return sum(
        1
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


# ---------------------------------------------------------------------------
# Match a single fish against the current commit's blocks
# ---------------------------------------------------------------------------

def _find_best_match(
    fish: DigitalFish,
    current_blocks: BlockMap,
    similarity_threshold: float,
    size_threshold: int,
) -> Optional[Tuple[str, str, float]]:
    """Find the best-matching block for *fish* in *current_blocks*.

    Returns:
        ``(name, content, similarity)`` for the best match, or ``None`` if no
        block exceeds the thresholds.
    """
    best_name: Optional[str] = None
    best_content: Optional[str] = None
    best_sim: float = 0.0

    for name, content in current_blocks.items():
        if _meaningful_lines(content) < size_threshold:
            continue
        sim = _similarity(fish.content, content)
        if sim >= similarity_threshold and sim > best_sim:
            best_name = name
            best_content = content
            best_sim = sim

    if best_name is not None:
        return best_name, best_content, best_sim  # type: ignore[return-value]
    return None


# ---------------------------------------------------------------------------
# Main Analyzer class
# ---------------------------------------------------------------------------

class Analyzer:
    """Traverses commits of a repository and maintains the fish population.

    Args:
        repo_path: Local path or remote URL of the Git repository.
        similarity_threshold: Minimum fuzzy-match ratio for a fish to survive
            (λ – default 0.7).
        size_threshold: Minimum meaningful line count for a block to be
            considered a fish (σ – default 5).
        file_extensions: Iterable of file suffixes to analyse.  Defaults to
            ``[".py"]``.
        branch: Branch to traverse.  ``None`` uses PyDriller's default.
        from_commit: Start traversal from this commit SHA (inclusive).
        to_commit: Stop traversal at this commit SHA (inclusive).
    """

    def __init__(
        self,
        repo_path: str,
        *,
        similarity_threshold: float = 0.7,
        size_threshold: int = 5,
        file_extensions: Optional[Iterable[str]] = None,
        branch: Optional[str] = None,
        from_commit: Optional[str] = None,
        to_commit: Optional[str] = None,
    ) -> None:
        self.repo_path = repo_path
        self.similarity_threshold = similarity_threshold
        self.size_threshold = size_threshold
        self.file_extensions: List[str] = list(file_extensions or [".py"])
        self.branch = branch
        self.from_commit = from_commit
        self.to_commit = to_commit

        # All fish ever seen (alive + extinct)
        self.population: List[DigitalFish] = []
        # Currently alive fish (mutates per commit)
        self._active: List[DigitalFish] = []
        # Running snapshot of code blocks per file (filename → BlockMap)
        self._file_blocks: Dict[str, BlockMap] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> List[DigitalFish]:
        """Traverse the repository and return the full fish population.

        Returns:
            All ``DigitalFish`` objects ever created (alive and extinct).
        """
        from pydriller import Repository  # local import to keep module testable

        kwargs: Dict[str, object] = {}
        if self.branch:
            kwargs["only_in_branch"] = self.branch
        if self.from_commit:
            kwargs["from_commit"] = self.from_commit
        if self.to_commit:
            kwargs["to_commit"] = self.to_commit

        logger.info("Starting analysis of %s", self.repo_path)
        commit_count = 0

        for commit in Repository(self.repo_path, **kwargs).traverse_commits():
            commit_count += 1
            logger.debug("Processing commit %s (%s)", commit.hash[:8], commit.msg[:60])

            current_blocks = self._extract_blocks(commit)
            self._process_commit(current_blocks, commit.hash)

        logger.info(
            "Analysis complete: %d commits, %d fish tracked.",
            commit_count,
            len(self.population),
        )
        return self.population

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_blocks(self, commit: object) -> BlockMap:
        """Return all code blocks visible in *commit*.

        Maintains a running snapshot (``_file_blocks``) of code blocks per
        file.  Only files that appear in *commit.modified_files* are updated;
        blocks from untouched files are carried forward so that their fish are
        not incorrectly marked as extinct.  When a file is deleted or emptied
        its blocks are removed from the snapshot.

        Returns:
            A :data:`BlockMap` (qualified-name → source-text) representing
            every tracked code block across all files.
        """
        for modified_file in commit.modified_files:  # type: ignore[attr-defined]
            if not any(
                modified_file.filename.endswith(ext) for ext in self.file_extensions
            ):
                continue
            source = modified_file.source_code
            if not source:
                # File was deleted or emptied – remove its tracked blocks.
                self._file_blocks.pop(modified_file.filename, None)
                continue
            try:
                self._file_blocks[modified_file.filename] = (
                    get_functions_and_classes(source)
                )
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "Could not parse %s at %s: %s",
                    modified_file.filename,
                    commit.hash[:8],  # type: ignore[attr-defined]
                    exc,
                )

        # Build the complete block map from all tracked files.
        blocks: BlockMap = {}
        for file_blocks in self._file_blocks.values():
            blocks.update(file_blocks)
        return blocks

    def _process_commit(self, current_blocks: BlockMap, commit_hash: str) -> None:
        """Update the fish population for a single commit.

        1. Try to match each active fish to a block in *current_blocks*.
        2. Matched fish survive (possibly mutating).
        3. Unmatched fish go extinct.
        4. Unclaimed blocks become new fish or resurrect extinct ones.
        """
        unclaimed = dict(current_blocks)
        still_alive: List[DigitalFish] = []

        # --- survival pass ---
        for fish in self._active:
            match = _find_best_match(
                fish, unclaimed, self.similarity_threshold, self.size_threshold
            )
            if match is not None:
                matched_name, matched_content, sim = match
                fish.survive(matched_content, commit_hash, sim)
                still_alive.append(fish)
                del unclaimed[matched_name]
            else:
                fish.go_extinct(commit_hash)

        # --- birth / resurrection pass ---
        for name, content in unclaimed.items():
            if _meaningful_lines(content) < self.size_threshold:
                continue  # plankton – too small to track

            # Check whether an extinct fish with the same name can be revived
            revived = self._try_resurrect(name, content, commit_hash)
            if revived is not None:
                still_alive.append(revived)
            else:
                new_fish = DigitalFish(name, content, commit_hash)
                self.population.append(new_fish)
                still_alive.append(new_fish)

        self._active = still_alive

    def _try_resurrect(
        self, name: str, content: str, commit_hash: str
    ) -> Optional[DigitalFish]:
        """Return an extinct fish that matches *name* and *content*, if any."""
        for fish in self.population:
            if fish.is_alive:
                continue
            sim = _similarity(fish.content, content)
            if fish.name == name and sim >= self.similarity_threshold:
                fish.resurrect(content, commit_hash)
                return fish
        return None
