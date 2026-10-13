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

    def to_json(self) -> dict[str, object]:
        return {
            "labels": list(QUARTILE_LABELS),
            "population_size": self.population_size,
            "sizes": list(self.sizes),
            "ranges": {
                label: {"min": round(lo, 6), "max": round(hi, 6)}
                for label, (lo, hi) in zip(QUARTILE_LABELS, self.ranges)
            },
            "cut_points": [round(c, 6) for c in self.cut_points],
            "boundary_ties": list(self.boundary_ties),
            "mapping_rule": "D1: s < c1; D2: c1 <= s < c2; D3: c2 <= s < c3; D4: s >= c3",
            "assignment_rule": "rank split of (human_mean_score, int(puzzle_id)), sizes differ by <= 1",
        }


def _sort_key(item: RankedPuzzle) -> tuple[float, int]:
    return (item.human_mean_score, int(item.puzzle_id))


def assign_quartiles(
    puzzles: Sequence[RankedPuzzle],
) -> tuple[dict[str, str], QuartileSpec]:
    """Rank-split ``puzzles`` into D1..D4.

    Returns ``({puzzle_id: label}, spec)``. Requires at least four puzzles.
    """

    n = len(puzzles)
    if n < len(QUARTILE_LABELS):
        raise ValueError("Need at least four puzzles to form quartiles.")
    if len({p.puzzle_id for p in puzzles}) != n:
        raise ValueError("Puzzle ids must be unique.")

    ordered = sorted(puzzles, key=_sort_key)
    k = len(QUARTILE_LABELS)
    groups = [ordered[i * n // k:(i + 1) * n // k] for i in range(k)]

    labels = {p.puzzle_id: label for label, group in zip(QUARTILE_LABELS, groups) for p in group}
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
    )
    return labels, spec


def map_score(score: float, cut_points: Sequence[float]) -> str:
    """Map a mean guess score to D1..D4 with the value rule above."""

    if len(cut_points) != len(QUARTILE_LABELS) - 1:
        raise ValueError("Expected three cut-points.")
    if list(cut_points) != sorted(cut_points):
        raise ValueError("Cut-points must be non-decreasing.")

    for label, cut in zip(QUARTILE_LABELS, cut_points):
        if score < cut:
            return label
    return QUARTILE_LABELS[-1]
