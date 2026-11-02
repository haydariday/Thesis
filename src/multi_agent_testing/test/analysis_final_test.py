import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path
from unittest import mock

from ..agent.backend import ScriptedBackend
from ..experiment import analysis_final as af
from ..experiment import runner
from ..experiment.analysis_pilot02 import Experiment, PuzzleRuns

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET = REPO_ROOT / "src" / "data" / "raw" / "worldepuzzles.json"
GUESSES = REPO_ROOT / "src" / "data" / "raw" / "allowed_guesses.txt"
QUARTILES = REPO_ROOT / "src" / "data" / "processed" / "quartiles.json"
QUARTILE_CUTS = [3.98, 4.24, 4.53]

# Reference values from scipy.stats.f.ppf and the Shrout-Fleiss formulas.
ICC_GROUPS = [[3, 4, 4, 5], [5, 6, 5, 7], [2, 3, 3, 3], [4, 4, 6, 5], [6, 7, 7, 6]]


def puzzle(pid: str, human: float, scores: Sequence[float], quartile: str = "D2") -> PuzzleRuns:
    return PuzzleRuns(
        experiment="test",
        puzzle_id=pid,
        answer="",
        human_quartile=quartile,
        human_mean=human,
        human_mean_low=None,
        human_mean_high=None,
        planned_runs=len(scores),
        scores=tuple(float(s) for s in scores),
        wins=sum(1 for s in scores if s < 7),
        losses=sum(1 for s in scores if s == 7),
        failed_attempts=0,
    )


def condition(name: str, puzzles: list[PuzzleRuns], config: dict | None = None) -> af.Condition:
    experiment = Experiment(
        name=name,
        directory=Path("/nonexistent"),
        config=config or {"settings": {"max_guesses": 6}},
        puzzles=tuple(puzzles),
        attempts=sum(len(p.scores) for p in puzzles),
        fingerprints={},
    )
    return af.Condition(name, name, experiment, {})


