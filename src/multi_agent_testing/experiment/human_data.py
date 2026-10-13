"""Clean the raw Worlde dataset into per-puzzle 7-bin human distributions.

Pilot-02, phase P1. The module is standard library only and is meant to be run as

    python -m multi_agent_testing.experiment.human_data \\
        --dataset src/data/raw/worldepuzzles.json \\
        --guess-list src/data/raw/allowed_guesses.txt \\
        --output src/data/processed/wordle_human_clean.csv

It writes two files:

* ``<output>.csv`` - one row per dataset record (eligible or not), ordered by
  ascending puzzle id.
* ``<output>.summary.json`` - input hashes, counts and the eligibility rules
  used, so later phases can verify they read the expected file.

7-bin distribution
------------------
``individual`` holds the whole-percent shares of human games solved in 1..6
guesses. No published row sums to exactly 100; the remainder is the share of
players who failed, which becomes bin 7:

    p_k = individual[k] / 100          for k = 1..6
    p_7 = (100 - sum(individual)) / 100

so ``p_1 + ... + p_7 == 1`` by construction. The bins are written for every
record whose distribution is structurally valid with ``0 <= S <= 100``, even
when the record is otherwise ineligible, so excluded rows can still be
inspected. ``human_mean_score`` and its rounding bounds are only written for
eligible rows and come straight from
:func:`manifest.reconstruct_human_baseline`, so pilot-01 and pilot-02 share
one definition of the human baseline.

Eligibility
-----------
Eligibility is :func:`manifest.audit_record`, unchanged. High-failure rows such
as 454 PARER are genuine hard puzzles and stay eligible.

Duplicate answers
-----------------
Some answers occur more than once. Every eligible row carries
``answer_occurrence`` (1 for the earliest puzzle id with that answer, 2 for the
next, ...) and ``duplicate_answer`` (true when the answer occurs more than
once among eligible rows). Both copies stay in the file; the pilot-02 sampler
(phase P3) only draws rows with ``duplicate_answer == False``.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .manifest import (
    MAX_SOLVED_SHARE,
    MIN_SOLVED_SHARE,
    QUARANTINED_PUZZLE_IDS,
    PuzzleAudit,
    _distribution_share,
    _puzzle_sort_key,
    audit_record,
    load_dataset,
    load_vocabulary,
)

BIN_COUNT = 7
FAIL_BIN = 7
BIN_COLUMNS: tuple[str, ...] = tuple(f"p{k}" for k in range(1, BIN_COUNT + 1))

CLEAN_COLUMNS: tuple[str, ...] = (
    "puzzle_id",
    "date",
    "answer",
    "eligible",
    "eligibility_notes",
    "sample",
    "solved_share",
    *BIN_COLUMNS,
    "human_mean_score",
    "human_mean_low",
    "human_mean_high",
    "human_loss_pct",
    "human_mode_bin",
    "answer_occurrence",
    "duplicate_answer",
)


@dataclass(frozen=True)
class CleanRow:
    """One cleaned puzzle: the manifest audit plus its 7-bin distribution."""

    audit: PuzzleAudit
    bins: tuple[float, ...] | None
    answer_occurrence: int | None
    duplicate_answer: bool | None

    @property
    def mode_bin(self) -> int | None:
        """Most common outcome bin (lowest bin on ties)."""

        if self.bins is None:
            return None
        best = max(self.bins)
        return self.bins.index(best) + 1


def seven_bin_distribution(individual: list[int]) -> tuple[float, ...]:
    """Convert six whole-percent solve shares into seven probabilities.

    Raises ``ValueError`` when the shares are negative or sum above 100,
    because the fail share would then be negative.
    """

    if len(individual) != 6:
        raise ValueError("Expected six solve shares (1..6 guesses).")
    if any(share < 0 for share in individual):
        raise ValueError("Solve shares must be non-negative.")

    solved = sum(individual)
    if solved > 100:
        raise ValueError(f"Solve shares sum to {solved}, above 100.")

    return tuple(share / 100 for share in individual) + ((100 - solved) / 100,)


def distribution_mean(bins: tuple[float, ...]) -> float:
    """Expected guess score of a 7-bin distribution (fail scored as 7)."""

    return sum(k * p for k, p in enumerate(bins, start=1))


def _row_bins(record: dict[str, object]) -> tuple[float, ...] | None:
    individual, solved = _distribution_share(record)
    if individual is None or solved is None or not 0 <= solved <= 100:
        return None
    return seven_bin_distribution(individual)


def clean_records(
    dataset: dict[str, dict[str, object]],
    vocabulary: set[str],
) -> list[CleanRow]:
    """Audit every record and attach its bins and duplicate-answer flags."""

    ordered_ids = sorted(dataset, key=_puzzle_sort_key)
    audits = {pid: audit_record(pid, dataset[pid], vocabulary) for pid in ordered_ids}

    eligible_answers = Counter(a.answer for a in audits.values() if a.eligible)
    seen: Counter[str] = Counter()

    rows: list[CleanRow] = []
    for pid in ordered_ids:
        audit = audits[pid]
        occurrence: int | None = None
        duplicate: bool | None = None
        if audit.eligible:
            seen[audit.answer] += 1
            occurrence = seen[audit.answer]
            duplicate = eligible_answers[audit.answer] > 1
        rows.append(
            CleanRow(
                audit=audit,
                bins=_row_bins(dataset[pid]),
                answer_occurrence=occurrence,
                duplicate_answer=duplicate,
            )
        )
    return rows


def _fmt(value: float | None, digits: int) -> float | str:
    return "" if value is None else round(value, digits)


def _fmt_optional(value: object) -> object:
    return "" if value is None else value


def write_clean_csv(path: Path, rows: list[CleanRow]) -> None:
    """Write the cleaned rows, one per dataset record."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CLEAN_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            audit = row.audit
            out: dict[str, object] = {
                "puzzle_id": audit.puzzle_id,
                "date": audit.date,
                "answer": audit.answer,
                "eligible": audit.eligible,
                "eligibility_notes": audit.notes,
                "sample": _fmt_optional(audit.sample),
                "solved_share": _fmt_optional(audit.solved_share),
                "human_mean_score": _fmt(audit.human_mean_score, 6),
                "human_mean_low": _fmt(audit.human_mean_low, 6),
                "human_mean_high": _fmt(audit.human_mean_high, 6),
                "human_loss_pct": _fmt(audit.human_loss_pct, 2),
                "human_mode_bin": _fmt_optional(row.mode_bin),
                "answer_occurrence": _fmt_optional(row.answer_occurrence),
                "duplicate_answer": _fmt_optional(row.duplicate_answer),
            }
            for column, index in zip(BIN_COLUMNS, range(BIN_COUNT)):
                out[column] = "" if row.bins is None else round(row.bins[index], 2)
            writer.writerow(out)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_summary(
    rows: list[CleanRow],
    dataset_path: Path,
    guess_list_path: Path,
    output_path: Path,
) -> dict[str, object]:
    """Counts, input hashes and rules for the cleaned file."""

    eligible = [r for r in rows if r.audit.eligible]
    excluded = {r.audit.puzzle_id: r.audit.notes for r in rows if not r.audit.eligible}
    duplicates = sorted({r.audit.answer for r in eligible if r.duplicate_answer})
    means = [cast(float, r.audit.human_mean_score) for r in eligible]
    hardest = max(eligible, key=lambda r: cast(float, r.audit.human_mean_score))
    easiest = min(eligible, key=lambda r: cast(float, r.audit.human_mean_score))

    return {
        "phase": "pilot-02 P1",
        "dataset": {"path": dataset_path.as_posix(), "sha256": _sha256(dataset_path)},
        "guess_list": {
            "path": guess_list_path.as_posix(),
            "sha256": _sha256(guess_list_path),
        },
        "output": {"path": output_path.as_posix(), "sha256": _sha256(output_path)},
        "mode": "standard",
        "rules": {
            "fail_bin": FAIL_BIN,
            "bins": "p_k = individual[k]/100 for k=1..6; p_7 = (100 - S)/100",
            "solved_share_range": [MIN_SOLVED_SHARE, MAX_SOLVED_SHARE],
            "quarantined_ids": sorted(QUARANTINED_PUZZLE_IDS, key=int),
        },
        "counts": {
            "rows": len(rows),
            "eligible": len(eligible),
            "excluded": len(excluded),
            "duplicate_answers": len(duplicates),
            "eligible_unique_answer_rows": sum(1 for r in eligible if not r.duplicate_answer),
        },
        "excluded": excluded,
        "duplicate_answers": duplicates,
        "human_mean": {
            "mean": round(sum(means) / len(means), 6),
            "min": {"puzzle_id": easiest.audit.puzzle_id, "answer": easiest.audit.answer,
                    "value": round(cast(float, easiest.audit.human_mean_score), 6)},
            "max": {"puzzle_id": hardest.audit.puzzle_id, "answer": hardest.audit.answer,
                    "value": round(cast(float, hardest.audit.human_mean_score), 6)},
        },
    }


