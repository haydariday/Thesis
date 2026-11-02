"""Rank tests for paired data: Wilcoxon signed-rank and Friedman.

Final study, phase F5. Standard library only. Both tests use their large-
sample approximations with the usual tie corrections, which suit the final
study's sizes (100 puzzles, 1,000 games per condition). ``n`` is reported
with every result, so small samples can be read with care.

Wilcoxon signed-rank (two-sided)
--------------------------------
Zero differences are dropped (Wilcoxon's method). The absolute differences
get average ranks, ``W+`` is the rank sum of the positive differences, and::

    z = (W+ - n(n+1)/4) / sqrt(n(n+1)(2n+1)/24 - sum(t^3 - t)/48)
    p = erfc(|z| / sqrt(2))

with ``t`` the size of each group of tied absolute differences. There is no
continuity correction.

Friedman
--------
Each block (a game, or a puzzle) ranks its ``k`` treatments with average
ranks. With ``R_j`` the rank sum of treatment ``j`` over ``n`` blocks::

    Q = (12 / (n k (k+1)) * sum(R_j^2) - 3 n (k+1)) / C
    C = 1 - sum(t^3 - t) / (n k (k^2 - 1))

and ``p`` is the chi-square upper tail with ``k - 1`` degrees of freedom.
When every block is fully tied, ``C`` is zero and the result is ``Q = 0``,
``p = 1``.
"""

import math
from collections import Counter
from collections.abc import Sequence
from typing import Any

from .distribution import chi_square_sf


def _average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        for position in range(start, end + 1):
            ranks[order[position]] = (start + end) / 2 + 1
        start = end + 1
    return ranks


def _tie_term(values: Sequence[float]) -> int:
    return sum(t ** 3 - t for t in Counter(values).values())


def wilcoxon_signed_rank(differences: Sequence[float]) -> dict[str, Any]:
    """Two-sided Wilcoxon signed-rank test that the median difference is zero."""

    nonzero = [d for d in differences if d != 0]
    n = len(nonzero)
    result: dict[str, Any] = {
        "test": "wilcoxon_signed_rank",
        "pairs": len(differences),
        "n": n,
        "zeros_dropped": len(differences) - n,
        "mean_difference": sum(differences) / len(differences) if differences else None,
        "w_plus": None,
        "z": None,
        "p_value": None,
    }
    if n == 0:
        return result

    magnitudes = [abs(d) for d in nonzero]
    ranks = _average_ranks(magnitudes)
    w_plus = sum(rank for rank, d in zip(ranks, nonzero) if d > 0)
    variance = n * (n + 1) * (2 * n + 1) / 24 - _tie_term(magnitudes) / 48
    result["w_plus"] = w_plus
    if variance <= 0:
        return result

    z = (w_plus - n * (n + 1) / 4) / math.sqrt(variance)
    result["z"] = z
    result["p_value"] = math.erfc(abs(z) / math.sqrt(2))
    return result


def friedman(blocks: Sequence[Sequence[float]], labels: Sequence[str]) -> dict[str, Any]:
    """Friedman test that ``k`` related treatments share one distribution.

    ``blocks`` holds one row per block with one value per label, in label
    order. Needs at least two labels.
    """

    k = len(labels)
    if k < 2:
        raise ValueError("The Friedman test needs at least two treatments.")
    if any(len(row) != k for row in blocks):
        raise ValueError("Every block needs one value per treatment.")

    n = len(blocks)
    result: dict[str, Any] = {
        "test": "friedman",
        "treatments": list(labels),
        "n": n,
        "df": k - 1,
        "mean_ranks": None,
        "statistic": None,
        "p_value": None,
    }
    if n == 0:
        return result

    rank_rows = [_average_ranks(row) for row in blocks]
    rank_sums = [sum(row[j] for row in rank_rows) for j in range(k)]
    result["mean_ranks"] = {label: total / n for label, total in zip(labels, rank_sums)}

    correction = 1 - sum(_tie_term(row) for row in blocks) / (n * k * (k * k - 1))
    if correction <= 0:
        result["statistic"] = 0.0
        result["p_value"] = 1.0
        return result

    statistic = (
        12 / (n * k * (k + 1)) * sum(total ** 2 for total in rank_sums) - 3 * n * (k + 1)
    ) / correction
    statistic = max(statistic, 0.0)
    result["statistic"] = statistic
    result["p_value"] = chi_square_sf(statistic, k - 1)
    return result
