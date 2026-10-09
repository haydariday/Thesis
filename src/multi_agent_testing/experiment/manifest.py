"""Build a deterministic Wordle pilot manifest from the raw Worlde dataset.

The module is self-contained (standard library only) and is meant to be run as

    python -m multi_agent_testing.experiment.manifest \
        --dataset src/data/raw/worldepuzzles.json \
        --guess-list src/data/raw/allowed_guesses.txt \
        --output-dir experiments/manifests \
        --pilot-size 20 --seed 20261008 --name pilot-01

It writes two CSVs into the output directory:

* ``<name>.csv`` - the selected pilot rows, ordered by ascending puzzle id.
* ``<name>-eligible.csv`` - every dataset row with its eligibility verdict.

Human baseline reconstruction
-----------------------------
``individual`` holds the whole-percent shares of human games solved in 1..6
tries; the remainder, ``100 - S`` with ``S = sum(individual)``, is treated as
the unsolved share, which is scored as 7:

    human_loss_pct   = 100.0 - S
    human_mean_score = sum(k * p_k for k in 1..6) / 100 + 7 * human_loss_pct / 100

Because the published shares are rounded to whole percents, ``S`` (and hence
the loss) is only accurate to about +/- 3 points. The sensitivity bounds
therefore rebuild the unsolved term at ``loss - 3`` (``human_mean_low``) and
``loss + 3`` (``human_mean_high``), clamped to ``[0, 100]``, so
``human_mean_low`` and ``human_mean_high`` bound the reconstructed mean from
below and above respectively. The easy/hard label uses the unrounded
``human_mean_score`` (``easy`` below 4.0, otherwise ``hard``). Only standard
mode is reconstructed
(the top-level arrays; ``hardmode`` is never used).

Eligibility rules
-----------------
A record is eligible when *all* of the checks below pass. Every failed check
adds a note and the collected notes are joined with ``"; "``:

* the JSON key is ASCII decimal digits and ``num == int(key)``
  ("num mismatch");
* ``answer`` matches ``^[A-Z]{5}$`` ("invalid answer");
* ``individual`` is a list of six non-negative ints equal to the successive
  differences of ``cumulative`` ("invalid distribution");
* ``40 <= sum(individual) <= 100`` ("implausible solved share S=<S>");
* ``sample`` is an int ``> 0`` ("missing sample");
* the answer is present in the uppercased guess vocabulary
  ("answer outside vocabulary");
* the key is not one of the quarantined study ids 620, 625, 1273, 1502
  ("quarantined (dataset diagnostic)").

Eligible records whose solved share sits within three points of the 40% floor
(``S <= 42``) additionally carry an "extreme solved share S=<S>" note in the
CSV outputs.

Pilot selection
---------------
Eligible records are sorted by ``(human_mean_score, int(puzzle_id))`` and split
into ten contiguous near-equal strata. A ``random.Random(seed)`` instance draws
up to two records per stratum (all of them when a stratum has fewer than two).
If that yields fewer than ``pilot_size`` rows, the remaining picks come from
the stratum with the most unselected eligible records (lowest index on ties)
via ``rng.choice``. Selection is reproducible for a fixed seed.
"""

import argparse
import csv
import json
import random
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

QUARANTINED_PUZZLE_IDS: frozenset[str] = frozenset({"620", "625", "1273", "1502"})
QUARANTINE_NOTE = "quarantined (dataset diagnostic)"
MIN_SOLVED_SHARE = 40
MAX_SOLVED_SHARE = 100
# S - 3 can fall below the plausibility floor when S <= 42.
EXTREME_SOLVED_SHARE_MAX = 42
ROUNDING_SENSITIVITY = 3
STRATUM_COUNT = 10
PER_STRATUM_SAMPLE = 2
ANSWER_PATTERN = re.compile(r"[A-Z]{5}")

PILOT_COLUMNS: tuple[str, ...] = (
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
)

ELIGIBLE_COLUMNS: tuple[str, ...] = (
    "puzzle_id",
    "date",
    "answer",
    "human_mean_score",
    "human_label",
    "eligible",
    "eligibility_notes",
)


