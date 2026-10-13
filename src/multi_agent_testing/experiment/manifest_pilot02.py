"""Select the pilot-02 puzzle manifests, stratified by human difficulty quartile.

Pilot-02, phase P3. Standard library only. Run as

    python -m multi_agent_testing.experiment.manifest_pilot02 \\
        --clean-csv src/data/processed/wordle_human_clean.csv \\
        --quartiles src/data/processed/quartiles.json \\
        --exclude-manifest experiments/manifests/pilot-01.csv \\
        --output-dir experiments/manifests

It writes three files into the output directory:

* ``pilot-02-deep.csv`` - Exp A, 3 puzzles per quartile (12), seed 20261013.
* ``pilot-02-wide.csv`` - Exp B, 12 puzzles per quartile (48), seed 20261014.
* ``pilot-02.summary.json`` - input hashes, pool sizes, seeds and selected ids.

Sampling pool
-------------
A row of the cleaned CSV (phase P1) can be sampled when it is eligible, its
answer is unique among eligible rows (``duplicate_answer == False``) and its
puzzle id is not in any ``--exclude-manifest`` (the 20 pilot-01 puzzles). The
quartile labels come from the cleaned CSV unchanged. The CSV hash must match
the one frozen in ``quartiles.json``, so the manifests always use the frozen
D1..D4 definition.

Selection
---------
Each quartile's pool is ordered by ascending integer puzzle id. Exp A draws
first: one ``random.Random(20261013)`` instance takes ``rng.sample(pool, 3)``
from D1, D2, D3 and D4 in that order. Exp A's picks then leave the pool, and
Exp B repeats the draw with ``random.Random(20261014)`` and 12 per quartile.
The two sets are disjoint by construction and the output is identical on
every re-run.

Manifest rows keep the pilot-01 columns, so the runner and the pilot-01
analysis can read them, and add ``quartile``, ``p1 .. p7`` and ``experiment``.
"""

import argparse
import csv
import hashlib
import json
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .human_data import BIN_COLUMNS
from .quartiles import QUARTILE_LABELS

EASY_HARD_THRESHOLD = 4.0


@dataclass(frozen=True)
class ExperimentDraw:
    """One stratified draw: name, seed and puzzles per quartile."""

    name: str
    seed: int
    per_quartile: int


DEEP = ExperimentDraw(name="pilot-02-deep", seed=20261013, per_quartile=3)
WIDE = ExperimentDraw(name="pilot-02-wide", seed=20261014, per_quartile=12)
DRAWS: tuple[ExperimentDraw, ...] = (DEEP, WIDE)

