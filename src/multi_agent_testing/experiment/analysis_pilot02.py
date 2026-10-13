"""Pilot-02 analysis (P12): RQ1 consistency and RQ2 mean and D1-D4 agreement.

Reads one or both pilot-02 experiment directories (``--deep`` for Exp A,
``--wide`` for Exp B), each holding ``experiment_config.json``,
``manifest.csv``, ``run_summary.csv`` and ``runs/``, plus the frozen
``quartiles.json``.  Writes ``metrics.json`` and ``puzzle_summary.csv`` into
``--output-dir``.  Only the Python standard library is used.

Usage::

    python -m multi_agent_testing.experiment.analysis_pilot02 \
        --deep experiments/pilot-02-deep --wide experiments/pilot-02-wide \
        --output-dir experiments/pilot-02-analysis

Study conventions encoded here:

* Finished losses score 7.  Only completed runs carry a score; failed
  attempts are counted separately and never scored.
* RQ1 is descriptive in pilot-02 (decided at P0): estimates with CIs and no
  pass/fail margin.  Exp A is the primary RQ1 source; Exp B's 3-run figures
  are reported for completeness only.
* RQ2 pairs each puzzle's system mean with its human mean.  Exp B is the
  primary RQ2 source and Exp A a check.  The human quartile is the frozen
  rank-based label from the manifest; the system mean is mapped by value
  with the frozen cut-points (``quartiles.map_score``).
* CIs come from a puzzle-level bootstrap stratified by human quartile, so
  every resample keeps the design's quartile balance.  Runs are never
  treated as independent puzzles.
* Deep and wide are pooled only when their configurations, code revision
  and model fingerprints match (README reuse rule 1).  The pooled block is
  a robustness check, never the primary result.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .analysis import (
    BOOTSTRAP_RESAMPLES,
    CI_HIGH_FRACTION,
    CI_LOW_FRACTION,
    INFRA_STATUSES,
    _normalise_puzzle_id,
    _parse_float,
    _pearson,
    _percentile,
    _round_output,
    _spearman,
    load_config,
    load_run_attempts,
    planned_repetitions,
)
from .quartiles import QUARTILE_LABELS, map_score

DEFAULT_SEED = 20261015
LOSS_SCORE = 7.0

# Settings that may differ between Exp A and Exp B without breaking pooling.
DESIGN_SETTINGS = frozenset({"repetitions"})

PUZZLE_SUMMARY_COLUMNS = (
    "experiment",
    "puzzle_id",
    "answer",
    "human_quartile",
    "human_mean",
    "human_mean_low",
    "human_mean_high",
    "planned_runs",
    "completed_runs",
    "failed_attempts",
    "wins",
    "losses",
    "win_rate",
    "system_mean",
    "system_sd",
    "system_quartile",
    "quartile_shift",
    "mean_error",
    "exact_match_rate",
    "mean_pairwise_abs_diff",
)


@dataclass(frozen=True)
class PuzzleRuns:
    """Completed scores and human reference for one puzzle in one experiment."""

    experiment: str
    puzzle_id: str
    answer: str
    human_quartile: str
    human_mean: float
    human_mean_low: float | None
    human_mean_high: float | None
    planned_runs: int
    scores: tuple[float, ...]
    wins: int
    losses: int
    failed_attempts: int

    @property
    def system_mean(self) -> float | None:
        return statistics.fmean(self.scores) if self.scores else None

    @property
    def system_sd(self) -> float | None:
        return statistics.stdev(self.scores) if len(self.scores) >= 2 else None


@dataclass(frozen=True)
class Experiment:
    """One loaded experiment directory."""

    name: str
    directory: Path
    config: dict[str, Any]
    puzzles: tuple[PuzzleRuns, ...]
    attempts: int
    fingerprints: dict[str, int]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_cut_points(path: Path) -> list[float]:
    """The frozen D1-D4 cut-points from ``quartiles.json``."""

    data = json.loads(path.read_text(encoding="utf-8"))
    cut_points = [float(value) for value in data["cut_points"]]
    if len(cut_points) != len(QUARTILE_LABELS) - 1:
        raise ValueError(f"{path} must hold three cut-points.")
    return cut_points


def load_fingerprints(runs_dir: Path) -> dict[str, int]:
    """Count model calls per ``system_fingerprint`` over every run file."""

    counts: dict[str, int] = {}
    if not runs_dir.is_dir():
        return counts

    for path in sorted(runs_dir.glob("*.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for call in run.get("calls") or []:
            key = call.get("system_fingerprint") or "unknown"
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def load_experiment(name: str, directory: Path) -> Experiment:
    """Join the manifest with completed run scores for one experiment."""

    config = load_config(directory / "experiment_config.json")
    attempts = load_run_attempts(directory / "run_summary.csv")
    planned = planned_repetitions(config)

    by_puzzle: dict[str, list] = {}
    for attempt in attempts:
        by_puzzle.setdefault(attempt.puzzle_id, []).append(attempt)

    puzzles: list[PuzzleRuns] = []
    with (directory / "manifest.csv").open("r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            puzzle_id = _normalise_puzzle_id(row["puzzle_id"])
            human_mean = _parse_float(row.get("human_mean_score"))
            quartile = (row.get("quartile") or "").strip()
            if human_mean is None or quartile not in QUARTILE_LABELS:
                raise ValueError(
                    f"{directory}/manifest.csv: puzzle {puzzle_id} needs "
                    "human_mean_score and a D1-D4 quartile."
                )

            rows = by_puzzle.get(puzzle_id, [])
            completed = [
                a for a in rows
                if a.status == "completed" and a.penalized_score is not None
            ]
            puzzles.append(
                PuzzleRuns(
                    experiment=name,
                    puzzle_id=puzzle_id,
                    answer=(row.get("answer") or "").strip(),
                    human_quartile=quartile,
                    human_mean=human_mean,
                    human_mean_low=_parse_float(row.get("human_mean_low")),
                    human_mean_high=_parse_float(row.get("human_mean_high")),
                    planned_runs=planned,
                    scores=tuple(float(a.penalized_score) for a in completed),
                    wins=sum(1 for a in completed if a.won is True),
                    losses=sum(1 for a in completed if a.won is False),
                    failed_attempts=sum(
                        1 for a in rows if a.status in INFRA_STATUSES
                    ),
                )
            )

    puzzles.sort(key=lambda item: int(item.puzzle_id))
    return Experiment(
        name=name,
        directory=directory,
        config=config,
        puzzles=tuple(puzzles),
        attempts=len(attempts),
        fingerprints=load_fingerprints(directory / "runs"),
    )


# ---------------------------------------------------------------------------
# RQ1: consistency
# ---------------------------------------------------------------------------


def icc_oneway(groups: Sequence[Sequence[float]]) -> dict[str, float | None]:
    """One-way random-effects ICC(1,1) and ICC(1,k) (Shrout and Fleiss 1979).

    Unequal group sizes use the average group size ``k0`` from the
    one-way ANOVA.  Returns ``None`` values when the ICC is undefined, for
    example when every score in every group is identical.
    """

    groups = [list(group) for group in groups if len(group) >= 1]
    total = sum(len(group) for group in groups)
    count = len(groups)
    empty: dict[str, float | None] = {"icc_1_1": None, "icc_1_k": None, "k0": None}

    if count < 2 or total <= count:
        return empty

    grand = statistics.fmean(value for group in groups for value in group)
    between = sum(
        len(group) * (statistics.fmean(group) - grand) ** 2 for group in groups
    )
    within = sum(
        (value - statistics.fmean(group)) ** 2
        for group in groups
        for value in group
    )
    ms_between = between / (count - 1)
    ms_within = within / (total - count)
    k0 = (total - sum(len(group) ** 2 for group in groups) / total) / (count - 1)

    denominator = ms_between + (k0 - 1) * ms_within
    if denominator <= 0 or ms_between <= 0:
        return {**empty, "k0": k0}

    return {
        "icc_1_1": (ms_between - ms_within) / denominator,
        "icc_1_k": (ms_between - ms_within) / ms_between,
        "k0": k0,
    }


def pairwise_agreement(scores: Sequence[float]) -> tuple[int, int, float]:
    """Return (run pairs, exactly matching pairs, summed absolute difference)."""

    pairs = matches = 0
    difference = 0.0
    for i in range(len(scores)):
        for j in range(i + 1, len(scores)):
            pairs += 1
            matches += scores[i] == scores[j]
            difference += abs(scores[i] - scores[j])
    return pairs, matches, difference


def consistency_metrics(puzzles: Sequence[PuzzleRuns]) -> dict[str, Any]:
    """RQ1 point estimates over puzzles with at least two completed runs."""

    usable = [p for p in puzzles if len(p.scores) >= 2]
    sds = [p.system_sd for p in usable if p.system_sd is not None]
    pair_totals = [pairwise_agreement(p.scores) for p in usable]
    pairs = sum(total[0] for total in pair_totals)

    within_ss = sum(
        (score - statistics.fmean(p.scores)) ** 2
        for p in usable
        for score in p.scores
    )
    within_df = sum(len(p.scores) - 1 for p in usable)
    runs = sum(len(p.scores) for p in puzzles)
    wins = sum(p.wins for p in puzzles)

    return {
        "puzzles": len(usable),
        "mean_within_sd": statistics.fmean(sds) if sds else None,
        "median_within_sd": statistics.median(sds) if sds else None,
        "max_within_sd": max(sds) if sds else None,
        "pooled_within_sd": (within_ss / within_df) ** 0.5 if within_df else None,
        **icc_oneway([p.scores for p in usable]),
        "exact_match_rate": (
            sum(total[1] for total in pair_totals) / pairs if pairs else None
        ),
        "mean_pairwise_abs_diff": (
            sum(total[2] for total in pair_totals) / pairs if pairs else None
        ),
        "completed_runs": runs,
        "win_rate": wins / runs if runs else None,
        "loss_share": (runs - wins) / runs if runs else None,
    }


RQ1_BOOTSTRAP = (
    "mean_within_sd",
    "pooled_within_sd",
    "icc_1_1",
    "icc_1_k",
    "exact_match_rate",
    "mean_pairwise_abs_diff",
    "win_rate",
)


# ---------------------------------------------------------------------------
# RQ2: mean and D1-D4 agreement
# ---------------------------------------------------------------------------


def quadratic_weighted_kappa(
    pairs: Sequence[tuple[int, int]],
    categories: int,
) -> float | None:
    """Cohen's kappa with quadratic weights for ordinal labels ``0..K-1``."""

    if not pairs or categories < 2:
        return None

    total = len(pairs)
    observed = [[0.0] * categories for _ in range(categories)]
    for human, system in pairs:
        observed[human][system] += 1

    rows = [sum(row) for row in observed]
    cols = [sum(observed[i][j] for i in range(categories)) for j in range(categories)]
    scale = (categories - 1) ** 2

    disagreement = expected = 0.0
    for i in range(categories):
        for j in range(categories):
            weight = (i - j) ** 2 / scale
            disagreement += weight * observed[i][j]
            expected += weight * rows[i] * cols[j] / total

    if expected == 0:
        return None
    return 1.0 - disagreement / expected


