"""Survival Analyzer – core logic that walks Git commits and tracks fish."""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Dict, Iterable, List, Optional, Tuple

from rapidfuzz import fuzz
from tqdm import tqdm

from .extractor import BlockInfo, get_functions_and_classes
from .fish import DigitalFish

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
BlockMap = Dict[str, BlockInfo]  # qualified_name -> BlockInfo(source, start_line, end_line)


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
) -> Optional[Tuple[str, BlockInfo, float]]:
    """Find the best-matching block for *fish* in *current_blocks*.

    Returns:
        ``(name, block_info, similarity)`` for the best match, or ``None`` if
        no block exceeds the thresholds.
    """
    best_name: Optional[str] = None
    best_info: Optional[BlockInfo] = None
    best_sim: float = 0.0

    for name, info in current_blocks.items():
        if _meaningful_lines(info.source) < size_threshold:
            continue
        sim = _similarity(fish.content, info.source)
        if sim >= similarity_threshold and sim > best_sim:
            best_name = name
            best_info = info
            best_sim = sim

    if best_name is not None:
        return best_name, best_info, best_sim  # type: ignore[return-value]
    return None


# ---------------------------------------------------------------------------
# Helper: estimate total commit count for progress bars
# ---------------------------------------------------------------------------

def _estimate_commit_count(
    repo_path: str,
    branch: Optional[str] = None,
    from_commit: Optional[str] = None,
    to_commit: Optional[str] = None,
) -> Optional[int]:
    """Use ``git rev-list --count`` to quickly estimate the number of commits.

    Returns ``None`` when the count cannot be determined (e.g. remote URL or
    missing git binary), in which case *tqdm* falls back to an indeterminate
    progress bar.
    """
    ref = to_commit or branch or "HEAD"
    cmd = ["git", "-C", str(repo_path), "rev-list", "--count"]
    if from_commit:
        cmd.append(f"{from_commit}^..{ref}")
    else:
        cmd.append(ref)
    try:
        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, check=True,
        )
        return int(result.stdout.strip())
    except Exception:
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
        progress: If ``True``, display progress bars on *stderr*.
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
        progress: bool = False,
    ) -> None:
        self.repo_path = repo_path
        self.similarity_threshold = similarity_threshold
        self.size_threshold = size_threshold
        self.file_extensions: List[str] = list(file_extensions or [".py"])
        self.branch = branch
        self.from_commit = from_commit
        self.to_commit = to_commit
        self._progress = progress

        # All fish ever seen (alive + extinct)
        self.population: List[DigitalFish] = []
        # Currently alive fish (mutates per commit)
        self._active: List[DigitalFish] = []
        # Running snapshot of code blocks per file (filename → BlockMap)
        self._file_blocks: Dict[str, BlockMap] = {}
        # Map from qualified name to the filename it belongs to
        self._block_files: Dict[str, str] = {}

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

        total = (
            _estimate_commit_count(
                self.repo_path, self.branch, self.from_commit, self.to_commit
            )
            if self._progress
            else None
        )

        commits_iter = Repository(self.repo_path, **kwargs).traverse_commits()
        commit_bar: Optional[tqdm] = None

        if self._progress:
            commit_bar = tqdm(
                commits_iter,
                total=total,
                desc="Analysing commits",
                unit="commit",
                file=sys.stderr,
            )
            commits_iter = commit_bar

        for commit in commits_iter:
            commit_count += 1
            logger.debug("Processing commit %s (%s)", commit.hash[:8], commit.msg[:60])

            n_files = len(commit.modified_files)
            if commit_bar is not None:
                commit_bar.set_postfix(files=n_files, refresh=False)

            current_blocks = self._extract_blocks(commit, commit_bar)
            self._process_commit(current_blocks, commit.hash)

        if commit_bar is not None:
            commit_bar.close()

        logger.info(
            "Analysis complete: %d commits, %d fish tracked.",
            commit_count,
            len(self.population),
        )
        return self.population

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_blocks(
        self, commit: object, commit_bar: Optional[tqdm] = None,
    ) -> BlockMap:
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
        modified = commit.modified_files  # type: ignore[attr-defined]
        file_iter = modified

        if self._progress and len(modified) > 1:
            file_iter = tqdm(
                modified,
                desc="  Scanning files",
                unit="file",
                leave=False,
                file=sys.stderr,
            )

        for modified_file in file_iter:
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

        if self._progress and len(modified) > 1 and isinstance(file_iter, tqdm):
            file_iter.close()

        # Build the complete block map from all tracked files.
        blocks: BlockMap = {}
        self._block_files = {}
        for filename, file_blocks in self._file_blocks.items():
            for qname, info in file_blocks.items():
                blocks[qname] = info
                self._block_files[qname] = filename
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
                matched_name, matched_info, sim = match
                fish.survive(matched_info.source, commit_hash, sim)
                fish.file_path = self._block_files.get(matched_name, fish.file_path)
                fish.start_line = matched_info.start_line
                fish.end_line = matched_info.end_line
                still_alive.append(fish)
                del unclaimed[matched_name]
            else:
                fish.go_extinct(commit_hash)

        # --- birth / resurrection pass ---
        for name, info in unclaimed.items():
            if _meaningful_lines(info.source) < self.size_threshold:
                continue  # plankton – too small to track

            file_path = self._block_files.get(name, "")

            # Check whether an extinct fish with the same name can be revived
            revived = self._try_resurrect(name, info.source, commit_hash)
            if revived is not None:
                revived.file_path = file_path
                revived.start_line = info.start_line
                revived.end_line = info.end_line
                still_alive.append(revived)
            else:
                new_fish = DigitalFish(
                    name, info.source, commit_hash,
                    file_path=file_path,
                    start_line=info.start_line,
                    end_line=info.end_line,
                )
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