@dataclass(frozen=True)
class PuzzleAudit:
    """Eligibility verdict and reconstructed human baseline for one puzzle."""

    puzzle_id: str
    date: str
    answer: str
    eligible: bool
    notes: str
    solved_share: int | None
    sample: int | None
    human_mean_score: float | None
    human_mean_low: float | None
    human_mean_high: float | None
    human_loss_pct: float | None
    human_label: str | None


def load_dataset(path: Path) -> dict[str, dict[str, object]]:
    """Load the raw puzzle JSON, requiring an object of records keyed by id."""

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise TypeError("Expected the dataset to be a JSON object keyed by puzzle id.")

    for puzzle_id, record in payload.items():
        if not isinstance(puzzle_id, str) or not isinstance(record, dict):
            raise TypeError("Expected string puzzle ids mapped to JSON objects.")

    return cast("dict[str, dict[str, object]]", payload)


def load_vocabulary(path: Path) -> set[str]:
    """Load a one-word-per-line vocabulary, uppercased and validated."""

    words: set[str] = set()

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            word = line.strip()

            if not word:
                continue

            upper = word.upper()

            if not word.isascii() or ANSWER_PATTERN.fullmatch(upper) is None:
                raise ValueError(
                    f"Invalid vocabulary entry at line {line_number}: {word!r}"
                )

            words.add(upper)

    if not words:
        raise ValueError("Vocabulary is empty.")

    return words


def _integer_field(value: object) -> int | None:
    """Return the value when it is a genuine int (not bool), else None."""

    if type(value) is int:
        return cast(int, value)
    return None


def _six_ints(value: object) -> list[int] | None:
    """Return the value when it is a list of six genuine ints, else None."""

    if not isinstance(value, list) or len(value) != 6:
        return None
    if any(type(item) is not int for item in value):
        return None
    return cast("list[int]", value)


def _distribution_share(
    record: Mapping[str, object],
) -> tuple[list[int] | None, int | None]:
    """Validate ``individual`` against the differences of ``cumulative``.

    Returns the individual shares and their sum, or ``(None, None)`` when the
    distribution is structurally invalid.
    """

    individual = _six_ints(record.get("individual"))
    cumulative = _six_ints(record.get("cumulative"))

    if individual is None or cumulative is None:
        return None, None

    if any(share < 0 for share in individual):
        return None, None

    expected = cumulative[:1] + [
        cumulative[index] - cumulative[index - 1] for index in range(1, 6)
    ]

    if individual != expected:
        return None, None

    return individual, sum(individual)


def reconstruct_human_baseline(
    individual: list[int],
) -> tuple[float, float, float, float, str]:
    """Rebuild the human mean score and its rounding-sensitivity bounds.

    Returns ``(human_mean_score, human_mean_low, human_mean_high,
    human_loss_pct, human_label)``.
    """

    solved_share = sum(individual)
    loss_pct = 100.0 - solved_share
    solved_term = sum(tries * share for tries, share in enumerate(individual, start=1)) / 100.0

    mean = solved_term + 7.0 * loss_pct / 100.0
    low = solved_term + 7.0 * max(0.0, loss_pct - ROUNDING_SENSITIVITY) / 100.0
    high = solved_term + 7.0 * min(100.0, loss_pct + ROUNDING_SENSITIVITY) / 100.0
    label = "easy" if mean < 4.0 else "hard"

    return mean, low, high, loss_pct, label


