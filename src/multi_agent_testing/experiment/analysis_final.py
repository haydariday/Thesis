"""Final-study analysis: three conditions, paired contrasts and persona tests.

Final study, phase F6 (plan Section 7). Reads the three condition
directories (``--c1`` persona debate, ``--c2`` single agent, ``--c3`` debate
without personas), each holding ``experiment_config.json``, ``manifest.csv``,
``run_summary.csv`` and ``runs/``, plus the frozen ``terciles.json`` and
``quartiles.json``. Writes ``metrics.json``, ``condition_summary.csv``,
``contrasts.csv``, ``persona_stats.csv``, ``puzzle_summary.csv`` and
``runs.csv`` into ``--output-dir``. Only the Python standard library is used.

Usage::

    python -m multi_agent_testing.experiment.analysis_final \\
        --c1 experiments/final-c1 --c2 experiments/final-c2 \\
        --c3 experiments/final-c3 --output-dir experiments/final-analysis

Study conventions encoded here:

* The three configurations must be equal except for the persona line-up
  (``settings.personas``), the experiment id, the creation time and the
  local paths, and none may come from a dirty tree. Anything else refuses
  the analysis, since the comparison would then mix configurations.
* Scores are the 6-guess penalized scores (a loss is 7). Only completed runs
  carry a score; failed attempts are counted separately.
* Reporting uses values and p-values, without resampling (decided on
  2026-11-02). Spearman and Pearson carry the t-test p-value with n - 2 df.
  The ICCs carry the F-distribution 95% interval of Shrout and Fleiss.
* RQ2 categories are terciles by rank: the system means of the puzzles at
  hand are rank-split into T1..T3 and compared with the frozen human
  tercile from the manifest. Quartiles stay as a sensitivity check.
* ``constant_baseline_mae`` is the MAE of predicting every puzzle at the
  human mean of the puzzles at hand; ``bias_corrected_mae`` is the MAE
  after subtracting the system's own bias. A bias-corrected MAE below the
  baseline means the system carries puzzle-level information beyond a
  constant shift.
* Condition contrasts pair puzzles by id. For each puzzle the absolute
  error, the signed error and the within-puzzle SD are differenced, and
  each measure gets a two-sided Wilcoxon signed-rank test with Holm's
  correction over the two planned contrasts (debate effect C3 - C2,
  persona effect C1 - C3). C1 - C2 is reported without a test. The
  difference in Spearman rho is a value only.
* The persona check (plan Section 3) holds when C1's Cautious minus Bold
  per-game non-candidate share is significantly positive (Wilcoxon) and
  C3's neutral advisors do not differ (Friedman), both at ``ALPHA``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .analysis import _normalise_puzzle_id, _pearson, _round_output, _spearman
from .analysis_pilot02 import (
    PERSONA_COLUMNS,
    RUN_COLUMNS,
    Experiment,
    PuzzleRuns,
    _regularized_beta,
    alignment_metrics,
    consistency_metrics,
    correlation_p_value,
    load_cut_points,
    load_experiment,
    max_guesses,
    missing_as_loss,
    persona_rows,
    quadratic_weighted_kappa,
    run_rows,
)
from .distribution import score_distribution, wasserstein_1
from .nonparametric import wilcoxon_signed_rank
from .persona_stats import load_games, persona_statistics
from .terciles import TERCILE_LABELS, rank_split

CONDITIONS: tuple[tuple[str, str], ...] = (
    ("c1", "persona debate"),
    ("c2", "single agent"),
    ("c3", "debate without personas"),
)
# (name, minuend, subtrahend, tested)
CONTRASTS: tuple[tuple[str, str, str, bool], ...] = (
    ("debate_effect", "c3", "c2", True),
    ("persona_effect", "c1", "c3", True),
    ("overall", "c1", "c2", False),
)
CONTRAST_MEASURES = ("abs_error", "signed_error", "within_sd")
ALPHA = 0.05
# Persona statistics have no bootstrap here; these only fill the pilot's
# manipulation_check, which the final study does not report.
PERSONA_SEED = 20261103
PERSONA_RESAMPLES = 1
STANDARD_GUESSES = 6
HUMAN_BINS = ("p1", "p2", "p3", "p4", "p5", "p6", "p7")

# Config keys allowed to differ between conditions.
FREE_KEYS = frozenset({
    "experiment_id",
    "created_at",
    "dataset",
    "guess_list",
    "manifest_source",
})
FREE_SETTINGS = frozenset({"personas"})

CONDITION_COLUMNS = (
    "condition",
    "label",
    "puzzles",
    "completed_runs",
    "failed_attempts",
    "win_rate",
    "mean_within_sd",
    "icc_1_1",
    "icc_1_1_low",
    "icc_1_1_high",
    "icc_1_k",
    "icc_1_k_low",
    "icc_1_k_high",
    "spearman",
    "spearman_p",
    "pearson",
    "pearson_p",
    "signed_error",
    "mae",
    "bias_corrected_mae",
    "constant_baseline_mae",
    "tercile_exact",
    "tercile_adjacent",
    "tercile_kappa",
    "mean_prompt_tokens",
    "mean_completion_tokens",
    "mean_seconds",
    "mean_calls",
    "mean_rejected",
)

CONTRAST_COLUMNS = (
    "contrast",
    "minuend",
    "subtrahend",
    "measure",
    "tested",
    "pairs",
    "n",
    "mean_difference",
    "w_plus",
    "z",
    "p_value",
    "p_holm",
)

PUZZLE_COLUMNS = (
    "condition",
    "puzzle_id",
    "answer",
    "human_quartile",
    "human_tercile",
    "human_mean",
    "completed_runs",
    "failed_attempts",
    "system_mean",
    "system_sd",
    "signed_error",
    "abs_error",
    "system_rank_tercile",
)


@dataclass(frozen=True)
class Condition:
    name: str
    label: str
    experiment: Experiment
    terciles: dict[str, str]


# ---------------------------------------------------------------------------
# Loading and checks
# ---------------------------------------------------------------------------


def load_terciles(directory: Path) -> dict[str, str]:
    """Human tercile per puzzle id from the condition's manifest copy."""

    with (directory / "manifest.csv").open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    labels = {_normalise_puzzle_id(row["puzzle_id"]): (row.get("tercile") or "").strip() for row in rows}
    bad = sorted((pid for pid, label in labels.items() if label not in TERCILE_LABELS), key=int)
    if bad:
        raise ValueError(f"{directory}/manifest.csv: puzzles {bad} need a T1-T3 tercile.")
    return labels


