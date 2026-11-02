import json
import tempfile
import unittest
from pathlib import Path

from ..experiment import human_data
from ..experiment import terciles as t
from ..experiment.quartiles import RankedPuzzle, assign_quartiles, mapping_rule

REPO_ROOT = Path(__file__).resolve().parents[3]
CLEAN_CSV = REPO_ROOT / "src" / "data" / "processed" / "wordle_human_clean.csv"
QUARTILES = REPO_ROOT / "src" / "data" / "processed" / "quartiles.json"
TERCILES = REPO_ROOT / "src" / "data" / "processed" / "terciles.json"


def _puzzles(means):
    return [RankedPuzzle(str(i), m) for i, m in enumerate(means)]


class AssignTercilesTest(unittest.TestCase):
    def test_equal_sizes_and_order(self):
        labels, spec = t.assign_terciles(_puzzles([float(i) for i in range(6)]))
        self.assertEqual(spec.sizes, (2, 2, 2))
        self.assertEqual([labels[str(i)] for i in range(6)], ["T1", "T1", "T2", "T2", "T3", "T3"])
        self.assertEqual(spec.cut_points, (2.0, 4.0))

    def test_sizes_differ_by_at_most_one(self):
        for n in range(3, 30):
            _, spec = t.assign_terciles(_puzzles([i / 10 for i in range(n)]))
            self.assertEqual(sum(spec.sizes), n)
            self.assertLessEqual(max(spec.sizes) - min(spec.sizes), 1)

    def test_ties_broken_by_puzzle_id(self):
        labels, spec = t.assign_terciles(_puzzles([3.0, 4.0, 4.0, 4.0, 4.0, 5.0]))
        self.assertEqual(labels["1"], "T1")
        self.assertEqual(labels["2"], "T2")
        self.assertEqual(labels["4"], "T3")
        self.assertEqual(spec.boundary_ties, (1, 2))

    def test_rejects_too_few(self):
        with self.assertRaises(ValueError):
            t.assign_terciles(_puzzles([1.0, 2.0]))

    def test_json_labels_and_rule(self):
        _, spec = t.assign_terciles(_puzzles([1.0, 2.0, 3.0]))
        payload = spec.to_json()
        self.assertEqual(payload["labels"], ["T1", "T2", "T3"])
        self.assertEqual(payload["mapping_rule"], "T1: s < c1; T2: c1 <= s < c2; T3: s >= c2")


class QuartileDefaultsTest(unittest.TestCase):
    def test_quartile_rule_unchanged(self):
        _, spec = assign_quartiles(_puzzles([float(i) for i in range(8)]))
        self.assertEqual(spec.to_json()["mapping_rule"],
                         "D1: s < c1; D2: c1 <= s < c2; D3: c2 <= s < c3; D4: s >= c3")
        self.assertEqual(mapping_rule(("A", "B")), "A: s < c1; B: s >= c1")


class MapScoreTest(unittest.TestCase):
    CUTS = (4.07, 4.42)

    def test_boundaries(self):
        self.assertEqual(t.map_score(3.0, self.CUTS), "T1")
        self.assertEqual(t.map_score(4.0699, self.CUTS), "T1")
        self.assertEqual(t.map_score(4.07, self.CUTS), "T2")
        self.assertEqual(t.map_score(4.4199, self.CUTS), "T2")
        self.assertEqual(t.map_score(4.42, self.CUTS), "T3")
        self.assertEqual(t.map_score(7.0, self.CUTS), "T3")

    def test_rejects_bad_cuts(self):
        with self.assertRaises(ValueError):
            t.map_score(4.0, (3.98, 4.24, 4.53))
        with self.assertRaises(ValueError):
            t.map_score(4.0, (4.42, 4.07))


class RankSplitTest(unittest.TestCase):
    def test_matches_assign_terciles(self):
        means = [4.3, 3.9, 5.0, 4.1, 4.6, 3.7, 4.4]
        labels, _ = t.assign_terciles(_puzzles(means))
        self.assertEqual(t.rank_split(means, list(range(len(means)))),
                         [labels[str(i)] for i in range(len(means))])


@unittest.skipUnless(CLEAN_CSV.exists() and QUARTILES.exists(), "processed data not present")
class RealTercilesTest(unittest.TestCase):
    def test_frozen_definition(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "terciles.json"
            payload = t.build_terciles(CLEAN_CSV, QUARTILES, out)
            if TERCILES.exists():
                built, committed = json.loads(out.read_text()), json.loads(TERCILES.read_text())
                # Paths differ with the working directory; the hashes must not.
                for name in ("clean_csv", "quartiles_json"):
                    built["source"].pop(name)
                    committed["source"].pop(name)
                self.assertEqual(built, committed)
        self.assertEqual(payload["population_size"], 1861)
        self.assertEqual(payload["sizes"], [620, 620, 621])
        self.assertEqual(payload["cut_points"], [4.07, 4.42])

    def test_human_puzzles_map_back_except_boundary_ties(self):
        rows = t.eligible_rows(CLEAN_CSV)
        labels, spec = t.assign_terciles(
            [RankedPuzzle(r["puzzle_id"], round(float(r["human_mean_score"]), 6)) for r in rows]
        )
        moved = sum(
            1 for r in rows
            if t.map_score(round(float(r["human_mean_score"]), 6), spec.cut_points)
            != labels[r["puzzle_id"]]
        )
        self.assertEqual(moved, sum(spec.boundary_ties))

    def test_rejects_unfrozen_clean_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tampered = Path(tmp) / "clean.csv"
            tampered.write_bytes(CLEAN_CSV.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                t.build_terciles(tampered, QUARTILES, Path(tmp) / "terciles.json")

    def test_quartiles_json_still_reproduces(self):
        rows, spec = human_data.clean_records(
            human_data.load_dataset(REPO_ROOT / "src" / "data" / "raw" / "worldepuzzles.json"),
            human_data.load_vocabulary(REPO_ROOT / "src" / "data" / "raw" / "allowed_guesses.txt"),
        )
        frozen = json.loads(QUARTILES.read_text())
        for key, value in spec.to_json().items():
            self.assertEqual(value, frozen[key], key)
        self.assertEqual(len([r for r in rows if r.quartile]), 1861)


if __name__ == "__main__":
    unittest.main()