class IccIntervalTest(unittest.TestCase):
    def test_f_quantile_matches_scipy(self):
        self.assertAlmostEqual(af.f_quantile(0.975, 4, 20), 3.51469516225841, places=8)
        self.assertAlmostEqual(af.f_quantile(0.975, 20, 4), 8.55994318705354, places=7)
        self.assertAlmostEqual(af.f_quantile(0.975, 99, 900), 1.3195349081059529, places=8)

    def test_interval_matches_reference(self):
        result = af.icc_interval(ICC_GROUPS)
        expected = {
            "f": 13.986486486486486,
            "icc_1_1": 0.7645186953062849,
            "icc_1_1_low": 0.4008856519427,
            "icc_1_1_high": 0.9677613296862438,
            "icc_1_k": 0.9285024154589372,
            "icc_1_k_low": 0.7280037881195803,
            "icc_1_k_high": 0.991740629069234,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(result[key] or 0.0, value, places=7, msg=key)

    def test_point_matches_pilot_icc(self):
        rq1 = af.rq1_metrics([puzzle(str(i), 4.0, g) for i, g in enumerate(ICC_GROUPS)])
        self.assertAlmostEqual(rq1["icc_1_1"], 0.7645186953062849)
        self.assertLess(rq1["icc_1_1_low"], rq1["icc_1_1"])

    def test_undefined_cases(self):
        self.assertIsNone(af.icc_interval([[4, 4], [4, 4]])["icc_1_1"])
        self.assertIsNone(af.icc_interval([[3, 4]])["icc_1_1_low"])


class HolmTest(unittest.TestCase):
    def test_step_down(self):
        self.assertEqual(af.holm([0.01, 0.04]), [0.02, 0.04])
        self.assertEqual(af.holm([0.04, 0.01]), [0.04, 0.02])
        self.assertEqual(af.holm([0.03, 0.02]), [0.04, 0.04])  # monotone
        self.assertEqual(af.holm([0.6, None]), [0.6, None])
        self.assertEqual(af.holm([0.7, 0.8]), [1.0, 1.0])


class Rq2Test(unittest.TestCase):
    def test_terciles_errors_and_baselines(self):
        # Six puzzles, system = human + 1 except one swap at the top.
        humans = [3.6, 3.9, 4.1, 4.3, 4.6, 5.0]
        systems = [4.6, 4.9, 5.1, 5.3, 6.0, 5.6]
        puzzles = [puzzle(str(i), h, [s, s]) for i, (h, s) in enumerate(zip(humans, systems))]
        terciles = {"0": "T1", "1": "T1", "2": "T2", "3": "T2", "4": "T3", "5": "T3"}
        rq2 = af.rq2_metrics(puzzles, terciles, QUARTILE_CUTS)

        self.assertAlmostEqual(rq2["signed_error"], 1.0)
        self.assertAlmostEqual(rq2["mae"], 1.0)
        self.assertAlmostEqual(rq2["bias_corrected_mae"], (0.4 + 0.4) / 6)
        self.assertAlmostEqual(rq2["constant_baseline_mae"], sum(abs(h - 25.5 / 6) for h in humans) / 6)
        self.assertEqual((rq2["tercile_exact"], rq2["tercile_adjacent"]), (1.0, 1.0))
        self.assertAlmostEqual(rq2["spearman"], 1 - 6 * 2 / (6 * 35))
        self.assertIsNotNone(rq2["spearman_p"])
        self.assertIsNotNone(rq2["quartile_sensitivity"]["rank_quartile_exact"])

    def test_tercile_distribution_pools_runs(self):
        p = replace_bins(puzzle("0", 4.0, [3, 4]), (0, 0, 0.5, 0.5, 0, 0, 0))
        result = af.tercile_distributions([p], {"0": "T1"})
        self.assertEqual(result["T1"]["runs"], 2)
        self.assertAlmostEqual(result["T1"]["w1"], 0.0)
        self.assertIsNone(result["T2"])


def replace_bins(p: PuzzleRuns, bins: tuple) -> PuzzleRuns:
    from dataclasses import replace

    return replace(p, human_bins=tuple(float(b) for b in bins))


class ContrastTest(unittest.TestCase):
    def test_paired_wilcoxon_and_holm(self):
        humans = [3.5 + 0.1 * i for i in range(12)]
        c2 = [puzzle(str(i), h, [h + 2, h + 2.5]) for i, h in enumerate(humans)]
        c3 = [puzzle(str(i), h, [h + 1, h + 1.5]) for i, h in enumerate(humans)]
        c1 = [puzzle(str(i), h, [h + 1, h + 1.5]) for i, h in enumerate(humans)]
        rows = af.contrast_rows({"c1": condition("c1", c1), "c2": condition("c2", c2), "c3": condition("c3", c3)})
        by_key = {(r["contrast"], r["measure"]): r for r in rows}

        debate = by_key[("debate_effect", "abs_error")]
        self.assertEqual((debate["pairs"], debate["n"]), (12, 12))
        self.assertAlmostEqual(debate["mean_difference"], -1.0)
        self.assertLess(debate["p_value"], 0.01)
        # Persona effect: identical scores, every difference is zero.
        persona = by_key[("persona_effect", "abs_error")]
        self.assertEqual(persona["n"], 0)
        self.assertIsNone(persona["p_value"])
        self.assertAlmostEqual(debate["p_holm"], debate["p_value"])  # only one test left to correct
        overall = by_key[("overall", "abs_error")]
        self.assertFalse(overall["tested"])
        self.assertIsNone(overall["p_value"])
        self.assertAlmostEqual(by_key[("debate_effect", "within_sd")]["mean_difference"], 0.0)

    def test_unpaired_puzzles_are_left_out(self):
        a = condition("c1", [puzzle("1", 4.0, [5, 5]), puzzle("2", 4.0, [6, 6])])
        b = condition("c2", [puzzle("1", 4.0, [4, 4])])
        rows = af.contrast_rows({"c1": a, "c2": b, "c3": b})
        overall = next(r for r in rows if r["contrast"] == "overall" and r["measure"] == "signed_error")
        self.assertEqual(overall["pairs"], 1)


class PersonaCheckTest(unittest.TestCase):
    def stats(self, c1_p, c1_diff, c3_p):
        return {
            "c1": {"cautious_vs_bold": {"p_value": c1_p, "mean_difference": c1_diff}},
            "c3": {"advisor_difference": {"p_value": c3_p}},
        }

    def test_outcomes(self):
        self.assertTrue(af.persona_check(self.stats(0.001, 0.2, 0.4))["personas_work"])
        self.assertFalse(af.persona_check(self.stats(0.001, 0.2, 0.01))["personas_work"])
        self.assertFalse(af.persona_check(self.stats(0.001, -0.2, 0.4))["personas_work"])
        self.assertFalse(af.persona_check(self.stats(0.2, 0.2, 0.4))["personas_work"])
        self.assertIsNone(af.persona_check(self.stats(None, None, 0.4))["personas_work"])


class ConfigCheckTest(unittest.TestCase):
    BASE = {
        "experiment_id": "a", "code_revision": "x", "code_dirty": False, "manifest_sha256": "m",
        "settings": {"max_guesses": 6, "max_rounds": 3, "personas": {"preset": "pilot-02"}},
    }

    def check(self, **changes):
        other = json.loads(json.dumps(self.BASE))
        for key, value in changes.items():
            if key.startswith("settings."):
                other["settings"][key.split(".", 1)[1]] = value
            else:
                other[key] = value
        return af.config_mismatches([condition("c1", [], self.BASE), condition("c2", [], other)])

    def test_personas_and_ids_may_differ(self):
        self.assertEqual(self.check(experiment_id="b", **{"settings.personas": {"preset": "solo"}}), [])

    def test_other_differences_refuse(self):
        self.assertEqual(self.check(code_revision="y"), ["c2: code_revision differs from c1"])
        self.assertEqual(self.check(**{"settings.max_rounds": 1}), ["c2: settings.max_rounds differs from c1"])
        self.assertIn("c2: ran from a dirty tree", self.check(code_dirty=True))


class EndToEndTest(unittest.TestCase):
    """Runner output for all three presets (scripted backend) feeds the analysis."""

    def run_condition(self, directory: Path, manifest: Path, preset: str) -> None:
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
            "--repetitions", "3",
            "--persona-preset", preset,
        ]
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(runner, "build_backend", return_value=backend),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            runner.main()
        # The test may run from a dirty working tree; the analysis refuses
        # dirty runs, so mark these scripted runs as clean.
        config_path = directory / "experiment_config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["code_dirty"] = False
        config_path.write_text(json.dumps(config), encoding="utf-8")

    def test_three_conditions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.csv"
            manifest.write_text(
                "puzzle_id,answer,human_mean_score,quartile,tercile,p1,p2,p3,p4,p5,p6,p7\n"
                "0,CIGAR,4.16,D2,T2,0.0,0.03,0.23,0.4,0.25,0.07,0.02\n",
                encoding="utf-8",
            )
            for name, preset in (("c1", "pilot-02"), ("c2", "solo"), ("c3", "neutral")):
                self.run_condition(root / name, manifest, preset)
            output = root / "analysis"
            with contextlib.redirect_stdout(io.StringIO()):
                af.main([
                    "--c1", str(root / "c1"), "--c2", str(root / "c2"), "--c3", str(root / "c3"),
                    "--quartiles", str(QUARTILES), "--output-dir", str(output),
                ])

            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            for name in ("c1", "c2", "c3"):
                block = metrics["conditions"][name]
                self.assertEqual(block["rq1"]["completed_runs"], 3, name)
                self.assertEqual(block["rq1"]["win_rate"], 1.0, name)
                self.assertEqual(block["rq2"]["signed_error"], 1 - 4.16, name)
            self.assertEqual(metrics["conditions"]["c2"]["cost"]["mean_calls"], 1.0)
            self.assertEqual(metrics["conditions"]["c1"]["cost"]["mean_calls"], 5.0)
            self.assertTrue(metrics["conditions"]["c2"]["rq3"]["solo"])
            self.assertEqual(metrics["conditions"]["c3"]["rq3"]["advisor_difference"]["treatments"],
                             ["neutral_1", "neutral_2", "neutral_3"])
            self.assertEqual(
                metrics["conditions"]["c1"]["sensitivity"]["tercile_distributions"]["T2"]["runs"], 3
            )

            with (output / "condition_summary.csv").open(encoding="utf-8", newline="") as file:
                summary = list(csv.DictReader(file))
            self.assertEqual([row["condition"] for row in summary], ["c1", "c2", "c3"])
            contrasts = (output / "contrasts.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(contrasts), 1 + 3 * 3)
            personas = (output / "persona_stats.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(personas), 1 + 4 + 1 + 4)  # GM + 3 advisors, GM only, GM + 3
            runs = (output / "runs.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(runs), 1 + 9)

    def test_refuses_a_changed_setting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.csv"
            manifest.write_text(
                "puzzle_id,answer,human_mean_score,quartile,tercile\n0,CIGAR,4.16,D2,T2\n",
                encoding="utf-8",
            )
            for name in ("c1", "c2", "c3"):
                self.run_condition(root / name, manifest, "solo")
            config_path = root / "c3" / "experiment_config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["settings"]["max_rounds"] = 2
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                af.main([
                    "--c1", str(root / "c1"), "--c2", str(root / "c2"), "--c3", str(root / "c3"),
                    "--quartiles", str(QUARTILES), "--output-dir", str(root / "out"),
                ])


if __name__ == "__main__":
    unittest.main()
