"""Levels of detail: which step summarises which.

Every step has a `level` (1 = key steps, 2 = the default, 3 = line by line, ...). The
hierarchy is derived from the recorded sequence:

* a deeper step belongs to the first shallower step that follows it: a key step
  summarises everything that happened since the previous key step, so it sits at a
  stage's return (or in the caller right after the call) and the details come before it;
* if no shallower step follows, the deeper step is attached to the last shallower step
  before it (trailing details);
* `parent="id"` on a step overrides the rule.

The viewer walks the sequence at the current step's level (Next/Prev skip deeper
steps), goes Down into the first detail of the current step, and Up to its summary.
"""

from __future__ import annotations

from typing import Optional, Sequence


def assign_parents(levels: Sequence[int], explicit: Optional[Sequence[Optional[int]]] = None) -> list[Optional[int]]:
    """Index of each step's parent (None for roots), given the levels in recorded order.

    `explicit[i]`, when not None, is the parent index chosen by the author for step i.
    """
    n = len(levels)
    parents: list[Optional[int]] = [None] * n
    for i in range(n):
        if explicit is not None and explicit[i] is not None and explicit[i] != i:
            parents[i] = explicit[i]
            continue
        level = levels[i]
        after = next((j for j in range(i + 1, n) if levels[j] < level), None)
        if after is not None:
            parents[i] = after
            continue
        before = next((j for j in range(i - 1, -1, -1) if levels[j] < level), None)
        parents[i] = before
    return parents


def children_of(parents: Sequence[Optional[int]]) -> list[list[int]]:
    """For each step, the indices of its children in recorded order."""
    out: list[list[int]] = [[] for _ in parents]
    for i, p in enumerate(parents):
        if p is not None:
            out[p].append(i)
    return out


def resolve_explicit(spec_parents: Sequence[Optional[str]], spec_ids: Sequence[str]) -> list[Optional[int]]:
    """Turn `parent="spec-id"` declarations into indices in the recorded sequence.

    When the parent step was recorded several times (hit="all"), the first instance after
    the step wins, else the last one before it.
    """
    out: list[Optional[int]] = [None] * len(spec_parents)
    for i, wanted in enumerate(spec_parents):
        if wanted is None:
            continue
        after = next((j for j in range(i + 1, len(spec_ids)) if spec_ids[j] == wanted), None)
        if after is not None:
            out[i] = after
            continue
        out[i] = next((j for j in range(i - 1, -1, -1) if spec_ids[j] == wanted), None)
    return out


def trailing_details(levels: Sequence[int], explicit: Optional[Sequence[Optional[int]]] = None) -> list[int]:
    """Steps deeper than the minimum level with no shallower step after them (and no explicit parent)."""
    out: list[int] = []
    n = len(levels)
    for i, level in enumerate(levels):
        if explicit is not None and explicit[i] is not None:
            continue
        if any(levels[j] < level for j in range(i + 1, n)):
            continue
        if any(levels[j] < level for j in range(i)):
            out.append(i)
    return out
