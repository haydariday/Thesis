"""Select the final-study puzzle manifest and its smoke manifest.

Final study, phase F2. Standard library only. Run as

    python -m multi_agent_testing.experiment.manifest_final \\
        --clean-csv src/data/processed/wordle_human_clean.csv \\
        --quartiles src/data/processed/quartiles.json \\
        --terciles src/data/processed/terciles.json \\
        --exclude-manifest experiments/manifests/pilot-01.csv \\
        --exclude-manifest experiments/manifests/pilot-02-deep.csv \\
        --exclude-manifest experiments/manifests/pilot-02-wide.csv \\
        --smoke-source experiments/manifests/pilot-02-wide.csv \\
        --output-dir experiments/manifests

It writes three files into the output directory:

* ``final.csv`` - 25 puzzles per quartile (100), seed 20261103.
* ``final-smoke.csv`` - 2 puzzles per quartile (8) from the pilot-02 wide
  manifest, seed 20261104, so smoke games never touch a final puzzle.
* ``final.summary.json`` - input hashes, pool sizes, seeds and selected ids.

Sampling pool
-------------
The pool rule is that of :mod:`manifest_pilot02`: eligible, unique answer and
not in any ``--exclude-manifest``. Every played pilot manifest must be
excluded. The draw is stratified by quartile, which keeps the human range
covered evenly; each row also carries its tercile, the category scheme of the
final study. The clean CSV hash must match the one frozen in both
``quartiles.json`` and ``terciles.json``.

Selection
---------
The final draw is :func:`manifest_pilot02.select_manifests` with one draw:
``random.Random(20261103)`` takes ``rng.sample(pool, 25)`` from D1, D2, D3 and
D4 in that order. The smoke draw groups the ``--smoke-source`` puzzles by
quartile, orders each group by integer puzzle id and takes
``random.Random(20261104).sample(group, 2)`` in the same order. Both outputs
are ordered by integer puzzle id and identical on every re-run.

Manifest rows keep the pilot-02 columns, set ``split`` to ``final`` or
``smoke`` and add ``tercile``.
"""

import argparse
import csv
import json
import random
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import cast

from . import manifest_pilot02 as p2
from .quartiles import QUARTILE_LABELS, RankedPuzzle
from .terciles import assign_terciles

FINAL = p2.ExperimentDraw(name="final", seed=20261103, per_quartile=25)
SMOKE = p2.ExperimentDraw(name="final-smoke", seed=20261104, per_quartile=2)

MANIFEST_COLUMNS: tuple[str, ...] = (*p2.MANIFEST_COLUMNS, "tercile")


def tercile_labels(rows: Iterable[Mapping[str, str]], terciles: Mapping[str, object]) -> dict[str, str]:
    """T1..T3 per eligible puzzle id, checked against the frozen ``terciles.json``."""

    eligible = [row for row in rows if row["eligible"] == "True"]
    labels, spec = assign_terciles(
        [RankedPuzzle(row["puzzle_id"], round(float(row["human_mean_score"]), 6)) for row in eligible]
    )
    frozen_cuts = cast("list[float]", terciles["cut_points"])
    frozen_sizes = cast("list[int]", terciles["sizes"])
    if [round(c, 6) for c in spec.cut_points] != frozen_cuts or list(spec.sizes) != frozen_sizes:
        raise ValueError("Terciles of the clean CSV do not match terciles.json.")
    return labels


def select_smoke(
    source_rows: Sequence[Mapping[str, str]],
    draw: p2.ExperimentDraw = SMOKE,
) -> list[Mapping[str, str]]:
    """Stratified draw from an earlier manifest, ordered by integer puzzle id."""

    rng = random.Random(draw.seed)
    picks: list[Mapping[str, str]] = []
    for label in QUARTILE_LABELS:
        group = sorted((row for row in source_rows if row["quartile"] == label),
                       key=lambda row: int(row["puzzle_id"]))
        if len(group) < draw.per_quartile:
            raise ValueError(
                f"{draw.name}: quartile {label} has {len(group)} puzzles, needs {draw.per_quartile}."
            )
        picks.extend(rng.sample(group, draw.per_quartile))
    return sorted(picks, key=lambda row: int(row["puzzle_id"]))


def manifest_row(
    row: Mapping[str, str],
    draw: p2.ExperimentDraw,
    split: str,
    tercile: str,
) -> dict[str, str]:
    """Pilot-02 manifest columns with ``split`` set and ``tercile`` added."""

    return {**p2.manifest_row(row, draw), "split": split, "tercile": tercile}


