"""Analysis stage for a finished Wordle multi-agent playtesting experiment.

Reads ``run_summary.csv``, ``manifest.csv``, and ``experiment_config.json``
from an experiment directory and writes ``puzzle_summary.csv``,
``threshold_sensitivity.csv``, ``termination_stats.csv``, and
``metrics.json`` into the same directory.  Only the Python standard
library is used.

Usage::

    python -m multi_agent_testing.experiment.analysis \
        --experiment-dir experiments/pilot-01 [--seed 20261008]

Study conventions encoded here:

* Finished losses are scored 7 (a loss penalty, not a seventh guess).
* The primary easy/hard threshold is the pre-registered value from the
  experiment config (4.0 in this study); 3.8 and 4.2 are sensitivity
  checks, not replacement thresholds.
* The primary panel contains manifest puzzles with at least the planned
  number of completed runs.  Descriptive follow-up numbers are reported
  separately over every puzzle with at least one completed run.
* Human difficulty means come from the manifest and are approximate when
  reconstructed from whole-percent rounded guess-distribution bins.
* Debate termination statistics (``gm_stop`` versus ``max_rounds`` and
the round at which each debate ended) are descriptive supporting
measurements for the frozen ``max_rounds`` configuration; they are not
hypothesis tests.

Attempt rows for puzzles that are not in the manifest (for example from a
superseded selection) are ignored.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_REPETITIONS = 5
DEFAULT_SEED = 20261008
DEFAULT_PRIMARY_THRESHOLD = 4.0
DEFAULT_THRESHOLDS: tuple[float, ...] = (3.8, 4.0, 4.2)
BOOTSTRAP_RESAMPLES = 10_000
CI_LOW_FRACTION = 0.025
CI_HIGH_FRACTION = 0.975
INFRA_STATUSES = frozenset({"failed", "interrupted", "running"})
ROUNDING_PLACES = 6

PUZZLE_SUMMARY_COLUMNS = (
    "puzzle_id",
    "answer",
    "human_mean_score",
    "human_label",
    "planned_repetitions",
    "completed_runs",
    "wins",
    "losses",
    "infra_failures",
    "win_rate",
    "system_mean",
    "system_sd",
    "system_label",
    "label_agreement",
    "turns",
    "gm_stop_turns",
    "max_rounds_turns",
)

THRESHOLD_SENSITIVITY_COLUMNS = (
    "threshold",
    "balanced_accuracy",
    "accuracy",
    "recall_easy",
    "recall_hard",
    "human_easy_system_easy",
    "human_easy_system_hard",
    "human_hard_system_easy",
    "human_hard_system_hard",
)

TERMINATION_STATS_COLUMNS = (
    "group",
    "puzzles",
    "turns",
    "gm_stop_turns",
    "max_rounds_turns",
    "gm_stop_share",
    "max_rounds_share",
)


@dataclass(frozen=True)
class RunAttempt:
    """One row of ``run_summary.csv``."""

    run_id: str
    puzzle_id: str
    status: str
    won: bool | None
    penalized_score: float | None
    total_tokens: int | None
    agent_calls: int
    rejected_responses: int
    backend_errors: int
    turns: int
    gm_stop_turns: int
    max_rounds_turns: int


@dataclass(frozen=True)
class ManifestPuzzle:
    """One selected puzzle from ``manifest.csv``."""

    puzzle_id: str
    answer: str
    human_mean_score: float | None
    human_label: str


@dataclass(frozen=True)
class PuzzleStats:
    """Per-puzzle aggregate used by every later computation."""

    puzzle_id: str
    answer: str
    human_mean_score: float | None
    human_label: str
    planned_repetitions: int
    completed_runs: int
    wins: int
    losses: int
    infra_failures: int
    win_rate: float | None
    system_mean: float | None
    system_sd: float | None
    system_label: str
    label_agreement: bool | None
    turns: int
    gm_stop_turns: int
    max_rounds_turns: int


@dataclass(frozen=True)
class AlignmentPair:
    """A panel puzzle with both a system mean and a human mean."""

    puzzle_id: str
    human: float
    system: float


@dataclass(frozen=True)
class AnalysisOutput:
    """Everything the CLI needs to write files and print a summary."""

    metrics: dict[str, Any]
    puzzle_stats: tuple[PuzzleStats, ...]
    sensitivity: tuple[dict[str, Any], ...]
    termination_rows: tuple[dict[str, Any], ...]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _clean(value: str | None) -> str:
    """Strip a CSV cell, mapping ``None`` to an empty string."""

    return "" if value is None else value.strip()


def _parse_float(value: str | None) -> float | None:
    """Parse an optional float cell, raising on malformed input."""

    text = _clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError as error:
        raise ValueError(f"Expected a number, got {value!r}.") from error


def _parse_count(value: str | None) -> int:
    """Parse a counter cell, treating blanks as zero."""

    text = _clean(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError as error:
        raise ValueError(
            f"Expected an integer count, got {value!r}."
        ) from error


def _parse_optional_int(value: str | None) -> int | None:
    """Parse an optional integer cell, mapping blanks to ``None``."""

    text = _clean(value)
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError as error:
        raise ValueError(
            f"Expected an integer or blank, got {value!r}."
        ) from error


def _parse_bool(value: str | None) -> bool | None:
    """Parse a truthy/falsy cell, mapping blanks to ``None``."""

    text = _clean(value).lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    if not text:
        return None
    raise ValueError(f"Expected True/False or blank, got {value!r}.")


def _normalise_puzzle_id(value: str) -> str:
    """Canonicalise a numeric puzzle ID for joining across files."""

    text = value.strip()
    try:
        return str(int(text))
    except ValueError:
        return text


def load_config(path: Path) -> dict[str, Any]:
    """Load ``experiment_config.json`` and require a JSON object."""

    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)
    if not isinstance(config, dict):
        raise TypeError(f"Expected a JSON object in {path}.")
    return config


def load_manifest(path: Path) -> list[ManifestPuzzle]:
    """Load the selected-puzzle manifest."""

    puzzles: list[ManifestPuzzle] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        for row_number, row in enumerate(csv.DictReader(file), start=2):
            try:
                puzzles.append(
                    ManifestPuzzle(
                        puzzle_id=_normalise_puzzle_id(
                            _clean(row.get("puzzle_id"))
                        ),
                        answer=_clean(row.get("answer")),
                        human_mean_score=_parse_float(
                            row.get("human_mean_score")
                        ),
                        human_label=_clean(
                            row.get("human_label")
                        ).lower(),
                    )
                )
            except ValueError as error:
                raise ValueError(f"{path}:{row_number}: {error}") from error
    return puzzles


def load_run_attempts(path: Path) -> list[RunAttempt]:
    """Load one ``RunAttempt`` per row of ``run_summary.csv``."""

    attempts: list[RunAttempt] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        for row_number, row in enumerate(csv.DictReader(file), start=2):
            try:
                attempts.append(
                    RunAttempt(
                        run_id=_clean(row.get("run_id")),
                        puzzle_id=_normalise_puzzle_id(
                            _clean(row.get("puzzle_id"))
                        ),
                        status=_clean(row.get("status")).lower(),
                        won=_parse_bool(row.get("won")),
                        penalized_score=_parse_float(
                            row.get("penalized_score")
                        ),
                        total_tokens=_parse_optional_int(
                            row.get("total_tokens")
                        ),
                        agent_calls=_parse_count(row.get("agent_calls")),
                        rejected_responses=_parse_count(
                            row.get("rejected_responses")
                        ),
                        backend_errors=_parse_count(
                            row.get("backend_errors")
                        ),
                        turns=_parse_count(row.get("turns")),
                        gm_stop_turns=_parse_count(
                            row.get("gm_stop_turns")
                        ),
                        max_rounds_turns=_parse_count(
                            row.get("max_rounds_turns")
                        ),
                    )
                )
            except ValueError as error:
                raise ValueError(f"{path}:{row_number}: {error}") from error
    return attempts


def load_rounds_at_termination(
    runs_dir: Path,
    panel_ids: set[str],
) -> dict[str, Any] | None:
    """Count the debate round at which each completed turn ended.

    Uses the full run checkpoints when present; returns ``None`` when
    the ``runs`` directory is unavailable.
    """

    if not runs_dir.is_dir():
        return None

    rounds: dict[str, dict[str, int]] = {}
    turns = 0
    runs_scanned = 0

    for path in sorted(runs_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as file:
                run = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        if run.get("status") != "completed":
            continue

        metadata = run.get("metadata") or {}
        puzzle_id = _normalise_puzzle_id(
            str(metadata.get("puzzle_id", ""))
        )

        if puzzle_id not in panel_ids:
            continue

        runs_scanned += 1

        for turn in run.get("turns") or []:
            termination = str(turn.get("termination", ""))
            round_number = turn.get("debate_rounds")

            if termination not in {"gm_stop", "max_rounds"}:
                continue

            if not isinstance(round_number, int) or round_number < 1:
                continue

            turns += 1
            bucket = rounds.setdefault(str(round_number), {})
            bucket[termination] = bucket.get(termination, 0) + 1

    return {
        "runs_scanned": runs_scanned,
        "turns": turns,
        "by_round": rounds,
    }


def _require_file(path: Path) -> Path:
    """Return ``path`` or fail with a readable message."""

    if not path.is_file():
        raise FileNotFoundError(f"Missing required input file: {path}")
    return path


def planned_repetitions(config: dict[str, Any]) -> int:
    """Read the planned repetition count, falling back to 5."""

    settings = config.get("settings")
    if isinstance(settings, dict):
        raw = settings.get("repetitions")
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            value = int(raw)
            if value >= 1:
                return value
    return DEFAULT_REPETITIONS


def primary_threshold(config: dict[str, Any]) -> float:
    """Read the pre-registered easy/hard threshold, defaulting to 4.0."""

    raw = config.get("primary_threshold")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    return DEFAULT_PRIMARY_THRESHOLD


def sensitivity_thresholds(config: dict[str, Any]) -> list[float]:
    """Read the robustness-check thresholds, sorted and de-duplicated."""

    raw = config.get("thresholds")
    values: list[float] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                values.append(float(item))
    if not values:
        values = list(DEFAULT_THRESHOLDS)
    return sorted(set(values))


# ---------------------------------------------------------------------------
# Per-puzzle aggregation
# ---------------------------------------------------------------------------


def _group_attempts(
    attempts: Sequence[RunAttempt],
) -> dict[str, list[RunAttempt]]:
    """Group run attempts by puzzle ID."""

    grouped: dict[str, list[RunAttempt]] = {}
    for attempt in attempts:
        grouped.setdefault(attempt.puzzle_id, []).append(attempt)
    return grouped


def build_puzzle_stats(
    manifest: Sequence[ManifestPuzzle],
    attempts_by_puzzle: dict[str, list[RunAttempt]],
    repetitions: int,
    threshold: float,
) -> list[PuzzleStats]:
    """Aggregate run attempts into one record per manifest puzzle."""

    stats: list[PuzzleStats] = []

    for puzzle in manifest:
        attempts = attempts_by_puzzle.get(puzzle.puzzle_id, [])
        completed = [a for a in attempts if a.status == "completed"]

        scores: list[float] = []
        for attempt in completed:
            if attempt.penalized_score is not None:
                scores.append(attempt.penalized_score)

        system_mean = _mean(scores)
        system_sd = statistics.stdev(scores) if len(scores) >= 2 else None

        if system_mean is None:
            system_label = ""
        elif system_mean < threshold:
            system_label = "easy"
        else:
            system_label = "hard"

        label_agreement: bool | None = None
        if system_label and puzzle.human_label:
            label_agreement = system_label == puzzle.human_label

        completed_runs = len(completed)
        wins = sum(1 for a in completed if a.won is True)
        turns = sum(a.turns for a in completed)
        gm_stop_turns = sum(a.gm_stop_turns for a in completed)
        max_rounds_turns = sum(a.max_rounds_turns for a in completed)

        stats.append(
            PuzzleStats(
                puzzle_id=puzzle.puzzle_id,
                answer=puzzle.answer,
                human_mean_score=puzzle.human_mean_score,
                human_label=puzzle.human_label,
                planned_repetitions=repetitions,
                completed_runs=completed_runs,
                wins=wins,
                losses=sum(1 for a in completed if a.won is False),
                infra_failures=sum(
                    1 for a in attempts if a.status in INFRA_STATUSES
                ),
                win_rate=(wins / completed_runs) if completed_runs else None,
                system_mean=system_mean,
                system_sd=system_sd,
                system_label=system_label,
                label_agreement=label_agreement,
                turns=turns,
                gm_stop_turns=gm_stop_turns,
                max_rounds_turns=max_rounds_turns,
            )
        )

    stats.sort(key=lambda item: int(item.puzzle_id))
    return stats


def alignment_pairs(panel: Sequence[PuzzleStats]) -> list[AlignmentPair]:
    """Return panel puzzles that have both a system and a human mean."""

    pairs: list[AlignmentPair] = []
    for puzzle in panel:
        if puzzle.human_mean_score is None or puzzle.system_mean is None:
            continue
        pairs.append(
            AlignmentPair(
                puzzle_id=puzzle.puzzle_id,
                human=puzzle.human_mean_score,
                system=puzzle.system_mean,
            )
        )
    return pairs


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------


def _mean(values: Sequence[float]) -> float | None:
    """Arithmetic mean, or ``None`` for an empty sample."""

    return statistics.fmean(values) if values else None


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Pearson correlation, or ``None`` when it is undefined."""

    if len(xs) < 2 or len(xs) != len(ys):
        return None

    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    covariance = sum(
        (x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)
    )
    variance_x = sum((x - mean_x) ** 2 for x in xs)
    variance_y = sum((y - mean_y) ** 2 for y in ys)

    if variance_x <= 0.0 or variance_y <= 0.0:
        return None

    return covariance / math.sqrt(variance_x * variance_y)


