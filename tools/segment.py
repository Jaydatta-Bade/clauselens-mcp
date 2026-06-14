# tools/segment.py
from __future__ import annotations

import re

from schemas import Clause

_MIN_CLAUSE_CHARS = 30

# Patterns indicating a new section/clause begins at this position.
# Each pattern matches at the start of a line.
_STARTERS = re.compile(
    r"""
    (?:^|\n)                   # start of string or preceded by newline
    (?:
      \d+[.)]\s+               # "1. " or "1) "
    | [A-Z][.)]\s+             # "A. " or "A) "
    | [a-z][.)]\s+             # "a. " or "a) "
    | \([a-z0-9]+\)\s+         # "(a) " or "(1) "
    | (?:Section|Article|Clause|SECTION|ARTICLE|CLAUSE)\s+\w+  # "Section 1"
    )
    """,
    re.VERBOSE | re.MULTILINE,
)


def segment_clauses(text: str) -> list[Clause]:
    """Split *text* into candidate clauses with exact char offsets.

    Returns a list of Clause objects where text[c.char_start:c.char_end] == c.text
    for every clause c.
    """
    if not text or not text.strip():
        return []

    split_points: set[int] = {0, len(text)}

    # Section header starters
    for match in _STARTERS.finditer(text):
        pos = match.start()
        # Skip the leading newline; the split starts at the header character
        if pos < len(text) and text[pos] == "\n":
            pos += 1
        split_points.add(pos)

    # Paragraph breaks
    for match in re.finditer(r"\n\n+", text):
        split_points.add(match.end())

    sorted_points = sorted(split_points)

    clauses: list[Clause] = []
    clause_num = 0

    for i in range(len(sorted_points) - 1):
        raw_start = sorted_points[i]
        raw_end = sorted_points[i + 1]

        chunk = text[raw_start:raw_end]
        stripped = chunk.strip()

        if len(stripped) < _MIN_CLAUSE_CHARS:
            continue

        # Compute exact offsets into the original text (after stripping whitespace)
        leading = len(chunk) - len(chunk.lstrip())
        trailing = len(chunk) - len(chunk.rstrip())

        actual_start = raw_start + leading
        actual_end = raw_end - trailing if trailing > 0 else raw_end

        clause_num += 1
        clauses.append(
            Clause(
                id=f"cl_{clause_num:03d}",
                text=stripped,
                char_start=actual_start,
                char_end=actual_end,
            )
        )

    return clauses
