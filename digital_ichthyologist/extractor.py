"""Source-code extractor – pulls functions and classes from Python source."""

from __future__ import annotations

import ast
import textwrap
import warnings
from typing import Dict, NamedTuple, Optional


class BlockInfo(NamedTuple):
    """Metadata for a single extracted code block."""

    source: str
    start_line: int
    end_line: int


def _get_source_segment(source: str, node: ast.AST) -> Optional[str]:
    """Return the source text for *node* from *source*.

    Falls back to a line-range slice when ``ast.get_source_segment`` is
    unavailable (Python < 3.8) or returns ``None``.
    """
    try:
        segment = ast.get_source_segment(source, node)
        if segment is not None:
            return segment
    except Exception:
        pass

    # Fallback: reconstruct from line numbers
    lines = source.splitlines(keepends=True)
    start = node.lineno - 1  # type: ignore[attr-defined]
    end = node.end_lineno  # type: ignore[attr-defined]
    return "".join(lines[start:end])


def _qualified_name(node: ast.AST, parent_name: Optional[str] = None) -> str:
    """Build a qualified name like ``ClassName.method_name``."""
    name: str = getattr(node, "name", "<anonymous>")
    return f"{parent_name}.{name}" if parent_name else name


def get_functions_and_classes(
    source_code: str,
    *,
    include_classes: bool = True,
    include_methods: bool = True,
) -> Dict[str, BlockInfo]:
    """Extract top-level functions, classes, and (optionally) methods.

    Args:
        source_code: Raw Python source text.
        include_classes: Whether to include class bodies as individual fish.
        include_methods: Whether to also extract methods inside classes.

    Returns:
        A mapping of *qualified_name* → :class:`BlockInfo` for every
        discovered code block.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source_code)
    except SyntaxError:
        return {}

    blocks: Dict[str, BlockInfo] = {}
    lines = source_code.splitlines(keepends=True)

    def _extract_node(node: ast.AST, parent_name: Optional[str] = None) -> None:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return

        qname = _qualified_name(node, parent_name)
        segment = _get_source_segment(source_code, node)
        if segment is None:
            return

        # Dedent so that methods are not indented relative to their class
        segment = textwrap.dedent(segment)

        start_line: int = getattr(node, "lineno", 0)
        end_line: int = getattr(node, "end_lineno", start_line)

        if isinstance(node, ast.ClassDef):
            if include_classes:
                blocks[qname] = BlockInfo(segment, start_line, end_line)
            if include_methods:
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        _extract_node(child, parent_name=qname)
        else:
            blocks[qname] = BlockInfo(segment, start_line, end_line)

    for top_node in ast.iter_child_nodes(tree):
        _extract_node(top_node)

    return blocks