def alignment_metrics(
    puzzles: Sequence[PuzzleRuns],
    cut_points: Sequence[float],
) -> dict[str, Any]:
    """RQ2 point estimates over puzzles with at least one completed run."""

    scored = [p for p in puzzles if p.system_mean is not None]
    humans = [p.human_mean for p in scored]
    systems = [p.system_mean for p in scored if p.system_mean is not None]
    index = {label: position for position, label in enumerate(QUARTILE_LABELS)}
    labels = [
        (index[p.human_quartile], index[map_score(s, cut_points)])
        for p, s in zip(scored, systems)
    ]
    size = len(QUARTILE_LABELS)

    confusion = {
        human: {system: 0 for system in QUARTILE_LABELS}
        for human in QUARTILE_LABELS
    }
    for human, system in labels:
        confusion[QUARTILE_LABELS[human]][QUARTILE_LABELS[system]] += 1

    recall = {}
    for position, label in enumerate(QUARTILE_LABELS):
        row = [system for human, system in labels if human == position]
        recall[label] = (
            sum(1 for system in row if system == position) / len(row)
            if row
            else None
        )

    count = len(labels)
    return {
        "puzzles": count,
        "mae": statistics.fmean(abs(s - h) for h, s in zip(humans, systems)) if count else None,
        "signed_error": statistics.fmean(s - h for h, s in zip(humans, systems)) if count else None,
        "spearman": _spearman(humans, systems),
        "pearson": _pearson(humans, systems),
        "quartile_exact": (
            sum(1 for h, s in labels if h == s) / count if count else None
        ),
        "quartile_adjacent": (
            sum(1 for h, s in labels if abs(h - s) <= 1) / count if count else None
        ),
        "quadratic_weighted_kappa": quadratic_weighted_kappa(labels, size),
        "quartile_recall": recall,
        "confusion_matrix": {"rows": "human", "columns": "system", "counts": confusion},
    }