def _average_ranks(values: Sequence[float]) -> list[float]:
    """One-based ranks where tied values share their average rank."""

    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)

    start = 0
    while start < len(order):
        end = start
        while (
            end + 1 < len(order)
            and values[order[end + 1]] == values[order[start]]
        ):
            end += 1

        average_rank = (start + end) / 2 + 1
        for position in range(start, end + 1):
            ranks[order[position]] = average_rank
        start = end + 1

    return ranks


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Spearman rank correlation using average ranks for ties."""

    if len(xs) < 2 or len(xs) != len(ys):
        return None
    return _pearson(_average_ranks(xs), _average_ranks(ys))


def _percentile(
    sorted_values: Sequence[float],
    fraction: float,
) -> float | None:
    """Linear-interpolation percentile of already-sorted values."""

    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (len(sorted_values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]

    weight = position - lower
    return (
        sorted_values[lower] * (1.0 - weight)
        + sorted_values[upper] * weight
    )


def classification_metrics(
    pairs: Sequence[AlignmentPair],
    threshold: float,
) -> dict[str, Any]:
    """Easy/hard agreement statistics for one threshold.

    The threshold is applied independently to the human and system means,
    matching the study's operational difficulty labels (``< threshold`` is
    easy).  Per-class recall is undefined for a class absent from the
    human labels; balanced accuracy averages whichever recalls exist,
    which mirrors ``sklearn.metrics.balanced_accuracy_score``.
    """

    human_easy_system_easy = 0
    human_easy_system_hard = 0
    human_hard_system_easy = 0
    human_hard_system_hard = 0

    for pair in pairs:
        human_easy = pair.human < threshold
        system_easy = pair.system < threshold
        if human_easy and system_easy:
            human_easy_system_easy += 1
        elif human_easy:
            human_easy_system_hard += 1
        elif system_easy:
            human_hard_system_easy += 1
        else:
            human_hard_system_hard += 1

    total = len(pairs)
    easy_total = human_easy_system_easy + human_easy_system_hard
    hard_total = human_hard_system_easy + human_hard_system_hard

    recall_easy = (
        human_easy_system_easy / easy_total if easy_total else None
    )
    recall_hard = (
        human_hard_system_hard / hard_total if hard_total else None
    )
    defined_recalls = [
        recall for recall in (recall_easy, recall_hard) if recall is not None
    ]

    accuracy = (
        (human_easy_system_easy + human_hard_system_hard) / total
        if total
        else None
    )
    majority_baseline = (
        max(easy_total, hard_total) / total if total else None
    )

    return {
        "threshold": threshold,
        "puzzles": total,
        "human_easy_system_easy": human_easy_system_easy,
        "human_easy_system_hard": human_easy_system_hard,
        "human_hard_system_easy": human_hard_system_easy,
        "human_hard_system_hard": human_hard_system_hard,
        "recall_easy": recall_easy,
        "recall_hard": recall_hard,
        "balanced_accuracy": (
            statistics.fmean(defined_recalls) if defined_recalls else None
        ),
        "accuracy": accuracy,
        "majority_baseline": majority_baseline,
    }


# ---------------------------------------------------------------------------
# Research-question summaries
# ---------------------------------------------------------------------------


def summarise_rq1(
    panel: Sequence[PuzzleStats],
    attempts: Sequence[RunAttempt],
) -> dict[str, Any]:
    """Outcome-consistency metrics for one puzzle cohort."""

    completed_runs = sum(p.completed_runs for p in panel)
    wins = sum(p.wins for p in panel)
    losses = sum(p.losses for p in panel)
    infra_failures = sum(p.infra_failures for p in panel)
    total_attempts = len(attempts)

    standard_deviations: list[float] = []
    for puzzle in panel:
        if puzzle.system_sd is not None:
            standard_deviations.append(puzzle.system_sd)

    agent_calls = sum(a.agent_calls for a in attempts)
    rejected = sum(a.rejected_responses for a in attempts)
    backend_errors = sum(a.backend_errors for a in attempts)

    return {
        "puzzles_with_sd": len(standard_deviations),
        "sd_distribution": {
            "mean": _mean(standard_deviations),
            "median": (
                statistics.median(standard_deviations)
                if standard_deviations
                else None
            ),
            "min": min(standard_deviations) if standard_deviations else None,
            "max": max(standard_deviations) if standard_deviations else None,
        },
        "completed_runs": completed_runs,
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / completed_runs) if completed_runs else None,
        "attempts": total_attempts,
        "infra_failures": infra_failures,
        "infra_failure_attempt_rate": (
            infra_failures / total_attempts if total_attempts else None
        ),
        "completed_runs_missing_total_tokens": sum(
            1
            for a in attempts
            if a.status == "completed" and a.total_tokens is None
        ),
        "total_agent_calls": agent_calls,
        "rejected_responses": rejected,
        "rejected_responses_per_agent_call": (
            rejected / agent_calls if agent_calls else None
        ),
        "backend_errors": backend_errors,
        "backend_errors_per_agent_call": (
            backend_errors / agent_calls if agent_calls else None
        ),
    }


def _point_metrics(
    pairs: Sequence[AlignmentPair],
    threshold: float,
) -> dict[str, float | None]:
    """Point estimates resampled by the bootstrap."""

    humans = [pair.human for pair in pairs]
    systems = [pair.system for pair in pairs]

    return {
        "mae": _mean([abs(h - s) for h, s in zip(humans, systems)]),
        "signed_error": _mean([s - h for h, s in zip(humans, systems)]),
        "spearman": _spearman(humans, systems),
        "balanced_accuracy": classification_metrics(pairs, threshold)[
            "balanced_accuracy"
        ],
    }


def summarise_rq2(
    panel: Sequence[PuzzleStats],
    threshold: float,
) -> dict[str, Any]:
    """Human-alignment metrics for one puzzle cohort.

    Each puzzle contributes one observation: its mean penalized score
    paired with its human mean.  Repetitions are never treated as
    independent puzzle observations.
    """

    pairs = alignment_pairs(panel)
    point = _point_metrics(pairs, threshold)

    return {
        "panel_puzzles": len(panel),
        "aligned_puzzles": len(pairs),
        "mae": point["mae"],
        "signed_error": point["signed_error"],
        "spearman": point["spearman"],
        "pearson": _pearson(
            [pair.human for pair in pairs],
            [pair.system for pair in pairs],
        ),
        "classification": classification_metrics(pairs, threshold),
    }


def bootstrap_cis(
    pairs: Sequence[AlignmentPair],
    threshold: float,
    seed: int,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Puzzle-level bootstrap percentile CIs for the RQ2 metrics.

    Resampling units are puzzles, not runs.  Entries are ``None`` when
    fewer than two aligned puzzles exist or a metric is undefined.
    """

    result: dict[str, Any] = {
        "resamples": resamples,
        "seed": seed,
        "ci_level": 0.95,
        "unit": "puzzle",
    }
    metric_names = ("mae", "signed_error", "spearman", "balanced_accuracy")

    if len(pairs) < 2:
        for name in metric_names:
            result[name] = None
        return result

    point = _point_metrics(pairs, threshold)
    draws: dict[str, list[float]] = {name: [] for name in metric_names}

    rng = random.Random(seed)
    size = len(pairs)
    for _ in range(resamples):
        sample = [pairs[rng.randrange(size)] for _ in range(size)]
        sample_values = _point_metrics(sample, threshold)
        for name in metric_names:
            value = sample_values[name]
            if value is not None:
                draws[name].append(value)

    for name in metric_names:
        if point[name] is None:
            result[name] = None
            continue
        sorted_values = sorted(draws[name])
        result[name] = {
            "point": point[name],
            "ci_low": _percentile(sorted_values, CI_LOW_FRACTION),
            "ci_high": _percentile(sorted_values, CI_HIGH_FRACTION),
            "valid_resamples": len(sorted_values),
        }

    return result


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def _termination_bucket(
    stats: Sequence[PuzzleStats],
) -> dict[str, Any]:
    """Count debate endings per termination type over completed turns."""

    turns = sum(p.turns for p in stats)
    gm_stop_turns = sum(p.gm_stop_turns for p in stats)
    max_rounds_turns = sum(p.max_rounds_turns for p in stats)

    return {
        "puzzles": len(stats),
        "turns": turns,
        "gm_stop_turns": gm_stop_turns,
        "max_rounds_turns": max_rounds_turns,
        "gm_stop_share": (gm_stop_turns / turns) if turns else None,
        "max_rounds_share": (
            max_rounds_turns / turns if turns else None
        ),
    }