def load_condition(name: str, label: str, directory: Path) -> Condition:
    return Condition(name, label, load_experiment(name, directory), load_terciles(directory))


def config_mismatches(conditions: Sequence[Condition]) -> list[str]:
    """Reasons the conditions are not one design apart from their personas."""

    first, *others = conditions
    reasons: list[str] = []
    base = first.experiment.config
    for other in others:
        config = other.experiment.config
        for key in sorted(set(base) | set(config)):
            if key in FREE_KEYS or key == "settings":
                continue
            if base.get(key) != config.get(key):
                reasons.append(f"{other.name}: {key} differs from {first.name}")
        settings_a, settings_b = base.get("settings") or {}, config.get("settings") or {}
        for key in sorted(set(settings_a) | set(settings_b)):
            if key not in FREE_SETTINGS and settings_a.get(key) != settings_b.get(key):
                reasons.append(f"{other.name}: settings.{key} differs from {first.name}")
    for condition in conditions:
        if condition.experiment.config.get("code_dirty"):
            reasons.append(f"{condition.name}: ran from a dirty tree")
        if max_guesses(condition.experiment.config) != STANDARD_GUESSES:
            reasons.append(f"{condition.name}: max_guesses is not {STANDARD_GUESSES}")
    return reasons


# ---------------------------------------------------------------------------
# RQ1: ICC with F intervals
# ---------------------------------------------------------------------------


def f_cdf(x: float, d1: float, d2: float) -> float:
    if x <= 0:
        return 0.0
    return _regularized_beta(d1 * x / (d1 * x + d2), d1 / 2, d2 / 2)


def f_quantile(p: float, d1: float, d2: float) -> float:
    """Inverse F cdf by bisection on a log scale."""

    low, high = 1e-12, 1.0
    while f_cdf(high, d1, d2) < p:
        high *= 2
    for _ in range(200):
        middle = math.sqrt(low * high)
        if f_cdf(middle, d1, d2) < p:
            low = middle
        else:
            high = middle
        if high / low < 1 + 1e-12:
            break
    return math.sqrt(low * high)