def audit_record(
    puzzle_id: str,
    record: Mapping[str, object],
    vocabulary: set[str],
) -> PuzzleAudit:
    """Apply the eligibility rules and reconstruct the baseline when eligible."""

    failures: list[str] = []

    number = _integer_field(record.get("num"))
    key_is_numeric = puzzle_id.isascii() and puzzle_id.isdecimal()
    if not key_is_numeric or number is None or number != int(puzzle_id):
        failures.append("num mismatch")

    answer_value = record.get("answer")
    answer = answer_value if isinstance(answer_value, str) else ""
    answer_is_valid = ANSWER_PATTERN.fullmatch(answer) is not None
    if not answer_is_valid:
        failures.append("invalid answer")

    individual, solved_share = _distribution_share(record)
    if individual is None:
        failures.append("invalid distribution")
    elif not (MIN_SOLVED_SHARE <= cast(int, solved_share) <= MAX_SOLVED_SHARE):
        failures.append(f"implausible solved share S={solved_share}")

    sample = _integer_field(record.get("sample"))
    if sample is None or sample <= 0:
        failures.append("missing sample")

    if puzzle_id in QUARANTINED_PUZZLE_IDS:
        failures.append(QUARANTINE_NOTE)

    if answer_is_valid and answer not in vocabulary:
        failures.append("answer outside vocabulary")

    eligible = not failures
    notes = list(failures)

    mean: float | None = None
    low: float | None = None
    high: float | None = None
    loss: float | None = None
    label: str | None = None

    if eligible:
        mean, low, high, loss, label = reconstruct_human_baseline(
            cast("list[int]", individual)
        )
        if solved_share is not None and solved_share <= EXTREME_SOLVED_SHARE_MAX:
            notes.append(f"extreme solved share S={solved_share}")

    date_value = record.get("date")

    return PuzzleAudit(
        puzzle_id=puzzle_id,
        date=date_value if isinstance(date_value, str) else "",
        answer=answer,
        eligible=eligible,
        notes="; ".join(notes),
        solved_share=solved_share,
        sample=sample,
        human_mean_score=mean,
        human_mean_low=low,
        human_mean_high=high,
        human_loss_pct=loss,
        human_label=label,
    )


def _puzzle_sort_key(puzzle_id: str) -> tuple[int, int, str]:
    """Sort numeric ids numerically; non-numeric ids (never eligible) last."""

    if puzzle_id.isascii() and puzzle_id.isdecimal():
        return (0, int(puzzle_id), "")
    return (1, 0, puzzle_id)


def _eligible_sort_key(item: PuzzleAudit) -> tuple[float, int]:
    mean = item.human_mean_score
    return (mean if mean is not None else 0.0, int(item.puzzle_id))


def stratified_pilot_selection(
    eligible: list[PuzzleAudit],
    pilot_size: int,
    seed: int,
) -> list[PuzzleAudit]:
    """Draw a seeded, stratified pilot set from eligible records.

    ``eligible`` must already be ordered by ``(human_mean_score,
    int(puzzle_id))``.
    """

    rng = random.Random(seed)
    count = len(eligible)
    strata = [
        eligible[index * count // STRATUM_COUNT : (index + 1) * count // STRATUM_COUNT]
        for index in range(STRATUM_COUNT)
    ]

    selected: list[PuzzleAudit] = []
    for stratum in strata:
        if len(stratum) >= PER_STRATUM_SAMPLE:
            selected.extend(rng.sample(stratum, PER_STRATUM_SAMPLE))
        else:
            selected.extend(stratum)

    selected_ids = {item.puzzle_id for item in selected}

    while len(selected) < pilot_size:
        remaining = [
            [item for item in stratum if item.puzzle_id not in selected_ids]
            for stratum in strata
        ]
        # max() returns the first maximal index, so ties go to the lowest stratum.
        best_index = max(range(STRATUM_COUNT), key=lambda index: len(remaining[index]))

        if not remaining[best_index]:
            break

        pick = rng.choice(remaining[best_index])
        selected.append(pick)
        selected_ids.add(pick.puzzle_id)

    return selected


def _format_float(value: float | None) -> float | str:
    """Round floats to 3 decimals; blank out values that cannot be computed."""

    return "" if value is None else round(value, 3)


def write_pilot_csv(path: Path, selected: list[PuzzleAudit], seed: int) -> None:
    """Write the selected pilot rows, ordered by ascending integer puzzle id."""

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=PILOT_COLUMNS)
        writer.writeheader()

        for row in selected:
            writer.writerow(
                {
                    "puzzle_id": row.puzzle_id,
                    "date": row.date,
                    "answer": row.answer,
                    "human_mean_score": _format_float(row.human_mean_score),
                    "human_mean_low": _format_float(row.human_mean_low),
                    "human_mean_high": _format_float(row.human_mean_high),
                    "human_loss_pct": _format_float(row.human_loss_pct),
                    "human_label": row.human_label if row.human_label is not None else "",
                    "human_mode": "standard",
                    "human_sample_size_if_known": (
                        row.sample if row.sample is not None else ""
                    ),
                    "split": "pilot",
                    "eligibility_notes": row.notes,
                    "selection_seed": seed,
                }
            )