MANIFEST_COLUMNS: tuple[str, ...] = (
    "puzzle_id",
    "date",
    "answer",
    "human_mean_score",
    "human_mean_low",
    "human_mean_high",
    "human_loss_pct",
    "human_label",
    "human_mode",
    "human_sample_size_if_known",
    "split",
    "eligibility_notes",
    "selection_seed",
    "quartile",
    *BIN_COLUMNS,
    "experiment",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_clean_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def load_excluded_ids(paths: Iterable[Path]) -> set[str]:
    """Puzzle ids listed in earlier manifests."""

    excluded: set[str] = set()
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as file:
            excluded.update(row["puzzle_id"] for row in csv.DictReader(file))
    return excluded


def sampling_pool(
    rows: Iterable[Mapping[str, str]],
    excluded_ids: set[str],
) -> dict[str, list[Mapping[str, str]]]:
    """Group sampleable rows by quartile, each ordered by integer puzzle id."""

    pool: dict[str, list[Mapping[str, str]]] = {label: [] for label in QUARTILE_LABELS}
    for row in rows:
        if row["eligible"] != "True" or row["duplicate_answer"] != "False":
            continue
        if row["puzzle_id"] in excluded_ids:
            continue
        pool[row["quartile"]].append(row)
    for group in pool.values():
        group.sort(key=lambda row: int(row["puzzle_id"]))
    return pool


def select_manifests(
    pool: Mapping[str, Sequence[Mapping[str, str]]],
    draws: Sequence[ExperimentDraw] = DRAWS,
) -> dict[str, list[Mapping[str, str]]]:
    """Draw each experiment in turn; later draws never reuse earlier picks.

    Returns ``{draw.name: rows}`` with rows ordered by integer puzzle id.
    """

    taken: set[str] = set()
    selected: dict[str, list[Mapping[str, str]]] = {}
    for draw in draws:
        rng = random.Random(draw.seed)
        picks: list[Mapping[str, str]] = []
        for label in QUARTILE_LABELS:
            remaining = [row for row in pool[label] if row["puzzle_id"] not in taken]
            if len(remaining) < draw.per_quartile:
                raise ValueError(
                    f"{draw.name}: quartile {label} has {len(remaining)} puzzles left, "
                    f"needs {draw.per_quartile}."
                )
            picks.extend(rng.sample(remaining, draw.per_quartile))
        taken.update(row["puzzle_id"] for row in picks)
        selected[draw.name] = sorted(picks, key=lambda row: int(row["puzzle_id"]))
    return selected


def manifest_row(row: Mapping[str, str], draw: ExperimentDraw) -> dict[str, str]:
    """Pilot-01 manifest columns plus quartile, 7 bins and experiment name."""

    mean = float(row["human_mean_score"])
    return {
        "puzzle_id": row["puzzle_id"],
        "date": row["date"],
        "answer": row["answer"],
        "human_mean_score": row["human_mean_score"],
        "human_mean_low": row["human_mean_low"],
        "human_mean_high": row["human_mean_high"],
        "human_loss_pct": row["human_loss_pct"],
        "human_label": "easy" if mean < EASY_HARD_THRESHOLD else "hard",
        "human_mode": "standard",
        "human_sample_size_if_known": row["sample"],
        "split": "pilot",
        "eligibility_notes": row["eligibility_notes"],
        "selection_seed": str(draw.seed),
        "quartile": row["quartile"],
        **{column: row[column] for column in BIN_COLUMNS},
        "experiment": draw.name,
    }


def write_manifest(path: Path, rows: Iterable[Mapping[str, str]], draw: ExperimentDraw) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(manifest_row(row, draw))


def build_manifests(
    clean_csv: Path,
    quartiles_json: Path,
    exclude_manifests: Sequence[Path],
    output_dir: Path,
) -> dict[str, object]:
    """Check the frozen inputs, draw both experiments and write all outputs."""

    quartiles = json.loads(quartiles_json.read_text(encoding="utf-8"))
    clean_hash = _sha256(clean_csv)
    frozen_hash = quartiles["source"]["clean_csv_sha256"]
    if clean_hash != frozen_hash:
        raise ValueError(
            f"{clean_csv} does not match the CSV frozen in {quartiles_json} "
            f"({clean_hash} != {frozen_hash})."
        )

    excluded_ids = load_excluded_ids(exclude_manifests)
    pool = sampling_pool(load_clean_rows(clean_csv), excluded_ids)
    selected = select_manifests(pool)

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, object] = {}
    for draw in DRAWS:
        path = output_dir / f"{draw.name}.csv"
        write_manifest(path, selected[draw.name], draw)
        outputs[draw.name] = {
            "path": path.as_posix(),
            "sha256": _sha256(path),
            "seed": draw.seed,
            "per_quartile": draw.per_quartile,
            "puzzle_ids": {
                label: [row["puzzle_id"] for row in selected[draw.name] if row["quartile"] == label]
                for label in QUARTILE_LABELS
            },
        }

    summary: dict[str, object] = {
        "phase": "pilot-02 P3",
        "inputs": {
            "clean_csv": {"path": clean_csv.as_posix(), "sha256": clean_hash},
            "quartiles": {"path": quartiles_json.as_posix(), "sha256": _sha256(quartiles_json)},
            "exclude_manifests": [
                {"path": path.as_posix(), "sha256": _sha256(path)} for path in exclude_manifests
            ],
        },
        "rules": {
            "pool": "eligible, duplicate_answer == False, not in an exclude manifest",
            "order": "each quartile pool sorted by int(puzzle_id); draws in D1..D4 order",
            "draw_order": [draw.name for draw in DRAWS],
            "disjoint": "later draws exclude earlier picks",
        },
        "excluded_ids": sorted(excluded_ids, key=int),
        "pool_sizes": {label: len(pool[label]) for label in QUARTILE_LABELS},
        "pool_total": sum(len(group) for group in pool.values()),
        "outputs": outputs,
    }
    summary_path = output_dir / "pilot-02.summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(
        description="Select the pilot-02 deep and wide manifests by quartile.",
    )
    parser.add_argument("--clean-csv", type=Path, required=True,
                        help="Cleaned 7-bin human data from phase P1.")
    parser.add_argument("--quartiles", type=Path, required=True,
                        help="Frozen quartiles.json from phase P2.")
    parser.add_argument("--exclude-manifest", type=Path, action="append", default=[],
                        help="Earlier manifest whose puzzles are excluded (repeatable).")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Directory for the manifests and the summary JSON.")
    args = parser.parse_args()

    summary = build_manifests(args.clean_csv, args.quartiles, args.exclude_manifest, args.output_dir)
    print(f"Excluded ids: {len(cast('list[str]', summary['excluded_ids']))}")
    print(f"Pool: {summary['pool_total']} {summary['pool_sizes']}")
    outputs = cast("dict[str, dict]", summary["outputs"])
    for name, output in outputs.items():
        ids = [pid for group in output["puzzle_ids"].values() for pid in group]
        print(f"{name}: {len(ids)} puzzles -> {output['path']}")
        for label, group in output["puzzle_ids"].items():
            print(f"  {label}: {', '.join(group)}")


if __name__ == "__main__":
    main()