def icc_interval(groups: Sequence[Sequence[float]], alpha: float = ALPHA) -> dict[str, float | None]:
    """ICC(1,1) and ICC(1,k) with their F-distribution intervals.

    Shrout and Fleiss (1979), case 1: ``F = MSB / MSW`` with ``n - 1`` and
    ``N - n`` degrees of freedom. With ``F_L = F / F(1 - a/2; n-1, N-n)``
    and ``F_U = F * F(1 - a/2; N-n, n-1)`` the limits are
    ``(F_L - 1) / (F_L + k - 1)`` for ICC(1,1) and ``1 - 1 / F_L`` for
    ICC(1,k), likewise with ``F_U``. ``k`` is the average group size ``k0``.
    """

    groups = [list(g) for g in groups if g]
    total = sum(len(g) for g in groups)
    count = len(groups)
    out: dict[str, float | None] = {
        "icc_1_1": None, "icc_1_1_low": None, "icc_1_1_high": None,
        "icc_1_k": None, "icc_1_k_low": None, "icc_1_k_high": None,
        "k0": None, "f": None,
    }
    if count < 2 or total <= count:
        return out

    grand = statistics.fmean(v for g in groups for v in g)
    ms_between = sum(len(g) * (statistics.fmean(g) - grand) ** 2 for g in groups) / (count - 1)
    ms_within = sum((v - statistics.fmean(g)) ** 2 for g in groups for v in g) / (total - count)
    k0 = (total - sum(len(g) ** 2 for g in groups) / total) / (count - 1)
    out["k0"] = k0
    if ms_within <= 0 or ms_between <= 0:
        return out

    f = ms_between / ms_within
    df1, df2 = count - 1, total - count
    f_low = f / f_quantile(1 - alpha / 2, df1, df2)
    f_high = f * f_quantile(1 - alpha / 2, df2, df1)
    out.update(
        f=f,
        icc_1_1=(f - 1) / (f + k0 - 1),
        icc_1_1_low=(f_low - 1) / (f_low + k0 - 1),
        icc_1_1_high=(f_high - 1) / (f_high + k0 - 1),
        icc_1_k=1 - 1 / f,
        icc_1_k_low=1 - 1 / f_low,
        icc_1_k_high=1 - 1 / f_high,
    )
    return out


def rq1_metrics(puzzles: Sequence[PuzzleRuns]) -> dict[str, Any]:
    usable = [p.scores for p in puzzles if len(p.scores) >= 2]
    return {**consistency_metrics(puzzles), **icc_interval(usable)}


# ---------------------------------------------------------------------------
# RQ2: correlations, error and terciles
# ---------------------------------------------------------------------------


def category_agreement(
    pairs: Sequence[tuple[int, int]],
    labels: Sequence[str],
) -> dict[str, Any]:
    """Exact and adjacent agreement, QWK and confusion for ``(human, system)`` indices."""

    count = len(pairs)
    confusion = {h: {s: 0 for s in labels} for h in labels}
    for human, system in pairs:
        confusion[labels[human]][labels[system]] += 1
    return {
        "exact": sum(1 for h, s in pairs if h == s) / count if count else None,
        "adjacent": sum(1 for h, s in pairs if abs(h - s) <= 1) / count if count else None,
        "kappa": quadratic_weighted_kappa(pairs, len(labels)),
        "confusion": {"rows": "human", "columns": "system", "counts": confusion},
    }


def system_rank_terciles(scored: Sequence[PuzzleRuns]) -> dict[str, str]:
    if len(scored) < len(TERCILE_LABELS):
        return {}
    labels = rank_split(
        [p.system_mean for p in scored if p.system_mean is not None],
        [int(p.puzzle_id) for p in scored],
    )
    return {p.puzzle_id: label for p, label in zip(scored, labels)}


