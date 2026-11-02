"""Human difficulty terciles T1 (easiest) to T3 (hardest).

Final study, phase F1. Standard library only. Run as

    python -m multi_agent_testing.experiment.terciles \\
        --clean-csv src/data/processed/wordle_human_clean.csv \\
        --quartiles src/data/processed/quartiles.json \\
        --output src/data/processed/terciles.json

The final study scores difficulty categories in terciles, because the human
shares are whole percents and four categories leave more puzzles with an
uncertain human label (progress report, 2026-10-23). Quartiles stay for
sampling and as a sensitivity check.

The rules are those of :mod:`quartiles` with three groups: eligible puzzles,
duplicates included, are rank-split by ``(human_mean_score, int(puzzle_id))``
into contiguous groups whose sizes differ by at most one. A system score is
mapped by value with ``c_k = min(human_mean_score in T(k+1))``::

    score <  c_1            -> T1
    c_1 <= score <  c_2     -> T2
    c_2 <= score            -> T3

or by rank with :func:`rank_split`.

``terciles.json`` is built from the cleaned CSV of phase P1, whose hash must
match the one frozen in ``quartiles.json``. The CSV itself is not changed, so
the pilot-02 inputs keep their hashes.
"""

import argparse
import csv
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from .human_data import BIN_COLUMNS
from . import quartiles

TERCILE_LABELS: tuple[str, ...] = ("T1", "T2", "T3")


def assign_terciles(
    puzzles: Sequence[quartiles.RankedPuzzle],
) -> tuple[dict[str, str], quartiles.QuartileSpec]:
    """Rank-split ``puzzles`` into T1..T3. Requires at least three puzzles."""

    return quartiles.assign_quartiles(puzzles, TERCILE_LABELS)


def rank_split(values: Sequence[float], tie_keys: Sequence[int]) -> list[str]:
    """T1..T3 for each value by its rank within ``values``."""

    return quartiles.rank_split(values, tie_keys, TERCILE_LABELS)


def map_score(score: float, cut_points: Sequence[float]) -> str:
    """Map a mean guess score to T1..T3 with the value rule above."""

    return quartiles.map_score(score, cut_points, TERCILE_LABELS)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def eligible_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return [row for row in csv.DictReader(file) if row["eligible"] == "True"]


def build_terciles_json(
    rows: Sequence[Mapping[str, str]],
    clean_csv: Path,
    quartiles_json: Path,
) -> dict[str, object]:
    """Frozen tercile definition plus per-tercile human descriptives."""

    tercile_of, spec = assign_terciles(
        [quartiles.RankedPuzzle(row["puzzle_id"], round(float(row["human_mean_score"]), 6))
         for row in rows]
    )
    payload = spec.to_json()
    payload["phase"] = "final F1"
    payload["source"] = {
        "clean_csv": clean_csv.as_posix(),
        "clean_csv_sha256": _sha256(clean_csv),
        "quartiles_json": quartiles_json.as_posix(),
        "quartiles_json_sha256": _sha256(quartiles_json),
    }
    descriptives: dict[str, object] = {}
    for label in TERCILE_LABELS:
        group = [row for row in rows if tercile_of[row["puzzle_id"]] == label]
        descriptives[label] = {
            "n": len(group),
            "mean_human_score": round(
                sum(float(row["human_mean_score"]) for row in group) / len(group), 6
            ),
            "mean_bins": {
                column: round(sum(float(row[column]) for row in group) / len(group), 6)
                for column in BIN_COLUMNS
            },
            "share_fail_ge_5pct": round(
                sum(1 for row in group if float(row["human_loss_pct"]) >= 5) / len(group), 6
            ),
            "quartile_counts": {
                q: sum(1 for row in group if row["quartile"] == q) for q in quartiles.QUARTILE_LABELS
            },
        }
    payload["descriptives"] = descriptives
    return payload


def build_terciles(clean_csv: Path, quartiles_json: Path, output: Path) -> dict[str, object]:
    """Check the frozen CSV, split it into terciles and write ``output``."""

    frozen = json.loads(quartiles_json.read_text(encoding="utf-8"))
    clean_hash = _sha256(clean_csv)
    frozen_hash = frozen["source"]["clean_csv_sha256"]
    if clean_hash != frozen_hash:
        raise ValueError(
            f"{clean_csv} does not match the CSV frozen in {quartiles_json} "
            f"({clean_hash} != {frozen_hash})."
        )

    payload = build_terciles_json(eligible_rows(clean_csv), clean_csv, quartiles_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description="Freeze the T1..T3 human difficulty terciles.")
    parser.add_argument("--clean-csv", type=Path, required=True,
                        help="Cleaned 7-bin human data from phase P1.")
    parser.add_argument("--quartiles", type=Path, required=True,
                        help="Frozen quartiles.json; its CSV hash must match --clean-csv.")
    parser.add_argument("--output", type=Path, required=True,
                        help="Path of the terciles JSON to write.")
    args = parser.parse_args()

    payload = build_terciles(args.clean_csv, args.quartiles, args.output)
    print(f"Tercile sizes: {payload['sizes']}  cut-points: {payload['cut_points']}  "
          f"boundary ties: {payload['boundary_ties']}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
