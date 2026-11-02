import contextlib
import io
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from ..agent.backend import ScriptedBackend
from ..experiment import analysis_pilot02 as analysis
from ..experiment import runner
from ..experiment.analysis_pilot02 import (
    Experiment,
    PuzzleRuns,
    alignment_metrics,
    cap_scores,
    capped,
    consistency_metrics,
    correlation_p_value,
    distribution_rows,
    experiment_block,
    icc_oneway,
    kendall_tau_b,
    load_fingerprints,
    missing_as_loss,
    pairwise_agreement,
    pooling_blockers,
    quadratic_weighted_kappa,
    stratified_bootstrap,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET = REPO_ROOT / "src" / "data" / "raw" / "worldepuzzles.json"
GUESSES = REPO_ROOT / "src" / "data" / "raw" / "allowed_guesses.txt"
QUARTILES = REPO_ROOT / "src" / "data" / "processed" / "quartiles.json"
CUTS = [3.98, 4.24, 4.53]
QUARTILE_LABELS_FOR_TEST = ("D1", "D2", "D3", "D4")


def puzzle(
    puzzle_id: str,
    quartile: str,
    human: float,
    scores: list[float],
    loss: float = 7,
    human_bins: tuple[float, ...] = (),
) -> PuzzleRuns:
    return PuzzleRuns(
        experiment="test",
        puzzle_id=puzzle_id,
        answer="",
        human_quartile=quartile,
        human_mean=human,
        human_mean_low=None,
        human_mean_high=None,
        planned_runs=len(scores),
        scores=tuple(scores),
        wins=sum(1 for score in scores if score < loss),
        losses=sum(1 for score in scores if score == loss),
        failed_attempts=0,
        human_bins=human_bins,
    )


class ConsistencyTests(unittest.TestCase):
    def test_icc_matches_a_hand_calculation(self):
        # Groups {1,2} and {3,4}: MSB = 4, MSW = 0.5, k = 2.
        result = icc_oneway([[1, 2], [3, 4]])

        self.assertAlmostEqual(result["icc_1_1"] or 0, 3.5 / 4.5)
        self.assertAlmostEqual(result["icc_1_k"] or 0, 3.5 / 4)
        self.assertAlmostEqual(result["k0"] or 0, 2)

    def test_icc_edge_cases(self):
        self.assertIsNone(icc_oneway([[4, 4], [4, 4]])["icc_1_1"])  # no variance at all
        self.assertAlmostEqual(icc_oneway([[3, 3], [5, 5]])["icc_1_1"] or 0, 1.0)  # no within-puzzle variance
        self.assertIsNone(icc_oneway([[4, 5]])["icc_1_1"])  # one puzzle

    def test_pairwise_agreement(self):
        self.assertEqual(pairwise_agreement([4, 4, 5]), (3, 1, 2.0))
        self.assertEqual(pairwise_agreement([4]), (0, 0, 0.0))

    def test_consistency_metrics(self):
        result = consistency_metrics(
            [puzzle("1", "D1", 3.5, [4, 4, 4]), puzzle("2", "D2", 4.1, [3, 5, 7])]
        )

        self.assertEqual(result["puzzles"], 2)
        self.assertAlmostEqual(result["mean_within_sd"], (0 + 2) / 2)
        self.assertAlmostEqual(result["pooled_within_sd"], (8 / 4) ** 0.5)
        self.assertAlmostEqual(result["exact_match_rate"], 3 / 6)
        self.assertAlmostEqual(result["mean_pairwise_abs_diff"], (0 + 2 + 4 + 2) / 6)
        self.assertAlmostEqual(result["win_rate"], 5 / 6)


class AlignmentTests(unittest.TestCase):
    def test_kappa_matches_hand_calculations(self):
        self.assertAlmostEqual(quadratic_weighted_kappa([(0, 0), (1, 1), (2, 2), (3, 3)], 4) or 0, 1.0)
        self.assertAlmostEqual(quadratic_weighted_kappa([(0, 0), (1, 1), (0, 1), (1, 0)], 2) or 0, 0.0)
        # One D1 puzzle read as D2: observed 1/9, expected 8/9, so 1 - 1/8.
        self.assertAlmostEqual(quadratic_weighted_kappa([(0, 1), (1, 1), (2, 2), (3, 3)], 4) or 0, 0.875)

    def test_alignment_metrics(self):
        puzzles = [
            puzzle("1", "D1", 3.8, [4, 4]),  # 4.0 maps to D2: one step harder
            puzzle("2", "D2", 4.1, [4, 4]),  # D2, exact
            puzzle("3", "D3", 4.4, [3, 3]),  # D1: two steps easier
            puzzle("4", "D4", 4.9, [5, 5]),  # D4, exact
        ]
        result = alignment_metrics(puzzles, CUTS)

        self.assertAlmostEqual(result["mae"], (0.2 + 0.1 + 1.4 + 0.1) / 4)
        self.assertAlmostEqual(result["signed_error"], (0.2 - 0.1 - 1.4 + 0.1) / 4)
        self.assertEqual(result["quartile_exact"], 0.5)
        self.assertEqual(result["quartile_adjacent"], 0.75)
        counts = result["confusion_matrix"]["counts"]
        self.assertEqual(counts["D1"]["D2"], 1)
        self.assertEqual(counts["D3"]["D1"], 1)
        self.assertEqual(result["quartile_recall"], {"D1": 0.0, "D2": 1.0, "D3": 0.0, "D4": 1.0})

    def test_kendall_tau_b(self):
        # One swapped pair out of six: (5 - 1) / 6.
        self.assertAlmostEqual(kendall_tau_b([1, 2, 3, 4], [1, 3, 2, 4]) or 0, 4 / 6)
        # One tie in x: (2 - 0) / sqrt((2 + 1) * 2).
        self.assertAlmostEqual(kendall_tau_b([1, 1, 2], [1, 2, 3]) or 0, 2 / 6 ** 0.5)
        self.assertIsNone(kendall_tau_b([4, 4], [1, 2]))
        self.assertIsNone(kendall_tau_b([1], [1]))

    def test_correlation_p_value_matches_scipy(self):
        # Reference values from scipy.stats.t (two-sided, n - 2 df).
        for r, n, expected in (
            (0.5, 12, 0.0978546142578125),
            (0.3, 48, 0.03829738000375187),
            (-0.4, 20, 0.08055387210850923),
            (0.05, 100, 0.6212899778453028),
        ):
            self.assertAlmostEqual(correlation_p_value(r, n) or 0, expected, places=10)
        self.assertEqual(correlation_p_value(1.0, 5), 0.0)
        self.assertAlmostEqual(correlation_p_value(0.0, 10) or 0, 1.0)
        self.assertIsNone(correlation_p_value(0.9, 2))
        self.assertIsNone(correlation_p_value(None, 10))

    def test_alignment_metrics_report_p_values(self):
        puzzles = [puzzle(str(i), "D1", 3.5 + i / 10, [4 + i % 3, 4]) for i in range(1, 9)]
        result = alignment_metrics(puzzles, CUTS)
        self.assertAlmostEqual(
            result["spearman_p"], correlation_p_value(result["spearman"], 8) or 0
        )
        self.assertAlmostEqual(
            result["pearson_p"], correlation_p_value(result["pearson"], 8) or 0
        )

    def test_rank_quartiles_ignore_the_scale(self):
        # The system is two guesses worse but keeps the human order.
        puzzles = [
            puzzle("1", "D1", 3.8, [6, 6]),
            puzzle("2", "D2", 4.1, [7, 7]),
            puzzle("3", "D3", 4.4, [8, 8]),
            puzzle("4", "D4", 4.9, [9, 9]),
        ]
        result = alignment_metrics(puzzles, CUTS)

        self.assertEqual(result["quartile_exact"], 0.25)  # by value everything is D4
        self.assertEqual(result["rank_quartile_exact"], 1.0)
        self.assertAlmostEqual(result["rank_quadratic_weighted_kappa"] or 0, 1.0)
        self.assertAlmostEqual(result["spearman"] or 0, 1.0)
        self.assertAlmostEqual(result["kendall_tau_b"] or 0, 1.0)

    def test_rank_quartiles_need_four_puzzles(self):
        result = alignment_metrics([puzzle(str(i), "D1", 4.0 + i / 10, [4 + i]) for i in range(3)], CUTS)

        self.assertIsNone(result["rank_quartile_exact"])
        self.assertIsNotNone(result["spearman"])

    def test_puzzles_without_completed_runs_are_left_out(self):
        result = alignment_metrics([puzzle("1", "D1", 3.8, []), puzzle("2", "D2", 4.1, [4])], CUTS)

        self.assertEqual(result["puzzles"], 1)


class GuessLimitTests(unittest.TestCase):
    def test_cap_scores(self):
        # Wins at 3, 7 and 9, and a loss at the 12-guess limit (13).
        raw = puzzle("1", "D2", 4.1, [3, 7, 9, 13], loss=13)
        six = cap_scores(raw, 6)
        eight = cap_scores(raw, 8)

        self.assertEqual(six.scores, (3, 7, 7, 7))
        self.assertEqual((six.wins, six.losses), (1, 3))
        self.assertEqual(eight.scores, (3, 7, 9, 9))
        self.assertEqual((eight.wins, eight.losses), (2, 2))

    def test_missing_as_loss(self):
        raw = replace(puzzle("1", "D2", 4.1, [3, 9], loss=13), planned_runs=3)
        filled = missing_as_loss(raw, 12)

        self.assertEqual(filled.scores, (3, 9, 13))
        self.assertEqual(filled.losses, 1)
        self.assertEqual(missing_as_loss(filled, 12), filled)  # nothing missing

    def experiment(self, max_guesses: int, scores: list[float]) -> Experiment:
        config = {"settings": {"repetitions": len(scores), "max_guesses": max_guesses}}
        bins = (0.0, 0.0, 0.25, 0.25, 0.25, 0.25, 0.0)
        puzzles = tuple(
            puzzle(str(i), q, 4.0 + i / 10, scores, loss=max_guesses + 1, human_bins=bins)
            for i, q in enumerate(QUARTILE_LABELS_FOR_TEST)
        )
        return Experiment("deep", Path("deep"), config, puzzles, 4 * len(scores), {"fp": 1})

    def test_capped_block_only_for_longer_games(self):
        long_games = experiment_block(self.experiment(12, [4, 9, 13]), CUTS, seed=1, resamples=20)
        standard = experiment_block(self.experiment(6, [4, 5, 7]), CUTS, seed=1, resamples=20)

        self.assertEqual(long_games["max_guesses"], 12)
        self.assertEqual(sorted(long_games["capped"]), ["6_guesses", "8_guesses"])
        self.assertEqual(sorted(long_games["missing_as_loss"]), ["6_guesses", "8_guesses", "raw"])
        self.assertAlmostEqual(long_games["rq1"]["win_rate"], 2 / 3)
        self.assertAlmostEqual(long_games["capped"]["6_guesses"]["rq1"]["win_rate"], 1 / 3)
        self.assertEqual(standard["capped"], {})

    def test_distribution_reads_six_guess_scores(self):
        experiment = self.experiment(12, [4, 9, 13])

        with self.assertRaises(ValueError):
            distribution_rows(experiment, seed=1, resamples=10)  # 9 and 13 are no bins
        rows = distribution_rows(capped(experiment, 6), seed=1, resamples=10)
        self.assertAlmostEqual(rows[0]["system_p7"], 2 / 3)


class BootstrapTests(unittest.TestCase):
    def test_resamples_keep_each_quartile_size(self):
        puzzles = [puzzle(str(i), q, 4.0, [4]) for i, q in enumerate(["D1", "D1", "D1", "D2", "D4"])]

        def per_quartile(sample):
            return {"d1_share": sum(p.human_quartile == "D1" for p in sample) / len(sample)}

        result = stratified_bootstrap(puzzles, per_quartile, ["d1_share"], seed=1, resamples=200)

        self.assertEqual(result["d1_share"]["ci_low"], 0.6)
        self.assertEqual(result["d1_share"]["ci_high"], 0.6)

    def test_seeded_and_bracketing_the_point(self):
        puzzles = [puzzle(str(i), "D2", 4.1, [3 + i % 3, 4, 5]) for i in range(8)]
        first = stratified_bootstrap(puzzles, consistency_metrics, ["mean_within_sd"], seed=7, resamples=300)
        again = stratified_bootstrap(puzzles, consistency_metrics, ["mean_within_sd"], seed=7, resamples=300)
        value = first["mean_within_sd"]

        self.assertEqual(first, again)
        self.assertLessEqual(value["ci_low"], value["point"])
        self.assertGreaterEqual(value["ci_high"], value["point"])


class PoolingTests(unittest.TestCase):
    def experiment(self, name: str, fingerprints=None, **settings) -> Experiment:
        config = {
            "code_revision": "abc",
            "source_sha256": "s",
            "dataset_sha256": "d",
            "guess_list_sha256": "g",
            "settings": {"model": "deepseek-flash", "temperature": 0.2, "repetitions": 3, **settings},
        }
        return Experiment(name, Path(name), config, (), 0, fingerprints or {"fp1": 10})

    def test_identical_configurations_pool(self):
        self.assertEqual(pooling_blockers([self.experiment("deep", repetitions=32), self.experiment("wide")]), [])

    def test_unanswered_calls_carry_no_fingerprint(self):
        calls = [
            {"system_fingerprint": "fp1"},
            {"system_fingerprint": None, "error_type": "APITimeoutError"},  # no reply
            {"system_fingerprint": None, "error_type": None},  # a reply without one
        ]
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "run.json").write_text(json.dumps({"calls": calls}), encoding="utf-8")
            self.assertEqual(load_fingerprints(Path(tmp)), {"fp1": 1, "unknown": 1})

    def test_changed_setting_or_fingerprint_blocks_pooling(self):
        self.assertEqual(
            pooling_blockers([self.experiment("deep", temperature=1.0), self.experiment("wide")]),
            ["settings.temperature differs"],
        )
        blockers = pooling_blockers([self.experiment("deep", {"fp1": 5, "fp2": 5}), self.experiment("wide")])
        self.assertEqual(len(blockers), 1)
        self.assertIn("fingerprints", blockers[0])