def rq2_metrics(
    puzzles: Sequence[PuzzleRuns],
    terciles: dict[str, str],
    quartile_cuts: Sequence[float],
) -> dict[str, Any]:
    scored = [p for p in puzzles if p.system_mean is not None]
    humans = [p.human_mean for p in scored]
    systems = [p.system_mean for p in scored if p.system_mean is not None]
    count = len(scored)

    spearman = _spearman(humans, systems)
    pearson = _pearson(humans, systems)
    bias = statistics.fmean(s - h for h, s in zip(humans, systems)) if count else None
    human_mean = statistics.fmean(humans) if count else None

    ranks = system_rank_terciles(scored)
    index = {label: i for i, label in enumerate(TERCILE_LABELS)}
    by_rank = category_agreement(
        [(index[terciles[p.puzzle_id]], index[ranks[p.puzzle_id]]) for p in scored if p.puzzle_id in ranks],
        TERCILE_LABELS,
    )
    quartiles = alignment_metrics(puzzles, quartile_cuts)

    return {
        "puzzles": count,
        "spearman": spearman,
        "spearman_p": correlation_p_value(spearman, count),
        "pearson": pearson,
        "pearson_p": correlation_p_value(pearson, count),
        "signed_error": bias,
        "mae": statistics.fmean(abs(s - h) for h, s in zip(humans, systems)) if count else None,
        "bias_corrected_mae": (
            statistics.fmean(abs(s - bias - h) for h, s in zip(humans, systems))
            if bias is not None else None
        ),
        "constant_baseline_mae": (
            statistics.fmean(abs(h - human_mean) for h in humans) if human_mean is not None else None
        ),
        "tercile_exact": by_rank["exact"],
        "tercile_adjacent": by_rank["adjacent"],
        "tercile_kappa": by_rank["kappa"],
        "tercile_confusion": by_rank["confusion"],
        "quartile_sensitivity": {
            "rank_quartile_exact": quartiles["rank_quartile_exact"],
            "rank_quartile_adjacent": quartiles["rank_quartile_adjacent"],
            "rank_quadratic_weighted_kappa": quartiles["rank_quadratic_weighted_kappa"],
            "rank_confusion_matrix": quartiles["rank_confusion_matrix"],
        },
    }


def tercile_distributions(puzzles: Sequence[PuzzleRuns], terciles: dict[str, str]) -> dict[str, Any]:
    """7-bin system distribution pooled by human tercile against the mean human bins."""

    out: dict[str, Any] = {}
    for label in TERCILE_LABELS:
        group = [p for p in puzzles if terciles.get(p.puzzle_id) == label]
        scores = [s for p in group for s in p.scores]
        bins = [p.human_bins for p in group if len(p.human_bins) == len(HUMAN_BINS)]
        if not scores or not bins:
            out[label] = None
            continue
        system = score_distribution(scores)
        human = [statistics.fmean(b[k] for b in bins) for k in range(len(HUMAN_BINS))]
        out[label] = {
            "puzzles": len(group),
            "runs": len(scores),
            "system": dict(zip(HUMAN_BINS, system)),
            "human": dict(zip(HUMAN_BINS, human)),
            "w1": wasserstein_1(system, human),
        }
    return out


# ---------------------------------------------------------------------------
# Contrasts
# ---------------------------------------------------------------------------


def puzzle_measures(puzzle: PuzzleRuns) -> dict[str, float | None]:
    mean = puzzle.system_mean
    return {
        "abs_error": abs(mean - puzzle.human_mean) if mean is not None else None,
        "signed_error": mean - puzzle.human_mean if mean is not None else None,
        "within_sd": puzzle.system_sd,
    }


def holm(p_values: Sequence[float | None]) -> list[float | None]:
    """Holm step-down adjusted p-values; None stays None and is not counted."""

    present = sorted((p, i) for i, p in enumerate(p_values) if p is not None)
    adjusted: list[float | None] = [None] * len(p_values)
    running = 0.0
    m = len(present)
    for rank, (p, i) in enumerate(present):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[i] = running
    return adjusted


def contrast_rows(conditions: dict[str, Condition]) -> list[dict[str, Any]]:
    measures = {
        name: {p.puzzle_id: puzzle_measures(p) for p in c.experiment.puzzles}
        for name, c in conditions.items()
    }
    rows: list[dict[str, Any]] = []
    for contrast, a, b, tested in CONTRASTS:
        for measure in CONTRAST_MEASURES:
            differences = [
                va - vb
                for pid in sorted(set(measures[a]) & set(measures[b]), key=int)
                if (va := measures[a][pid][measure]) is not None
                and (vb := measures[b][pid][measure]) is not None
            ]
            result = wilcoxon_signed_rank(differences)
            rows.append({
                "contrast": contrast,
                "minuend": a,
                "subtrahend": b,
                "measure": measure,
                "tested": tested,
                **{key: result[key] for key in ("pairs", "n", "mean_difference", "w_plus", "z")},
                "p_value": result["p_value"] if tested else None,
                "p_holm": None,
            })
    for measure in CONTRAST_MEASURES:
        tested_rows = [r for r in rows if r["measure"] == measure and r["tested"]]
        for row, adjusted in zip(tested_rows, holm([r["p_value"] for r in tested_rows])):
            row["p_holm"] = adjusted
    return rows