def build_clean_dataset(
    dataset_path: Path,
    guess_list_path: Path,
    output_path: Path,
) -> tuple[list[CleanRow], dict[str, object]]:
    """Clean the dataset and write the CSV plus its summary JSON."""

    rows = clean_records(load_dataset(dataset_path), load_vocabulary(guess_list_path))
    write_clean_csv(output_path, rows)
    summary = build_summary(rows, dataset_path, guess_list_path, output_path)
    summary_path = output_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return rows, summary


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(
        description="Clean the Worlde dataset into 7-bin human distributions.",
    )
    parser.add_argument("--dataset", type=Path, required=True,
                        help="Path to the raw puzzle JSON.")
    parser.add_argument("--guess-list", type=Path, required=True,
                        help="Path to the allowed Wordle guesses, one word per line.")
    parser.add_argument("--output", type=Path, required=True,
                        help="Output CSV path; the summary JSON is written next to it.")
    args = parser.parse_args()

    _, summary = build_clean_dataset(args.dataset, args.guess_list, args.output)
    counts = cast("dict[str, int]", summary["counts"])
    print(f"Rows: {counts['rows']}")
    print(f"Eligible: {counts['eligible']}")
    print(f"Excluded: {counts['excluded']} {sorted(cast(dict, summary['excluded']), key=int)}")
    print(f"Duplicate answers: {counts['duplicate_answers']}")
    print(f"Eligible rows with a unique answer: {counts['eligible_unique_answer_rows']}")
    print(f"Wrote {args.output} and {args.output.with_suffix('.summary.json')}")


if __name__ == "__main__":
    main()
