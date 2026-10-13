import csv
import json
import tempfile
import unittest
from pathlib import Path

from ..experiment import human_data, manifest

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DATASET = REPO_ROOT / "src" / "data" / "raw" / "worldepuzzles.json"
RAW_GUESSES = REPO_ROOT / "src" / "data" / "raw" / "allowed_guesses.txt"


def _record(num: int, answer: str, individual: list[int], sample: int | None = 1000):
    cumulative = []
    running = 0
    for share in individual:
        running += share
        cumulative.append(running)
    record: dict[str, object] = {
        "num": num,
        "date": "01/01",
        "answer": answer,
        "individual": individual,
        "cumulative": cumulative,
    }
    if sample is not None:
        record["sample"] = sample
    return record


class SevenBinTest(unittest.TestCase):
    def test_fail_bin_is_remainder(self):
        bins = human_data.seven_bin_distribution([1, 5, 20, 35, 25, 10])
        self.assertEqual(len(bins), 7)
        self.assertAlmostEqual(bins[6], 0.04)
        self.assertAlmostEqual(sum(bins), 1.0)

    def test_full_solve_has_zero_fail(self):
        bins = human_data.seven_bin_distribution([0, 0, 0, 0, 0, 100])
        self.assertEqual(bins[6], 0.0)
        self.assertAlmostEqual(human_data.distribution_mean(bins), 6.0)

    def test_rejects_negative_fail(self):
        with self.assertRaises(ValueError):
            human_data.seven_bin_distribution([50, 51, 0, 0, 0, 0])

    def test_rejects_negative_share(self):
        with self.assertRaises(ValueError):
            human_data.seven_bin_distribution([-1, 0, 0, 0, 0, 50])

    def test_mean_matches_manifest(self):
        individual = [0, 3, 18, 33, 27, 13]
        bins = human_data.seven_bin_distribution(individual)
        expected = manifest.reconstruct_human_baseline(individual)[0]
        self.assertAlmostEqual(human_data.distribution_mean(bins), expected)


class CleanRecordsTest(unittest.TestCase):
    def setUp(self):
        self.vocabulary = {"CIGAR", "REBUT", "SISSY", "PARER"}
        self.dataset = {
            "1": _record(1, "CIGAR", [1, 5, 20, 35, 25, 10]),
            "2": _record(2, "REBUT", [0, 4, 21, 36, 26, 10], sample=None),
            "3": _record(3, "SISSY", [0, 0, 0, 0, 0, 0]),
            "4": _record(4, "PARER", [0, 1, 4, 10, 13, 13]),
            "5": _record(5, "CIGAR", [1, 6, 22, 34, 24, 10]),
        }

    def test_eligibility_and_bins(self):
        rows = {r.audit.puzzle_id: r for r in human_data.clean_records(self.dataset, self.vocabulary)}

        self.assertTrue(rows["1"].audit.eligible)
        self.assertFalse(rows["2"].audit.eligible)  # missing sample
        self.assertFalse(rows["3"].audit.eligible)  # S = 0
        self.assertTrue(rows["4"].audit.eligible)  # 59% fail is kept

        # Bins are present for structurally valid rows even when ineligible.
        self.assertIsNotNone(rows["2"].bins)
        self.assertAlmostEqual(rows["4"].bins[6], 0.59)
        self.assertIsNone(rows["2"].audit.human_mean_score)

    def test_duplicate_answers(self):
        rows = {r.audit.puzzle_id: r for r in human_data.clean_records(self.dataset, self.vocabulary)}
        self.assertEqual(rows["1"].answer_occurrence, 1)
        self.assertEqual(rows["5"].answer_occurrence, 2)
        self.assertTrue(rows["1"].duplicate_answer)
        self.assertFalse(rows["4"].duplicate_answer)
        self.assertIsNone(rows["2"].duplicate_answer)

    def test_mode_bin(self):
        rows = {r.audit.puzzle_id: r for r in human_data.clean_records(self.dataset, self.vocabulary)}
        self.assertEqual(rows["1"].mode_bin, 4)
        self.assertEqual(rows["4"].mode_bin, 7)

    def test_csv_round_trip(self):
        rows = human_data.clean_records(self.dataset, self.vocabulary)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.csv"
            human_data.write_clean_csv(path, rows)
            with path.open(encoding="utf-8", newline="") as file:
                written = list(csv.DictReader(file))

        self.assertEqual([r["puzzle_id"] for r in written], ["1", "2", "3", "4", "5"])
        self.assertEqual(tuple(written[0].keys()), human_data.CLEAN_COLUMNS)
        first = written[0]
        self.assertAlmostEqual(sum(float(first[c]) for c in human_data.BIN_COLUMNS), 1.0)
        self.assertEqual(written[1]["human_mean_score"], "")


@unittest.skipUnless(RAW_DATASET.exists() and RAW_GUESSES.exists(), "raw dataset not present")
class RealDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        output = Path(cls.tmp.name) / "wordle_human_clean.csv"
        cls.rows, cls.summary = human_data.build_clean_dataset(RAW_DATASET, RAW_GUESSES, output)
        cls.output = output

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_counts(self):
        counts = self.summary["counts"]
        self.assertEqual(counts["rows"], 1865)
        self.assertEqual(counts["eligible"], 1861)
        self.assertEqual(sorted(self.summary["excluded"], key=int), ["620", "625", "1273", "1502"])

    def test_bins_sum_to_one_and_means_match(self):
        for row in self.rows:
            if not row.audit.eligible:
                continue
            self.assertIsNotNone(row.bins)
            self.assertAlmostEqual(sum(row.bins), 1.0, places=9)
            self.assertAlmostEqual(
                human_data.distribution_mean(row.bins),
                row.audit.human_mean_score,
                places=9,
            )

    def test_hard_tail_is_kept(self):
        by_id = {r.audit.puzzle_id: r for r in self.rows}
        self.assertTrue(by_id["454"].audit.eligible)  # PARER
        self.assertEqual(self.summary["human_mean"]["max"]["answer"], "PARER")

    def test_summary_file_written(self):
        summary_path = self.output.with_suffix(".summary.json")
        loaded = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["counts"], self.summary["counts"])


if __name__ == "__main__":
    unittest.main()