def spearman_differences(blocks: dict[str, dict[str, Any]]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for contrast, a, b, _ in CONTRASTS:
        ra, rb = blocks[a]["rq2"]["spearman"], blocks[b]["rq2"]["spearman"]
        out[contrast] = ra - rb if ra is not None and rb is not None else None
    return out


# ---------------------------------------------------------------------------
# Persona check, cost and assembly
# ---------------------------------------------------------------------------


def persona_check(stats: dict[str, dict[str, Any]], alpha: float = ALPHA) -> dict[str, Any]:
    c1 = stats["c1"].get("cautious_vs_bold")
    c3 = stats["c3"].get("advisor_difference")
    c1_holds = (
        None if c1 is None or c1["p_value"] is None
        else bool(c1["p_value"] < alpha and (c1["mean_difference"] or 0) > 0)
    )
    c3_differ = None if c3 is None or c3["p_value"] is None else bool(c3["p_value"] < alpha)
    return {
        "alpha": alpha,
        "c1_cautious_above_bold": c1_holds,
        "c3_neutral_advisors_differ": c3_differ,
        "personas_work": (
            None if c1_holds is None or c3_differ is None else c1_holds and not c3_differ
        ),
    }


def cost_metrics(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Mean tokens, seconds, calls and rejected replies per completed game."""

    done = [r for r in rows if r["status"] == "completed"]

    def mean(key: str) -> float | None:
        values = [float(r[key]) for r in done if r.get(key) not in (None, "")]
        return statistics.fmean(values) if values else None

    return {
        "attempts": len(rows),
        "completed": len(done),
        "failed": len(rows) - len(done),
        "mean_prompt_tokens": mean("prompt_tokens"),
        "mean_completion_tokens": mean("completion_tokens"),
        "mean_seconds": mean("elapsed_seconds"),
        "mean_calls": mean("agent_calls"),
        "mean_rejected": mean("rejected_responses"),
    }


@dataclass(frozen=True)
class AnalysisResult:
    metrics: dict[str, Any]
    tables: dict[str, list[dict[str, Any]]]


def analyse(conditions: dict[str, Condition], quartile_cuts: Sequence[float]) -> AnalysisResult:
    blocks: dict[str, dict[str, Any]] = {}
    persona: dict[str, dict[str, Any]] = {}
    tables: dict[str, list[dict[str, Any]]] = {
        "condition_summary": [], "persona_stats": [], "puzzle_summary": [], "runs": [],
    }

    for name, c in conditions.items():
        puzzles = c.experiment.puzzles
        runs = run_rows(c.experiment)
        stats = persona_statistics(load_games(c.experiment.directory / "runs"),
                                   PERSONA_SEED, PERSONA_RESAMPLES)
        stats.pop("manipulation_check", None)
        persona[name] = stats
        blocks[name] = {
            "label": c.label,
            "directory": str(c.experiment.directory),
            "code_revision": c.experiment.config.get("code_revision"),
            "persona_preset": ((c.experiment.config.get("settings") or {}).get("personas") or {}).get("preset"),
            "puzzles": len(puzzles),
            "failed_attempts": sum(p.failed_attempts for p in puzzles),
            "fingerprints": c.experiment.fingerprints,
            "rq1": rq1_metrics(puzzles),
            "rq2": rq2_metrics(puzzles, c.terciles, quartile_cuts),
            "rq3": stats,
            "cost": cost_metrics(runs),
            "sensitivity": {
                "missing_as_loss": rq2_metrics(
                    [missing_as_loss(p, STANDARD_GUESSES) for p in puzzles], c.terciles, quartile_cuts
                ),
                "tercile_distributions": tercile_distributions(puzzles, c.terciles),
            },
        }
        tables["condition_summary"].append(summary_row(name, blocks[name]))
        tables["persona_stats"].extend(persona_rows(name, stats))
        tables["puzzle_summary"].extend(puzzle_rows(c))
        tables["runs"].extend(runs)

    contrasts = contrast_rows(conditions)
    tables["contrasts"] = contrasts
    fingerprints = {name: sorted(b["fingerprints"]) for name, b in blocks.items()}
    metrics = {
        "generated_at": datetime.now(UTC).isoformat(),
        "analysis": "final F6",
        "alpha": ALPHA,
        "loss_score": "7 (6 guesses)",
        "conditions": blocks,
        "contrasts": contrasts,
        "spearman_differences": spearman_differences(blocks),
        "persona_check": persona_check(persona),
        "fingerprints": fingerprints,
        "fingerprint_warning": (
            None if len({fp for prints in fingerprints.values() for fp in prints}) <= 1
            else "More than one system_fingerprint: report the games on each fingerprint separately."
        ),
    }
    return AnalysisResult(metrics, tables)


def summary_row(name: str, block: dict[str, Any]) -> dict[str, Any]:
    rq1, rq2, cost = block["rq1"], block["rq2"], block["cost"]
    return {
        "condition": name,
        "label": block["label"],
        "puzzles": block["puzzles"],
        "completed_runs": rq1["completed_runs"],
        "failed_attempts": block["failed_attempts"],
        **{key: rq1[key] for key in (
            "win_rate", "mean_within_sd", "icc_1_1", "icc_1_1_low", "icc_1_1_high",
            "icc_1_k", "icc_1_k_low", "icc_1_k_high",
        )},
        **{key: rq2[key] for key in (
            "spearman", "spearman_p", "pearson", "pearson_p", "signed_error", "mae",
            "bias_corrected_mae", "constant_baseline_mae",
            "tercile_exact", "tercile_adjacent", "tercile_kappa",
        )},
        **{key: cost[key] for key in (
            "mean_prompt_tokens", "mean_completion_tokens", "mean_seconds", "mean_calls", "mean_rejected",
        )},
    }


def puzzle_rows(condition: Condition) -> list[dict[str, Any]]:
    puzzles = condition.experiment.puzzles
    ranks = system_rank_terciles([p for p in puzzles if p.system_mean is not None])
    return [
        {
            "condition": condition.name,
            "puzzle_id": p.puzzle_id,
            "answer": p.answer,
            "human_quartile": p.human_quartile,
            "human_tercile": condition.terciles.get(p.puzzle_id),
            "human_mean": p.human_mean,
            "completed_runs": len(p.scores),
            "failed_attempts": p.failed_attempts,
            "system_mean": p.system_mean,
            "system_sd": p.system_sd,
            **{key: puzzle_measures(p)[key] for key in ("signed_error", "abs_error")},
            "system_rank_tercile": ranks.get(p.puzzle_id),
        }
        for p in puzzles
    ]


TABLE_COLUMNS = {
    "condition_summary": CONDITION_COLUMNS,
    "contrasts": CONTRAST_COLUMNS,
    "persona_stats": PERSONA_COLUMNS,
    "puzzle_summary": PUZZLE_COLUMNS,
    "runs": RUN_COLUMNS,
}


def write_outputs(output_dir: Path, result: AnalysisResult) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(_round_output(result.metrics), indent=2) + "\n", encoding="utf-8"
    )
    for name, columns in TABLE_COLUMNS.items():
        with (output_dir / f"{name}.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(columns), extrasaction="ignore")
            writer.writeheader()
            for row in result.tables[name]:
                writer.writerow({
                    key: "" if row.get(key) is None else _round_output(row[key]) for key in columns
                })


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Final-study analysis of conditions C1, C2 and C3.")
    parser.add_argument("--c1", type=Path, required=True, help="Persona debate directory.")
    parser.add_argument("--c2", type=Path, required=True, help="Single-agent directory.")
    parser.add_argument("--c3", type=Path, required=True, help="Debate-without-personas directory.")
    parser.add_argument("--quartiles", type=Path, default=Path("src/data/processed/quartiles.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    directories = {"c1": args.c1, "c2": args.c2, "c3": args.c3}
    conditions = {
        name: load_condition(name, label, directories[name]) for name, label in CONDITIONS
    }
    mismatches = config_mismatches(list(conditions.values()))
    if mismatches:
        parser.error("The conditions are not one configuration:\n  " + "\n  ".join(mismatches))

    result = analyse(conditions, load_cut_points(args.quartiles))
    write_outputs(args.output_dir, result)

    for name, block in result.metrics["conditions"].items():
        rq1, rq2 = block["rq1"], block["rq2"]
        print(
            f"{name} ({block['label']}): {rq1['completed_runs']} runs, SD {rq1['mean_within_sd']}, "
            f"ICC(1,1) {rq1['icc_1_1']}, Spearman {rq2['spearman']} (p {rq2['spearman_p']}), "
            f"bias {rq2['signed_error']}, MAE {rq2['mae']}, tercile QWK {rq2['tercile_kappa']}"
        )
    for row in result.metrics["contrasts"]:
        if row["tested"]:
            print(f"{row['contrast']} {row['measure']}: mean diff {row['mean_difference']}, "
                  f"p {row['p_value']}, Holm {row['p_holm']}")
    print(f"Persona check: {result.metrics['persona_check']}")
    if result.metrics["fingerprint_warning"]:
        print(result.metrics["fingerprint_warning"])
    print(f"Wrote {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