def summarise_terminations(
    stats: Sequence[PuzzleStats],
) -> dict[str, Any]:
    """Describe how debates ended, split by difficulty labels.

    Turn-level counts over the completed runs of the given puzzles; a
    descriptive supporting measurement, not a hypothesis test.
    """

    return {
        "unit": "turns: one debate per submitted guess",
        "scope": "completed runs of the analysed puzzles",
        "overall": _termination_bucket(stats),
        "by_human_label": {
            label: _termination_bucket(
                [p for p in stats if p.human_label == label]
            )
            for label in ("easy", "hard")
        },
        "by_system_label": {
            label: _termination_bucket(
                [p for p in stats if p.system_label == label]
            )
            for label in ("easy", "hard")
        },
    }


def termination_rows(
    stats: Sequence[PuzzleStats],
) -> list[dict[str, Any]]:
    """Flatten termination statistics into CSV rows."""

    summary = summarise_terminations(stats)

    rows: list[dict[str, Any]] = [
        {"group": "overall", **summary["overall"]}
    ]

    for label in ("easy", "hard"):
        rows.append(
            {
                "group": f"human_{label}",
                **summary["by_human_label"][label],
            }
        )

    for label in ("easy", "hard"):
        rows.append(
            {
                "group": f"system_{label}",
                **summary["by_system_label"][label],
            }
        )

    return rows