@unittest.skipUnless(DATASET.exists() and GUESSES.exists() and QUARTILES.exists(), "data not present")
class EndToEndTest(unittest.TestCase):
    """Runner output (scripted backend) feeds the analysis unchanged."""

    def run_experiment(self, directory: Path, repetitions: int) -> None:
        manifest = directory.parent / f"{directory.name}-manifest.csv"
        manifest.write_text(
            "puzzle_id,answer,human_mean_score,quartile,p1,p2,p3,p4,p5,p6,p7\n"
            "0,CIGAR,4.16,D2,0.0,0.03,0.23,0.4,0.25,0.07,0.02\n",
            encoding="utf-8",
        )
        backend = ScriptedBackend(response='{"action": "CIGAR", "reason": "scripted", "stop": false}')
        argv = [
            "runner", "start",
            "--experiment-dir", str(directory),
            "--manifest", str(manifest),
            "--dataset", str(DATASET),
            "--guess-list", str(GUESSES),
            "--backend", "ollama", "--model", "scripted",
            "--base-url", "http://localhost:11434/v1",
            "--temperature", "0.2", "--max-rounds", "1",
            "--repetitions", str(repetitions),
            "--persona-preset", "pilot-02",
        ]
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(runner, "build_backend", return_value=backend),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            runner.main()

    def test_deep_and_wide_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_experiment(root / "deep", repetitions=3)
            self.run_experiment(root / "wide", repetitions=2)
            output = root / "analysis"

            # Lower the run threshold so the 3-run deep experiment gets the
            # distribution comparison that 32-run Exp A will get.
            with (
                contextlib.redirect_stdout(io.StringIO()),
                mock.patch.object(analysis, "MIN_RUNS_FOR_DISTRIBUTION", 3),
            ):
                analysis.main([
                    "--deep", str(root / "deep"),
                    "--wide", str(root / "wide"),
                    "--quartiles", str(QUARTILES),
                    "--output-dir", str(output),
                    "--resamples", "50",
                ])

            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            deep = metrics["experiments"]["deep"]
            self.assertEqual(deep["rq1"]["completed_runs"], 3)
            self.assertEqual(deep["rq1"]["win_rate"], 1.0)
            self.assertEqual(deep["rq1"]["exact_match_rate"], 1.0)  # every run wins in 1
            self.assertEqual(deep["rq2"]["confusion_matrix"]["counts"]["D2"]["D1"], 1)
            self.assertEqual(metrics["pooling_blockers"], [])  # same settings apart from repetitions
            self.assertIsNotNone(metrics["pooled"])

            rows = (output / "puzzle_summary.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows), 3)  # header plus one puzzle per experiment
            self.assertIn("deep,0,CIGAR,D2,4.16", rows[1])

            # Every run solves in 1, so W1 equals the whole mean gap: 4.16 - 1.
            self.assertAlmostEqual(deep["distribution"]["mean_w1"], 3.16)
            self.assertIsNone(metrics["experiments"]["wide"]["distribution"])
            distribution = (output / "distribution_summary.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(distribution), 2)  # deep only

            self.assertEqual(deep["personas"]["games"], 3)
            self.assertEqual(deep["personas"]["gm_retention_rate"], 1.0)
            openers = (output / "openers.csv").read_text(encoding="utf-8").splitlines()
            self.assertIn("deep,1,all,CIGAR,gm,3", openers)
            runs = (output / "runs.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(runs), 1 + 3 + 2)  # header plus every attempt
            self.assertIn("deep,0,D2,1,1,completed,,True,1,1.0,1.0", runs[1])
            personas = (output / "persona_stats.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(personas), 1 + 2 * 4)  # GM plus 3 advisors, per experiment


if __name__ == "__main__":
    unittest.main()