RQ2_BOOTSTRAP = (
    "mae",
    "signed_error",
    "spearman",
    "pearson",
    "quartile_exact",
    "quartile_adjacent",
    "quadratic_weighted_kappa",
)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


def stratified_bootstrap(
    puzzles: Sequence[PuzzleRuns],
    statistic: Callable[[Sequence[PuzzleRuns]], dict[str, Any]],
    names: Sequence[str],
    seed: int,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Percentile CIs from resampling puzzles within each human quartile."""

    point = statistic(puzzles)
    strata: dict[str, list[PuzzleRuns]] = {}
    for puzzle in puzzles:
        strata.setdefault(puzzle.human_quartile, []).append(puzzle)

    result: dict[str, Any] = {
        "resamples": resamples,
        "seed": seed,
        "ci_level": 0.95,
        "unit": "puzzle, stratified by human quartile",
    }
    if len(puzzles) < 2:
        return {**result, **{name: None for name in names}}

    rng = random.Random(seed)
    draws: dict[str, list[float]] = {name: [] for name in names}
    groups = [strata[key] for key in sorted(strata)]
    for _ in range(resamples):
        sample = [
            group[rng.randrange(len(group))]
            for group in groups
            for _ in range(len(group))
        ]
        values = statistic(sample)
        for name in names:
            if values.get(name) is not None:
                draws[name].append(values[name])

    for name in names:
        if point.get(name) is None:
            result[name] = None
            continue
        ordered = sorted(draws[name])
        result[name] = {
            "point": point[name],
            "ci_low": _percentile(ordered, CI_LOW_FRACTION),
            "ci_high": _percentile(ordered, CI_HIGH_FRACTION),
            "valid_resamples": len(ordered),
        }
    return result


# ---------------------------------------------------------------------------
# Pooling
# ---------------------------------------------------------------------------


def pooling_blockers(experiments: Sequence[Experiment]) -> list[str]:
    """Reasons Exp A and Exp B may not be pooled (README reuse rule 1)."""

    if len(experiments) < 2:
        return ["only one experiment loaded"]

    first, *others = experiments
    reasons: list[str] = []
    keys = ("code_revision", "source_sha256", "dataset_sha256", "guess_list_sha256")

    for other in others:
        for key in keys:
            if first.config.get(key) != other.config.get(key):
                reasons.append(f"{key} differs")

        settings_a = first.config.get("settings") or {}
        settings_b = other.config.get("settings") or {}
        for key in sorted(set(settings_a) | set(settings_b)):
            if key not in DESIGN_SETTINGS and settings_a.get(key) != settings_b.get(key):
                reasons.append(f"settings.{key} differs")

    fingerprints = [set(e.fingerprints) for e in experiments]
    if any(len(prints) != 1 for prints in fingerprints) or len(set.union(*fingerprints)) != 1:
        reasons.append(
            "model fingerprints are not one shared value: "
            + "; ".join(f"{e.name}={sorted(e.fingerprints)}" for e in experiments)
        )
    return reasons


# ---------------------------------------------------------------------------
# Assembly and output
# ---------------------------------------------------------------------------


def experiment_block(
    experiment: Experiment,
    cut_points: Sequence[float],
    seed: int,
    resamples: int,
) -> dict[str, Any]:
    puzzles = experiment.puzzles
    return {
        "directory": str(experiment.directory),
        "code_revision": experiment.config.get("code_revision"),
        "planned_runs_per_puzzle": planned_repetitions(experiment.config),
        "puzzles": len(puzzles),
        "puzzles_with_all_planned_runs": sum(
            1 for p in puzzles if len(p.scores) >= p.planned_runs
        ),
        "attempts": experiment.attempts,
        "failed_attempts": sum(p.failed_attempts for p in puzzles),
        "fingerprints": experiment.fingerprints,
        "rq1": consistency_metrics(puzzles),
        "rq1_bootstrap": stratified_bootstrap(
            puzzles, consistency_metrics, RQ1_BOOTSTRAP, seed, resamples
        ),
        "rq2": alignment_metrics(puzzles, cut_points),
        "rq2_bootstrap": stratified_bootstrap(
            puzzles,
            lambda sample: alignment_metrics(sample, cut_points),
            RQ2_BOOTSTRAP,
            seed,
            resamples,
        ),
    }


def analyse(
    experiments: Sequence[Experiment],
    cut_points: Sequence[float],
    seed: int = DEFAULT_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Build the full metrics document."""

    blockers = pooling_blockers(experiments)
    pooled = None
    if not blockers:
        puzzles = [p for e in experiments for p in e.puzzles]
        pooled = {
            "role": "robustness check for RQ2 mean alignment, not primary",
            "rq2": alignment_metrics(puzzles, cut_points),
            "rq2_bootstrap": stratified_bootstrap(
                puzzles,
                lambda sample: alignment_metrics(sample, cut_points),
                RQ2_BOOTSTRAP,
                seed,
                resamples,
            ),
        }

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "analysis": "pilot-02 P12",
        "cut_points": list(cut_points),
        "loss_score": LOSS_SCORE,
        "experiments": {
            e.name: experiment_block(e, cut_points, seed, resamples)
            for e in experiments
        },
        "pooled": pooled,
        "pooling_blockers": blockers,
        "notes": [
            "RQ1 is descriptive in pilot-02; Exp A (deep) is its primary source.",
            "RQ2 primary source is Exp B (wide); Exp A is a check.",
            "Human quartile is the frozen rank label; system quartile maps the "
            "system mean by value with the frozen cut-points.",
            "CIs resample puzzles within human quartiles; runs are never "
            "treated as independent puzzles.",
        ],
    }