def _panel_block(
    stats: Sequence[PuzzleStats],
    attempts: Sequence[RunAttempt],
    repetitions: int,
) -> dict[str, Any]:
    """Completeness and infrastructure description of the manifest."""

    total_attempts = len(attempts)
    infra_failures = sum(
        1 for a in attempts if a.status in INFRA_STATUSES
    )

    return {
        "planned_puzzles": len(stats),
        "complete_puzzles": sum(
            1 for p in stats if p.completed_runs >= repetitions
        ),
        "incomplete_puzzle_ids": [
            p.puzzle_id for p in stats if p.completed_runs < repetitions
        ],
        "planned_units": len(stats) * repetitions,
        "completed_runs": sum(
            1 for a in attempts if a.status == "completed"
        ),
        "failed_attempts": sum(
            1 for a in attempts if a.status == "failed"
        ),
        "interrupted_attempts": sum(
            1 for a in attempts if a.status == "interrupted"
        ),
        "infra_failure_attempt_rate": (
            infra_failures / total_attempts if total_attempts else None
        ),
    }


def _notes(threshold: float) -> list[str]:
    """Document the study choices embedded in these outputs."""

    return [
        (
            f"The primary easy/hard threshold ({threshold}) was fixed "
            "before analysing system results; 3.8 and 4.2 are sensitivity "
            "checks only."
        ),
        (
            "System difficulty is the mean penalized guess score over a "
            "puzzle's completed runs."
        ),
        (
            "Finished losses are scored 7, matching the human baseline "
            "loss convention; infrastructure failures have no game "
            "score."
        ),
        (
            "The primary panel contains only manifest puzzles with at "
            "least the planned number of completed runs; incomplete "
            "puzzles are reported but excluded from primary metrics."
        ),
        (
            "Human mean scores are approximate: they were reconstructed "
            "from whole-percent rounded guess-distribution bins, with "
            "the unsolved share as the complement of the solved shares."
        ),
        (
            "Debate termination statistics are descriptive supporting "
            "measurements at the frozen max_rounds setting: turn-level "
            "gm_stop versus max_rounds counts over the completed runs "
            "of the primary panel, split by human and system difficulty "
            "labels; the round at which each debate ended is included "
            "when the run checkpoints are available."
        ),
    ]


