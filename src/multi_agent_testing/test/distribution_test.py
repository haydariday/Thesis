import unittest

from ..experiment.distribution import (
    chi_square_gof,
    chi_square_sf,
    jensen_shannon,
    merge_sparse_bins,
    score_distribution,
    split_half_w1,
    total_variation,
    wasserstein_1,
)

# Puzzle 234 (FRAME) human shares, bins 1..6 and fail.
FRAME = [0.0, 0.05, 0.18, 0.29, 0.30, 0.15, 0.03]


class DistanceTests(unittest.TestCase):
    def test_w1_worked_examples(self):
        self.assertAlmostEqual(wasserstein_1(score_distribution([5, 5, 5]), FRAME), 1.01)
        self.assertAlmostEqual(wasserstein_1(score_distribution([5, 4, 5]), FRAME), 0.6767, places=4)
        # The same shape one guess sooner is exactly one guess away.
        sooner = FRAME[1:] + [0.0]
        self.assertAlmostEqual(wasserstein_1(sooner, FRAME), 1.0)
        self.assertEqual(wasserstein_1(FRAME, FRAME), 0.0)

    def test_w1_respects_order_while_tvd_and_jsd_do_not(self):
        three = score_distribution([3])
        four = score_distribution([4])
        fail = score_distribution([7])

        self.assertAlmostEqual(wasserstein_1(three, four), 1.0)
        self.assertAlmostEqual(wasserstein_1(three, fail), 4.0)
        self.assertEqual(total_variation(three, four), total_variation(three, fail))
        self.assertAlmostEqual(jensen_shannon(three, four), jensen_shannon(three, fail))

    def test_jsd_bounds(self):
        self.assertEqual(jensen_shannon(FRAME, FRAME), 0.0)
        self.assertAlmostEqual(jensen_shannon(score_distribution([2]), score_distribution([6])), 1.0)

    def test_scores_must_be_whole_bins(self):
        for bad in ([0], [8], [4.5], []):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                score_distribution(bad)


class ChiSquareTests(unittest.TestCase):
    def test_upper_tail_matches_table_values(self):
        for statistic, df in [(3.841, 1), (5.991, 2), (9.488, 4), (18.307, 10)]:
            with self.subTest(df=df):
                self.assertAlmostEqual(chi_square_sf(statistic, df), 0.05, places=3)
        self.assertAlmostEqual(chi_square_sf(2.0, 2), 0.36788, places=4)  # exp(-1)
        self.assertEqual(chi_square_sf(0.0, 3), 1.0)

    def test_sparse_bins_are_merged(self):
        observed, expected = merge_sparse_bins([1, 2, 3, 10, 10, 4, 2], [0, 2, 6, 9, 10, 5, 0])

        self.assertEqual(expected, [8, 9, 10, 5])
        self.assertEqual(observed, [6, 10, 10, 6])
        self.assertEqual(sum(observed), 32)

    def test_gof_on_32_runs(self):
        scores = [3] * 6 + [4] * 9 + [5] * 10 + [6] * 5 + [7] * 2
        result = chi_square_gof(scores, FRAME)

        self.assertGreaterEqual(result["merged_bins"] or 0, 3)
        self.assertEqual(result["df"], (result["merged_bins"] or 0) - 1)
        self.assertGreater(result["p_value"] or 0, 0.05)  # close to the human shape
        far = chi_square_gof([2] * 32, FRAME)
        self.assertIsNotNone(far["p_value"])
        self.assertLess(far["p_value"], 0.001)  # type: ignore[operator]


class SplitHalfTests(unittest.TestCase):
    def test_identical_runs_have_no_split_difference(self):
        result = split_half_w1([4] * 32, seed=1)

        self.assertEqual(result["observed"], 0.0)
        self.assertEqual(result["random_mean"], 0.0)

    def test_drift_stands_out_against_random_splits(self):
        result = split_half_w1([3] * 16 + [5] * 16, seed=1)

        self.assertEqual(result["observed"], 2.0)
        self.assertLess(result["random_mean"] or 0, 1.0)
        self.assertEqual(result["random_share_above"], 0.0)
        self.assertEqual(result, split_half_w1([3] * 16 + [5] * 16, seed=1))


if __name__ == "__main__":
    unittest.main()