def puzzle_rows(
    experiments: Sequence[Experiment],
    cut_points: Sequence[float],
) -> list[dict[str, Any]]:
    rows = []
    index = {label: position for position, label in enumerate(QUARTILE_LABELS)}
    for experiment in experiments:
        for p in experiment.puzzles:
            mean = p.system_mean
            system_quartile = map_score(mean, cut_points) if mean is not None else None
            pairs, matches, difference = pairwise_agreement(p.scores)
            runs = len(p.scores)
            rows.append(
                {
                    "experiment": p.experiment,
                    "puzzle_id": p.puzzle_id,
                    "answer": p.answer,
                    "human_quartile": p.human_quartile,
                    "human_mean": p.human_mean,
                    "human_mean_low": p.human_mean_low,
                    "human_mean_high": p.human_mean_high,
                    "planned_runs": p.planned_runs,
                    "completed_runs": runs,
                    "failed_attempts": p.failed_attempts,
                    "wins": p.wins,
                    "losses": p.losses,
                    "win_rate": p.wins / runs if runs else None,
                    "system_mean": mean,
                    "system_sd": p.system_sd,
                    "system_quartile": system_quartile,
                    "quartile_shift": (
                        index[system_quartile] - index[p.human_quartile]
                        if system_quartile
                        else None
                    ),
                    "mean_error": mean - p.human_mean if mean is not None else None,
                    "exact_match_rate": matches / pairs if pairs else None,
                    "mean_pairwise_abs_diff": difference / pairs if pairs else None,
                }
            )
    return rows