def write_eligible_csv(path: Path, audits: list[PuzzleAudit]) -> None:
    """Write every dataset record with its eligibility verdict."""

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=ELIGIBLE_COLUMNS)
        writer.writeheader()

        for row in audits:
            writer.writerow(
                {
                    "puzzle_id": row.puzzle_id,
                    "date": row.date,
                    "answer": row.answer,
                    "human_mean_score": _format_float(row.human_mean_score),
                    "human_label": row.human_label if row.human_label is not None else "",
                    "eligible": row.eligible,
                    "eligibility_notes": row.notes,
                }
            )


def build_manifest(
    dataset_path: Path,
    guess_list_path: Path,
    output_dir: Path,
    pilot_size: int,
    seed: int,
    name: str,
) -> tuple[list[PuzzleAudit], list[PuzzleAudit], list[PuzzleAudit]]:
    """Audit the dataset, select the pilot set, and write both CSV outputs.

    Returns ``(all_audits, eligible, selected)``.
    """

    dataset = load_dataset(dataset_path)
    vocabulary = load_vocabulary(guess_list_path)

    audits = [
        audit_record(puzzle_id, dataset[puzzle_id], vocabulary)
        for puzzle_id in sorted(dataset, key=_puzzle_sort_key)
    ]
    eligible = [audit for audit in audits if audit.eligible]
    eligible.sort(key=_eligible_sort_key)

    selected = stratified_pilot_selection(eligible, pilot_size, seed)
    selected.sort(key=lambda item: int(item.puzzle_id))

    output_dir.mkdir(parents=True, exist_ok=True)
    write_pilot_csv(output_dir / f"{name}.csv", selected, seed)
    write_eligible_csv(output_dir / f"{name}-eligible.csv", audits)

    return audits, eligible, selected


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(
        description="Build a deterministic Wordle pilot manifest.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Path to the raw puzzle JSON.",
    )
    parser.add_argument(
        "--guess-list",
        type=Path,
        required=True,
        help="Path to the allowed Wordle guesses, one word per line.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for the manifest CSVs (created if needed).",
    )
    parser.add_argument(
        "--pilot-size",
        type=int,
        default=20,
        help="Number of pilot puzzles to select (default: 20).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261008,
        help="Seed for the deterministic selection (default: 20261008).",
    )
    parser.add_argument(
        "--name",
        default="pilot-01",
        help="Base name of the output CSVs (default: pilot-01).",
    )

    args = parser.parse_args()

    audits, eligible, selected = build_manifest(
        dataset_path=args.dataset,
        guess_list_path=args.guess_list,
        output_dir=args.output_dir,
        pilot_size=args.pilot_size,
        seed=args.seed,
        name=args.name,
    )

    easy = sum(1 for item in selected if item.human_label == "easy")
    hard = len(selected) - easy
    means = [
        cast(float, item.human_mean_score)
        for item in selected
        if item.human_mean_score is not None
    ]

    print(f"Dataset rows: {len(audits)}")
    print(f"Eligible records: {len(eligible)}")
    print(f"Selected for pilot: {len(selected)}")
    print(f"Selection labels: easy={easy}, hard={hard}")
    if means:
        print(f"Selection mean range: {min(means):.3f} to {max(means):.3f}")
    print("Selected puzzle ids: " + ", ".join(item.puzzle_id for item in selected))


if __name__ == "__main__":
    main()
