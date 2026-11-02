import csv
import tempfile
import unittest
from pathlib import Path

from ..experiment import manifest_final as m
from ..experiment.quartiles import QUARTILE_LABELS

REPO_ROOT = Path(__file__).resolve().parents[3]
PROCESSED = REPO_ROOT / "src" / "data" / "processed"
CLEAN_CSV = PROCESSED / "wordle_human_clean.csv"
QUARTILES = PROCESSED / "quartiles.json"
TERCILES = PROCESSED / "terciles.json"
MANIFESTS = REPO_ROOT / "experiments" / "manifests"
PILOTS = [MANIFESTS / name for name in ("pilot-01.csv", "pilot-02-deep.csv", "pilot-02-wide.csv")]
WIDE = MANIFESTS / "pilot-02-wide.csv"


def _ids(rows) -> list[str]:
    return [row["puzzle_id"] for row in rows]


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


class SelectFinalTest(unittest.TestCase):
    POOL = {"D1": [{"puzzle_id": str(i)} for i in range(30)]}
    TERCILE_OF = {str(i): ("T1", "T2", "T3")[i % 3] for i in range(30)}

    def test_counts_per_tercile_and_order(self):
        rows = m.select_final(self.POOL, self.TERCILE_OF, {"T1": 3, "T2": 2, "T3": 4}, seed=1)
        counts = {t: sum(1 for r in rows if self.TERCILE_OF[r["puzzle_id"]] == t) for t in ("T1", "T2", "T3")}
        self.assertEqual(counts, {"T1": 3, "T2": 2, "T3": 4})
        ids = [int(pid) for pid in _ids(rows)]
        self.assertEqual(ids, sorted(ids))

    def test_input_order_does_not_matter(self):
        reversed_pool = {"D1": list(reversed(self.POOL["D1"]))}
        counts = {"T1": 3, "T2": 3, "T3": 3}
        self.assertEqual(_ids(m.select_final(self.POOL, self.TERCILE_OF, counts, seed=5)),
                         _ids(m.select_final(reversed_pool, self.TERCILE_OF, counts, seed=5)))

    def test_too_small_tercile_raises(self):
        with self.assertRaises(ValueError):
            m.select_final(self.POOL, self.TERCILE_OF, {"T1": 11, "T2": 1, "T3": 1}, seed=1)


class SelectSmokeTest(unittest.TestCase):
    ROWS = [{"puzzle_id": str(i * 10 + j), "quartile": label}
            for i, label in enumerate(QUARTILE_LABELS) for j in range(5)]

    def test_two_per_quartile_sorted(self):
        rows = m.select_smoke(self.ROWS)
        self.assertEqual(len(rows), 8)
        for label in QUARTILE_LABELS:
            self.assertEqual(sum(1 for row in rows if row["quartile"] == label), 2)
        ids = [int(pid) for pid in _ids(rows)]
        self.assertEqual(ids, sorted(ids))

    def test_order_independent(self):
        self.assertEqual(_ids(m.select_smoke(self.ROWS)),
                         _ids(m.select_smoke(list(reversed(self.ROWS)))))

    def test_too_small_quartile_raises(self):
        with self.assertRaises(ValueError):
            m.select_smoke(self.ROWS[:-4])  # no D4 puzzles left


@unittest.skipUnless(all(p.exists() for p in [CLEAN_CSV, QUARTILES, TERCILES, *PILOTS]),
                     "processed data not present")
class RealManifestTest(unittest.TestCase):
    def _build(self, out: Path, excludes=PILOTS):
        return m.build_manifests(CLEAN_CSV, QUARTILES, TERCILES, excludes, WIDE, out)

    def test_rebuild_matches_committed_and_is_disjoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            summary = self._build(out)
            self.assertEqual(summary["pool_total"], 1729)
            for name in ("final.csv", "final-smoke.csv"):
                committed = MANIFESTS / name
                if committed.exists():
                    self.assertEqual((out / name).read_bytes(), committed.read_bytes(), name)

            # A second build gives the same bytes.
            again = out / "again"
            self._build(again)
            for name in ("final.csv", "final-smoke.csv"):
                self.assertEqual((out / name).read_bytes(), (again / name).read_bytes(), name)

            final = _read(out / "final.csv")
            smoke = _read(out / "final-smoke.csv")

        self.assertEqual(len(final), 100)
        self.assertEqual(len(smoke), 8)
        for label, count in m.FINAL_PER_TERCILE.items():
            self.assertEqual(sum(1 for row in final if row["tercile"] == label), count)
        self.assertEqual(m.FINAL_PER_TERCILE, {"T1": 33, "T2": 33, "T3": 34})
        for label in QUARTILE_LABELS:
            self.assertEqual(sum(1 for row in smoke if row["quartile"] == label), 2)

        pilot_ids = {pid for path in PILOTS for pid in _ids(_read(path))}
        final_ids = set(_ids(final))
        self.assertFalse(final_ids & pilot_ids)
        self.assertFalse(final_ids & set(_ids(smoke)))
        self.assertTrue(set(_ids(smoke)) <= set(_ids(_read(WIDE))))

        pilot_answers = {row["answer"] for path in PILOTS for row in _read(path)}
        final_answers = [row["answer"] for row in final]
        self.assertEqual(len(final_answers), len(set(final_answers)))
        self.assertFalse(set(final_answers) & pilot_answers)

        for row in final + smoke:
            self.assertIn(row["tercile"], ("T1", "T2", "T3"))
            self.assertAlmostEqual(sum(float(row[c]) for c in m.p2.BIN_COLUMNS), 1.0, places=9)
        self.assertEqual({row["split"] for row in final}, {"final"})
        self.assertEqual({row["split"] for row in smoke}, {"smoke"})

    def test_terciles_match_value_rule(self):
        # Away from the boundary ties, a puzzle's tercile follows its mean.
        final = _read(MANIFESTS / "final.csv") if (MANIFESTS / "final.csv").exists() else []
        for row in final:
            score = float(row["human_mean_score"])
            if score in (4.07, 4.42):
                continue
            expected = "T1" if score < 4.07 else "T2" if score < 4.42 else "T3"
            self.assertEqual(row["tercile"], expected, row["puzzle_id"])

    def test_smoke_source_must_be_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                self._build(Path(tmp), excludes=PILOTS[:2])

    def test_rejects_unfrozen_clean_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tampered = Path(tmp) / "clean.csv"
            tampered.write_bytes(CLEAN_CSV.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                m.build_manifests(tampered, QUARTILES, TERCILES, PILOTS, WIDE, Path(tmp) / "out")


if __name__ == "__main__":
    unittest.main()