def _experiment_id(config: dict[str, Any], experiment_dir: Path) -> str:
    """Prefer the configured experiment ID, else the directory name."""

    raw = config.get("experiment_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return experiment_dir.name


def analyse(
    experiment_dir: Path,
    seed: int = DEFAULT_SEED,
) -> AnalysisOutput:
    """Load an experiment directory and compute every analysis output."""

    attempts = load_run_attempts(
        _require_file(experiment_dir / "run_summary.csv")
    )
    manifest = load_manifest(_require_file(experiment_dir / "manifest.csv"))
    config = load_config(
        _require_file(experiment_dir / "experiment_config.json")
    )

    repetitions = planned_repetitions(config)
    threshold = primary_threshold(config)
    thresholds = sensitivity_thresholds(config)

    manifest_ids = {puzzle.puzzle_id for puzzle in manifest}
    selected_attempts = [
        attempt
        for attempt in attempts
        if attempt.puzzle_id in manifest_ids
    ]
    attempts_by_puzzle = _group_attempts(selected_attempts)

    stats = build_puzzle_stats(
        manifest,
        attempts_by_puzzle,
        repetitions,
        threshold,
    )

    panel = [p for p in stats if p.completed_runs >= repetitions]
    panel_ids = {puzzle.puzzle_id for puzzle in panel}
    panel_attempts = [
        attempt
        for attempt in selected_attempts
        if attempt.puzzle_id in panel_ids
    ]

    descriptive = [p for p in stats if p.completed_runs >= 1]
    descriptive_ids = {puzzle.puzzle_id for puzzle in descriptive}
    descriptive_attempts = [
        attempt
        for attempt in selected_attempts
        if attempt.puzzle_id in descriptive_ids
    ]

    termination = summarise_terminations(panel)
    rounds_at_termination = load_rounds_at_termination(
        experiment_dir / "runs", panel_ids
    )
    if rounds_at_termination is not None:
        termination["rounds_at_termination"] = rounds_at_termination

    pairs = alignment_pairs(panel)
    sensitivity = [
        classification_metrics(pairs, value) for value in thresholds
    ]

    metrics: dict[str, Any] = {
        "experiment_id": _experiment_id(config, experiment_dir),
        "generated_at": datetime.now(UTC).isoformat(
            timespec="seconds"
        ),
        "panel": _panel_block(stats, selected_attempts, repetitions),
        "rq1": summarise_rq1(panel, panel_attempts),
        "rq2": summarise_rq2(panel, threshold),
        "termination_stats": termination,
        "sensitivity": sensitivity,
        "bootstrap": bootstrap_cis(pairs, threshold, seed),
        "descriptive_all_puzzles": {
            "puzzles": len(descriptive),
            "rq1": summarise_rq1(descriptive, descriptive_attempts),
            "rq2": summarise_rq2(descriptive, threshold),
        },
        "notes": _notes(threshold),
    }

    return AnalysisOutput(
        metrics=_round_output(metrics),
        puzzle_stats=tuple(stats),
        sensitivity=tuple(_round_output(row) for row in sensitivity),
        termination_rows=tuple(termination_rows(panel)),
    )


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------


def _round_output(value: Any) -> Any:
    """Recursively round floats for stable, readable output files."""

    if isinstance(value, float):
        return round(value, ROUNDING_PLACES)
    if isinstance(value, dict):
        return {key: _round_output(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_round_output(item) for item in value]
    return value


def _csv_cell(value: Any) -> str:
    """Render one CSV cell, using blanks for undefined values."""

    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return str(round(value, ROUNDING_PLACES))
    return str(value)


def write_puzzle_summary(
    path: Path,
    stats: Sequence[PuzzleStats],
) -> None:
    """Write ``puzzle_summary.csv`` with one row per manifest puzzle."""

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(PUZZLE_SUMMARY_COLUMNS)
        for puzzle in stats:
            writer.writerow(
                [
                    _csv_cell(puzzle.puzzle_id),
                    _csv_cell(puzzle.answer),
                    _csv_cell(puzzle.human_mean_score),
                    _csv_cell(puzzle.human_label),
                    _csv_cell(puzzle.planned_repetitions),
                    _csv_cell(puzzle.completed_runs),
                    _csv_cell(puzzle.wins),
                    _csv_cell(puzzle.losses),
                    _csv_cell(puzzle.infra_failures),
                    _csv_cell(puzzle.win_rate),
                    _csv_cell(puzzle.system_mean),
                    _csv_cell(puzzle.system_sd),
                    _csv_cell(puzzle.system_label),
                    _csv_cell(puzzle.label_agreement),
                    _csv_cell(puzzle.turns),
                    _csv_cell(puzzle.gm_stop_turns),
                    _csv_cell(puzzle.max_rounds_turns),
                ]
            )


def write_threshold_sensitivity(
    path: Path,
    rows: Sequence[dict[str, Any]],
) -> None:
    """Write ``threshold_sensitivity.csv`` sorted by threshold."""

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(THRESHOLD_SENSITIVITY_COLUMNS)
        for row in rows:
            writer.writerow(
                [_csv_cell(row.get(column)) for column in THRESHOLD_SENSITIVITY_COLUMNS]
            )


def write_termination_stats(
    path: Path,
    rows: Sequence[dict[str, Any]],
) -> None:
    """Write ``termination_stats.csv`` (descriptive supporting table)."""

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(TERMINATION_STATS_COLUMNS)
        for row in rows:
            writer.writerow(
                [
                    _csv_cell(row.get(column))
                    for column in TERMINATION_STATS_COLUMNS
                ]
            )


def write_metrics(path: Path, metrics: dict[str, Any]) -> None:
    """Write ``metrics.json``."""

    with path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2, ensure_ascii=False)
        file.write("\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        prog="python -m multi_agent_testing.experiment.analysis",
        description=(
            "Analyse a finished experiment directory and write "
            "puzzle_summary.csv, threshold_sensitivity.csv, "
            "termination_stats.csv, and metrics.json into it."
        ),
    )
    parser.add_argument(
        "--experiment-dir",
        type=Path,
        required=True,
        help="Directory containing run_summary.csv, manifest.csv, and "
        "experiment_config.json.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Bootstrap seed (default {DEFAULT_SEED}).",
    )
    return parser


def _format_number(value: Any, places: int = 4) -> str:
    """Format a metric for the console, using ``n/a`` when undefined."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "n/a"
    return f"{float(value):.{places}f}"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the analysis CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    experiment_dir: Path = args.experiment_dir

    if not experiment_dir.is_dir():
        parser.error(f"Experiment directory does not exist: {experiment_dir}")

    try:
        output = analyse(experiment_dir, args.seed)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))

    write_puzzle_summary(
        experiment_dir / "puzzle_summary.csv",
        output.puzzle_stats,
    )
    write_threshold_sensitivity(
        experiment_dir / "threshold_sensitivity.csv",
        output.sensitivity,
    )
    write_termination_stats(
        experiment_dir / "termination_stats.csv",
        output.termination_rows,
    )
    write_metrics(experiment_dir / "metrics.json", output.metrics)

    metrics = output.metrics
    panel = metrics["panel"]
    rq1 = metrics["rq1"]
    rq2 = metrics["rq2"]

    print(f"Experiment: {metrics['experiment_id']}")
    print(
        f"Panel: {panel['complete_puzzles']}/{panel['planned_puzzles']} "
        "puzzles complete"
    )
    if panel["incomplete_puzzle_ids"]:
        incomplete = ", ".join(panel["incomplete_puzzle_ids"])
        print(f"Incomplete (excluded from primary panel): {incomplete}")
    print(
        "Overall win rate: "
        f"{_format_number(rq1['win_rate'])} "
        f"({rq1['wins']}/{rq1['completed_runs']} completed runs)"
    )
    print(
        "RQ2: "
        f"MAE={_format_number(rq2['mae'])} "
        f"signed_error={_format_number(rq2['signed_error'])} "
        f"Spearman={_format_number(rq2['spearman'])} "
        f"balanced_accuracy="
        f"{_format_number(rq2['classification']['balanced_accuracy'])}"
    )
    terminations = metrics.get("termination_stats", {}).get(
        "overall", {}
    )
    print(
        "Terminations (turns): "
        f"gm_stop={terminations.get('gm_stop_turns', 'n/a')} "
        f"max_rounds={terminations.get('max_rounds_turns', 'n/a')} "
        f"total={terminations.get('turns', 'n/a')}"
    )
    print(
        "Wrote: puzzle_summary.csv, threshold_sensitivity.csv, "
        "termination_stats.csv, metrics.json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