def write_outputs(
    output_dir: Path,
    metrics: dict[str, Any],
    rows: Sequence[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(_round_output(metrics), indent=2) + "\n", encoding="utf-8"
    )
    with (output_dir / "puzzle_summary.csv").open("w", encoding="utf-8", newline="") as file:
        fieldnames: list[str] = list(PUZZLE_SUMMARY_COLUMNS)
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {key: "" if value is None else _round_output(value) for key, value in row.items()}
            )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pilot-02 analysis: RQ1 consistency and RQ2 alignment."
    )
    parser.add_argument("--deep", type=Path, help="Exp A directory (RQ1 primary).")
    parser.add_argument("--wide", type=Path, help="Exp B directory (RQ2 primary).")
    parser.add_argument(
        "--quartiles",
        type=Path,
        default=Path("src/data/processed/quartiles.json"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    args = parser.parse_args(argv)

    if args.deep is None and args.wide is None:
        parser.error("Give --deep, --wide or both.")

    experiments = [
        load_experiment(name, directory)
        for name, directory in (("deep", args.deep), ("wide", args.wide))
        if directory is not None
    ]
    cut_points = load_cut_points(args.quartiles)
    metrics = analyse(experiments, cut_points, args.seed, args.resamples)
    write_outputs(args.output_dir, metrics, puzzle_rows(experiments, cut_points))

    for name, block in metrics["experiments"].items():
        rq1, rq2 = block["rq1"], block["rq2"]
        print(
            f"{name}: {rq1['completed_runs']} runs, win rate {rq1['win_rate']}, "
            f"mean within-SD {rq1['mean_within_sd']}, ICC(1,1) {rq1['icc_1_1']}, "
            f"MAE {rq2['mae']}, QWK {rq2['quadratic_weighted_kappa']}"
        )
    print("pooled:" if metrics["pooled"] else "not pooled:", metrics["pooling_blockers"] or "ok")
    print(f"Wrote {args.output_dir / 'metrics.json'} and puzzle_summary.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
