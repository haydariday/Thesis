"""Distances between a system's guess-count distribution and the human one.

Bins are guesses 1..6 plus 7 for a loss.  Every function takes probability
vectors of length 7 (or per-run scores) and uses only the standard library.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

BINS = 7
MIN_EXPECTED = 5.0


def score_distribution(scores: Sequence[float]) -> list[float]:
    """Share of runs in each bin 1..7; scores must be whole numbers 1..7."""

    if not scores:
        raise ValueError("At least one score is needed.")
    counts = [0] * BINS
    for score in scores:
        index = int(score) - 1
        if index != score - 1 or not 0 <= index < BINS:
            raise ValueError(f"Score {score} is not a whole number from 1 to 7.")
        counts[index] += 1
    return [count / len(scores) for count in counts]


def wasserstein_1(p: Sequence[float], q: Sequence[float]) -> float:
    """Earth mover's distance on the ordered bins, in guesses."""

    total = cdf_p = cdf_q = 0.0
    for k in range(BINS - 1):
        cdf_p += p[k]
        cdf_q += q[k]
        total += abs(cdf_p - cdf_q)
    return total


def total_variation(p: Sequence[float], q: Sequence[float]) -> float:
    return 0.5 * sum(abs(a - b) for a, b in zip(p, q))


def jensen_shannon(p: Sequence[float], q: Sequence[float]) -> float:
    """Jensen-Shannon divergence in bits, from 0 (equal) to 1 (disjoint)."""

    def kl(a: Sequence[float], m: Sequence[float]) -> float:
        return sum(x * math.log2(x / y) for x, y in zip(a, m) if x > 0)

    middle = [(a + b) / 2 for a, b in zip(p, q)]
    return 0.5 * kl(p, middle) + 0.5 * kl(q, middle)


def merge_sparse_bins(
    observed: Sequence[float],
    expected: Sequence[float],
    minimum: float = MIN_EXPECTED,
) -> tuple[list[float], list[float]]:
    """Merge neighbouring bins until each has an expected count >= ``minimum``.

    Bins are merged left to right; a small remainder joins the last group.
    This is the usual rule for a valid chi-square approximation.
    """

    merged_o: list[float] = []
    merged_e: list[float] = []
    run_o = run_e = 0.0
    for o, e in zip(observed, expected):
        run_o += o
        run_e += e
        if run_e >= minimum:
            merged_o.append(run_o)
            merged_e.append(run_e)
            run_o = run_e = 0.0
    if run_e > 0 or run_o > 0:
        if merged_e:
            merged_o[-1] += run_o
            merged_e[-1] += run_e
        else:
            merged_o.append(run_o)
            merged_e.append(run_e)
    return merged_o, merged_e


def chi_square_sf(statistic: float, df: int) -> float:
    """Upper tail P(X >= statistic) of a chi-square with ``df`` degrees.

    Uses the regularised upper incomplete gamma Q(df/2, statistic/2), by
    series below a + 1 and by continued fraction above (Numerical Recipes).
    """

    if df < 1:
        raise ValueError("df must be at least 1.")
    if statistic <= 0:
        return 1.0

    a, x = df / 2.0, statistic / 2.0
    log_prefix = -x + a * math.log(x) - math.lgamma(a)

    if x < a + 1:
        term = total = 1.0 / a
        n = a
        for _ in range(1000):
            n += 1
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return max(0.0, 1.0 - total * math.exp(log_prefix))

    tiny = 1e-300
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(log_prefix) * h


def chi_square_gof(
    scores: Sequence[float],
    human: Sequence[float],
) -> dict[str, float | int | None]:
    """Goodness of fit of the system's runs against the human shares.

    Sparse bins are merged first, so the test is only as fine-grained as the
    run count allows.  With 32 runs this usually leaves three or four bins.
    """

    n = len(scores)
    observed = [share * n for share in score_distribution(scores)]
    expected = [share * n for share in human]
    merged_o, merged_e = merge_sparse_bins(observed, expected)
    df = len(merged_e) - 1

    if df < 1 or any(e <= 0 for e in merged_e):
        return {"statistic": None, "df": df, "p_value": None, "merged_bins": len(merged_e)}

    statistic = sum((o - e) ** 2 / e for o, e in zip(merged_o, merged_e))
    return {
        "statistic": statistic,
        "df": df,
        "p_value": chi_square_sf(statistic, df),
        "merged_bins": len(merged_e),
    }


def split_half_w1(
    scores_in_run_order: Sequence[float],
    seed: int,
    random_splits: int = 200,
) -> dict[str, float | None]:
    """W1 between the first and second half of a puzzle's runs.

    ``random_splits`` random halvings of the same runs give the value that
    chance alone produces.  An observed W1 well above that mean points to a
    change over the run sequence, such as provider drift.
    """

    half = len(scores_in_run_order) // 2
    if half < 1:
        return {"observed": None, "random_mean": None, "random_share_above": None}

    first = scores_in_run_order[:half]
    second = scores_in_run_order[half:]
    observed = wasserstein_1(score_distribution(first), score_distribution(second))

    rng = random.Random(seed)
    values = []
    shuffled = list(scores_in_run_order)
    for _ in range(random_splits):
        rng.shuffle(shuffled)
        values.append(
            wasserstein_1(
                score_distribution(shuffled[:half]),
                score_distribution(shuffled[half:]),
            )
        )

    return {
        "observed": observed,
        "random_mean": sum(values) / len(values),
        # Share of random splits at least as far apart as the real halves.
        "random_share_above": sum(v >= observed - 1e-12 for v in values) / len(values),
    }