def write_manifest(
    path: Path,
    rows: Iterable[Mapping[str, str]],
    draw: p2.ExperimentDraw,
    split: str,
    terciles: Mapping[str, str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(manifest_row(row, draw, split, terciles[row["puzzle_id"]]))


def _check_frozen(clean_hash: str, frozen_json: Path) -> dict:
    frozen = json.loads(frozen_json.read_text(encoding="utf-8"))
    frozen_hash = frozen["source"]["clean_csv_sha256"]
    if clean_hash != frozen_hash:
        raise ValueError(
            f"The clean CSV does not match the one frozen in {frozen_json} "
            f"({clean_hash} != {frozen_hash})."
        )
    return frozen


def _output_entry(path: Path, draw: p2.ExperimentDraw, rows: Sequence[Mapping[str, str]],
                  terciles: Mapping[str, str]) -> dict[str, object]:
    return {
        "path": path.as_posix(),
        "sha256": p2._sha256(path),
        "seed": draw.seed,
        "per_quartile": draw.per_quartile,
        "puzzle_ids": {
            label: [row["puzzle_id"] for row in rows if row["quartile"] == label]
            for label in QUARTILE_LABELS
        },
        "tercile_counts": {
            label: sum(1 for row in rows if terciles[row["puzzle_id"]] == label)
            for label in ("T1", "T2", "T3")
        },
    }


def build_manifests(
    clean_csv: Path,
    quartiles_json: Path,
    terciles_json: Path,
    exclude_manifests: Sequence[Path],
    smoke_source: Path,
    output_dir: Path,
) -> dict[str, object]:
    """Check the frozen inputs, draw the final and smoke sets and write all outputs."""

    clean_hash = p2._sha256(clean_csv)
    _check_frozen(clean_hash, quartiles_json)
    terciles_spec = _check_frozen(clean_hash, terciles_json)

    clean_rows = p2.load_clean_rows(clean_csv)
    tercile_of = tercile_labels(clean_rows, terciles_spec)
    excluded_ids = p2.load_excluded_ids(exclude_manifests)
    smoke_ids = p2.load_excluded_ids([smoke_source])
    if not smoke_ids <= excluded_ids:
        raise ValueError(f"{smoke_source} must also be passed as --exclude-manifest.")

    pool = p2.sampling_pool(clean_rows, excluded_ids)
    final_rows = p2.select_manifests(pool, (FINAL,))[FINAL.name]

    by_id = {row["puzzle_id"]: row for row in clean_rows}
    smoke_picks = select_smoke(p2.load_clean_rows(smoke_source))
    smoke_rows = [by_id[row["puzzle_id"]] for row in smoke_picks]
    for picked, clean in zip(smoke_picks, smoke_rows):
        if picked["quartile"] != clean["quartile"] or picked["answer"] != clean["answer"]:
            raise ValueError(f"Smoke puzzle {picked['puzzle_id']} disagrees with the clean CSV.")

    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / f"{FINAL.name}.csv"
    smoke_path = output_dir / f"{SMOKE.name}.csv"
    write_manifest(final_path, final_rows, FINAL, "final", tercile_of)
    write_manifest(smoke_path, smoke_rows, SMOKE, "smoke", tercile_of)

    summary: dict[str, object] = {
        "phase": "final F2",
        "inputs": {
            "clean_csv": {"path": clean_csv.as_posix(), "sha256": clean_hash},
            "quartiles": {"path": quartiles_json.as_posix(), "sha256": p2._sha256(quartiles_json)},
            "terciles": {"path": terciles_json.as_posix(), "sha256": p2._sha256(terciles_json)},
            "exclude_manifests": [
                {"path": path.as_posix(), "sha256": p2._sha256(path)} for path in exclude_manifests
            ],
            "smoke_source": {"path": smoke_source.as_posix(), "sha256": p2._sha256(smoke_source)},
        },
        "rules": {
            "pool": "eligible, duplicate_answer == False, not in an exclude manifest",
            "order": "each quartile pool sorted by int(puzzle_id); draws in D1..D4 order",
            "smoke": "stratified draw from the smoke source, which is also excluded from the final pool",
        },
        "excluded_ids": sorted(excluded_ids, key=int),
        "pool_sizes": {label: len(pool[label]) for label in QUARTILE_LABELS},
        "pool_total": sum(len(group) for group in pool.values()),
        "outputs": {
            FINAL.name: _output_entry(final_path, FINAL, final_rows, tercile_of),
            SMOKE.name: _output_entry(smoke_path, SMOKE, smoke_rows, tercile_of),
        },
    }
    summary_path = output_dir / "final.summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description="Select the final and smoke manifests by quartile.")
    parser.add_argument("--clean-csv", type=Path, required=True,
                        help="Cleaned 7-bin human data from phase P1.")
    parser.add_argument("--quartiles", type=Path, required=True,
                        help="Frozen quartiles.json from phase P2.")
    parser.add_argument("--terciles", type=Path, required=True,
                        help="Frozen terciles.json from phase F1.")
    parser.add_argument("--exclude-manifest", type=Path, action="append", default=[],
                        help="Earlier manifest whose puzzles are excluded (repeatable).")
    parser.add_argument("--smoke-source", type=Path, required=True,
                        help="Earlier manifest the smoke puzzles are drawn from.")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Directory for the manifests and the summary JSON.")
    args = parser.parse_args()

    summary = build_manifests(args.clean_csv, args.quartiles, args.terciles,
                              args.exclude_manifest, args.smoke_source, args.output_dir)
    print(f"Excluded ids: {len(cast('list[str]', summary['excluded_ids']))}")
    print(f"Pool: {summary['pool_total']} {summary['pool_sizes']}")
    outputs = cast("dict[str, dict]", summary["outputs"])
    for name, output in outputs.items():
        ids = [pid for group in output["puzzle_ids"].values() for pid in group]
        print(f"{name}: {len(ids)} puzzles -> {output['path']}  terciles {output['tercile_counts']}")
        for label, group in output["puzzle_ids"].items():
            print(f"  {label}: {', '.join(group)}")


if __name__ == "__main__":
    main()
