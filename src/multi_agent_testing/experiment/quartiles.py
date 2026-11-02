"""Human difficulty quartiles D1 (easiest) to D4 (hardest).

Pilot-02, phase P2. Standard library only.

Assignment (human puzzles)
--------------------------
Eligible puzzles are sorted by ``(human_mean_score, int(puzzle_id))`` and
split by rank into four contiguous groups whose sizes differ by at most one
(``group k`` holds ranks ``k*n//4 .. (k+1)*n//4 - 1``). Rank splitting keeps
the groups equal even though many puzzles share the same mean: the published
shares are whole percents, so every human mean is a multiple of 0.01. When a
mean value straddles a boundary, the puzzle id breaks the tie; the number of
such puzzles is recorded in ``quartiles.json`` (``boundary_ties``).

Cut-points (mapping system scores)
----------------------------------
A system mean score has no puzzle id, so it is mapped by value with the cut
``c_k = min(human_mean_score in D(k+1))``::

    score <  c_1            -> D1
    c_1 <= score <  c_2     -> D2
    c_2 <= score <  c_3     -> D3
    c_3 <= score            -> D4

With this rule a human puzzle mapped by value lands in its rank quartile
except for the ``boundary_ties`` puzzles, which move up one quartile.

Rank split (mapping system scores by rank)
------------------------------------------
A system that plays on another scale (for example with a 12-guess limit)
is compared by rank instead: ``rank_split`` applies the same contiguous split
to the system means of the puzzles at hand.

Other group counts
------------------
Every function takes an optional ``labels`` tuple; the number of labels sets
the number of groups. The defaults give D1..D4. :mod:`terciles` uses the same
rules with T1..T3.
"""

from collections.abc import Sequence
from dataclasses import dataclass

QUARTILE_LABELS: tuple[str, ...] = ("D1", "D2", "D3", "D4")


@dataclass(frozen=True)
class RankedPuzzle:
    puzzle_id: str
    human_mean_score: float


@dataclass(frozen=True)
class QuartileSpec:
    """Frozen quartile definition for one population of puzzles."""

    population_size: int
    sizes: tuple[int, ...]
    ranges: tuple[tuple[float, float], ...]
    cut_points: tuple[float, ...]
    boundary_ties: tuple[int, ...]
    labels: tuple[str, ...] = QUARTILE_LABELS

    def to_json(self) -> dict[str, object]:
        return {
            "labels": list(self.labels),
            "population_size": self.population_size,
            "sizes": list(self.sizes),
            "ranges": {
                label: {"min": round(lo, 6), "max": round(hi, 6)}
                for label, (lo, hi) in zip(self.labels, self.ranges)
            },
            "cut_points": [round(c, 6) for c in self.cut_points],
            "boundary_ties": list(self.boundary_ties),
            "mapping_rule": mapping_rule(self.labels),
            "assignment_rule": "rank split of (human_mean_score, int(puzzle_id)), sizes differ by <= 1",
        }


def mapping_rule(labels: Sequence[str]) -> str:
    """Readable value rule, e.g. ``D1: s < c1; ...; D4: s >= c3``."""

    k = len(labels)
    parts = [f"{labels[0]}: s < c1"]
    parts += [f"{labels[i]}: c{i} <= s < c{i + 1}" for i in range(1, k - 1)]
    parts.append(f"{labels[-1]}: s >= c{k - 1}")
    return "; ".join(parts)


def _check_labels(labels: Sequence[str]) -> None:
    if len(labels) < 2 or len(set(labels)) != len(labels):
        raise ValueError("Need at least two distinct labels.")


def _sort_key(item: RankedPuzzle) -> tuple[float, int]:
    return (item.human_mean_score, int(item.puzzle_id))


def assign_quartiles(
    puzzles: Sequence[RankedPuzzle],
    labels: Sequence[str] = QUARTILE_LABELS,
) -> tuple[dict[str, str], QuartileSpec]:
    """Rank-split ``puzzles`` into D1..D4 (or one group per label).

    Returns ``({puzzle_id: label}, spec)``. Requires at least one puzzle per
    label.
    """

    _check_labels(labels)
    n = len(puzzles)
    k = len(labels)
    if n < k:
        raise ValueError(f"Need at least {k} puzzles to form {k} groups.")
    if len({p.puzzle_id for p in puzzles}) != n:
        raise ValueError("Puzzle ids must be unique.")

    ordered = sorted(puzzles, key=_sort_key)
    groups = [ordered[i * n // k:(i + 1) * n // k] for i in range(k)]

    label_of = {p.puzzle_id: label for label, group in zip(labels, groups) for p in group}
    ranges = tuple((g[0].human_mean_score, g[-1].human_mean_score) for g in groups)
    cut_points = tuple(groups[i + 1][0].human_mean_score for i in range(k - 1))
    boundary_ties = tuple(
        sum(1 for p in groups[i] if p.human_mean_score >= cut_points[i])
        for i in range(k - 1)
    )

    spec = QuartileSpec(
        population_size=n,
        sizes=tuple(len(g) for g in groups),
        ranges=ranges,
        cut_points=cut_points,
        boundary_ties=boundary_ties,
        labels=tuple(labels),
    )
    return label_of, spec


def rank_split(
    values: Sequence[float],
    tie_keys: Sequence[int],
    labels: Sequence[str] = QUARTILE_LABELS,
) -> list[str]:
    """D1..D4 (or one label per group) for each value by its rank in ``values``.

    The same contiguous split as ``assign_quartiles``, for system means that
    do not share the human scale. Ties on value are broken by ``tie_keys``
    (puzzle ids) and then by position, so a bootstrap sample may repeat a
    puzzle. Requires at least one value per label.
    """

    _check_labels(labels)
    n = len(values)
    k = len(labels)
    if n < k:
        raise ValueError(f"Need at least {k} values to form {k} groups.")
    if len(tie_keys) != n:
        raise ValueError("Need one tie key per value.")

    order = sorted(range(n), key=lambda i: (values[i], tie_keys[i], i))
    out = [""] * n
    for group, label in enumerate(labels):
        for position in order[group * n // k:(group + 1) * n // k]:
            out[position] = label
    return out


def map_score(
    score: float,
    cut_points: Sequence[float],
    labels: Sequence[str] = QUARTILE_LABELS,
) -> str:
    """Map a mean guess score to D1..D4 (or ``labels``) with the value rule above."""

    _check_labels(labels)
    if len(cut_points) != len(labels) - 1:
        raise ValueError(f"Expected {len(labels) - 1} cut-points.")
    if list(cut_points) != sorted(cut_points):
        raise ValueError("Cut-points must be non-decreasing.")

    for label, cut in zip(labels, cut_points):
        if score < cut:
            return label
    return labels[-1]
