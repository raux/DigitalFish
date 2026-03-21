"""DigitalFish model – one tracked code organism (function or class)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class DigitalFish:
    """Represents a single tracked code organism.

    Attributes:
        name: Qualified name of the function or class.
        content: Source text of the code block.
        birth_commit: SHA of the commit where this fish was first seen.
        fish_id: Stable integer identity derived from name + birth_commit.
        age: Number of commits in which this fish has survived.
        mutation_rate: Cumulative similarity distance (1 - ratio) accumulated
            over all commits where the fish was matched but changed.
        is_alive: Whether the fish is still present in the latest analysed
            commit.
        commit_hashes: Ordered list of every commit SHA where the fish was
            seen alive (including birth).
        extinction_commit: SHA of the commit after which the fish disappeared,
            or ``None`` if still alive.
        lazarus_count: Number of times this fish reappeared after extinction.
    """

    name: str
    content: str
    birth_commit: str
    fish_id: int = field(init=False)
    age: int = field(default=0, init=False)
    mutation_rate: float = field(default=0.0, init=False)
    is_alive: bool = field(default=True, init=False)
    commit_hashes: List[str] = field(default_factory=list, init=False)
    extinction_commit: str | None = field(default=None, init=False)
    lazarus_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.fish_id = hash(self.name + self.birth_commit)
        self.commit_hashes.append(self.birth_commit)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def survive(self, new_content: str, commit_hash: str, similarity: float) -> None:
        """Update the fish after it survives into the next commit.

        Args:
            new_content: The updated source text in this commit.
            commit_hash: SHA of the current commit.
            similarity: Similarity ratio (0–1) between old and new content.
        """
        if new_content != self.content:
            self.mutation_rate += 1.0 - similarity
        self.content = new_content
        self.age += 1
        self.commit_hashes.append(commit_hash)
        self.is_alive = True

    def go_extinct(self, commit_hash: str) -> None:
        """Mark the fish as extinct.

        Args:
            commit_hash: SHA of the commit in which it was no longer found.
        """
        self.is_alive = False
        self.extinction_commit = commit_hash

    def resurrect(self, new_content: str, commit_hash: str) -> None:
        """Bring a previously extinct fish back to life (Lazarus event).

        Args:
            new_content: The source text in the commit where it reappeared.
            commit_hash: SHA of that commit.
        """
        self.content = new_content
        self.is_alive = True
        self.extinction_commit = None
        self.lazarus_count += 1
        self.age += 1
        self.commit_hashes.append(commit_hash)

    # ------------------------------------------------------------------
    # Representation helpers
    # ------------------------------------------------------------------

    @property
    def line_count(self) -> int:
        """Number of non-empty, non-comment lines in the current content."""
        return sum(
            1
            for line in self.content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    def __repr__(self) -> str:
        status = "alive" if self.is_alive else "extinct"
        return (
            f"DigitalFish(name={self.name!r}, age={self.age}, "
            f"mutation_rate={self.mutation_rate:.3f}, status={status})"
        )
