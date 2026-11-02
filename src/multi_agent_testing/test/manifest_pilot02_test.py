import csv
import json
import tempfile
import unittest
from pathlib import Path

from ..experiment import manifest_pilot02 as m
from ..experiment.quartiles import QUARTILE_LABELS

REPO_ROOT = Path(__file__).resolve().parents[3]
CLEAN_CSV = REPO_ROOT / "src" / "data" / "processed" / "wordle_human_clean.csv"
QUARTILES = REPO_ROOT / "src" / "data" / "processed" / "quartiles.json"
MANIFESTS = REPO_ROOT / "experiments" / "manifests"
PILOT_01 = MANIFESTS / "pilot-01.csv"


def _row(puzzle_id: int, quartile: str, *, eligible=True, duplicate=False) -> dict[str, str]:
    return {
        "puzzle_id": str(puzzle_id),
        "eligible": str(eligible),
        "duplicate_answer": str(duplicate) if eligible else "",
        "quartile": quartile if eligible else "",
    }


def _synthetic_rows(per_quartile: int) -> list[dict[str, str]]:
    return [
        _row(index * 100 + offset, label)
        for index, label in enumerate(QUARTILE_LABELS)
        for offset in range(per_quartile)
    ]


def _ids(rows) -> list[str]:
    return [row["puzzle_id"] for row in rows]


class SamplingPoolTest(unittest.TestCase):
    def test_excludes_ineligible_duplicates_and_listed_ids(self):
        rows = [
            _row(1, "D1"),
            _row(2, "D1", duplicate=True),
            _row(3, "D1", eligible=False),
            _row(4, "D1"),
            _row(5, "D2"),
        ]
        pool = m.sampling_pool(rows, excluded_ids={"4"})
        self.assertEqual(_ids(pool["D1"]), ["1"])
        self.assertEqual(_ids(pool["D2"]), ["5"])
        self.assertEqual(pool["D3"], [])

    def test_pool_is_ordered_by_integer_id(self):
        rows = [_row(10, "D1"), _row(9, "D1"), _row(100, "D1")]
        pool = m.sampling_pool(rows, excluded_ids=set())
        self.assertEqual(_ids(pool["D1"]), ["9", "10", "100"])


class SelectManifestsTest(unittest.TestCase):
    def setUp(self):
        self.pool = m.sampling_pool(_synthetic_rows(20), excluded_ids=set())

    def test_sizes_per_quartile(self):
        selected = m.select_manifests(self.pool)
        for draw in m.DRAWS:
            rows = selected[draw.name]
            self.assertEqual(len(rows), 4 * draw.per_quartile)
            for label in QUARTILE_LABELS:
                count = sum(1 for row in rows if row["quartile"] == label)
                self.assertEqual(count, draw.per_quartile)

    def test_draws_are_disjoint(self):
        selected = m.select_manifests(self.pool)
        deep = set(_ids(selected[m.DEEP.name]))
        wide = set(_ids(selected[m.WIDE.name]))
        self.assertFalse(deep & wide)

    def test_deterministic_and_order_independent(self):
        first = m.select_manifests(self.pool)
        shuffled = m.sampling_pool(list(reversed(_synthetic_rows(20))), excluded_ids=set())
        second = m.select_manifests(shuffled)
        for draw in m.DRAWS:
            self.assertEqual(_ids(first[draw.name]), _ids(second[draw.name]))

    def test_rows_sorted_by_puzzle_id(self):
        for rows in m.select_manifests(self.pool).values():
            ids = [int(pid) for pid in _ids(rows)]
            self.assertEqual(ids, sorted(ids))

    def test_too_small_quartile_raises(self):
        pool = m.sampling_pool(_synthetic_rows(14), excluded_ids=set())
        with self.assertRaises(ValueError):
            m.select_manifests(pool)  # 3 + 12 = 15 needed per quartile


@unittest.skipUnless(CLEAN_CSV.exists() and QUARTILES.exists() and PILOT_01.exists(),
                     "processed data not present")
class RealManifestTest(unittest.TestCase):
    def test_rebuild_matches_committed_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            summary = m.build_manifests(CLEAN_CSV, QUARTILES, [PILOT_01], out)
            self.assertEqual(summary["pool_total"], 1789)
            for draw in m.DRAWS:
                name = f"{draw.name}.csv"
                committed = MANIFESTS / name
                if committed.exists():
                    self.assertEqual((out / name).read_bytes(), committed.read_bytes(), name)

            deep = self._read(out / "pilot-02-deep.csv")
            wide = self._read(out / "pilot-02-wide.csv")
            self.assertEqual(len(deep), 12)
            self.assertEqual(len(wide), 48)

            pilot_01 = set(_ids(self._read(PILOT_01)))
            deep_ids, wide_ids = set(_ids(deep)), set(_ids(wide))
            self.assertFalse(deep_ids & wide_ids)
            self.assertFalse((deep_ids | wide_ids) & pilot_01)

            answers = [row["answer"] for row in deep + wide]
            self.assertEqual(len(answers), len(set(answers)))

            for row in deep + wide:
                bins = sum(float(row[column]) for column in m.BIN_COLUMNS)
                self.assertAlmostEqual(bins, 1.0, places=9)

    def test_rejects_unfrozen_clean_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tampered = Path(tmp) / "clean.csv"
            tampered.write_bytes(CLEAN_CSV.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                m.build_manifests(tampered, QUARTILES, [PILOT_01], Path(tmp) / "out")

    @staticmethod
    def _read(path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))


if __name__ == "__main__":
    unittest.main()
