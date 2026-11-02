import math
import unittest

from ..experiment.nonparametric import friedman, wilcoxon_signed_rank

# Reference values from scipy 1.x: wilcoxon(d, zero_method="wilcox",
# correction=False, method="approx") and friedmanchisquare(a, b, c).
DIFFERENCES = [1.5, -0.5, 2, 2, 0, -1, 3, 0.5, 0.5, 4]
A = [0.1, 0.2, 0.2, 0.5, 0.0, 0.3]
B = [0.3, 0.2, 0.4, 0.6, 0.1, 0.3]
C = [0.2, 0.5, 0.1, 0.9, 0.1, 0.0]


class WilcoxonTest(unittest.TestCase):
    def test_matches_scipy(self):
        result = wilcoxon_signed_rank(DIFFERENCES)
        self.assertEqual((result["pairs"], result["n"], result["zeros_dropped"]), (10, 9, 1))
        self.assertEqual(result["w_plus"], 39.0)  # n(n+1)/2 = 45, so W- = 6 as in scipy
        self.assertAlmostEqual(result["p_value"], 0.04960185169639382, places=12)
        self.assertAlmostEqual(result["mean_difference"], 1.2)

    def test_sign_does_not_change_p(self):
        flipped = wilcoxon_signed_rank([-d for d in DIFFERENCES])
        self.assertAlmostEqual(flipped["p_value"], wilcoxon_signed_rank(DIFFERENCES)["p_value"])
        self.assertLess(flipped["z"], 0)

    def test_all_positive_textbook_case(self):
        result = wilcoxon_signed_rank([1, 2, 3, 4, 5])
        self.assertAlmostEqual(result["z"], 7.5 / math.sqrt(13.75))

    def test_all_zero_or_empty(self):
        self.assertIsNone(wilcoxon_signed_rank([0, 0, 0])["p_value"])
        self.assertIsNone(wilcoxon_signed_rank([])["mean_difference"])


class FriedmanTest(unittest.TestCase):
    def test_matches_scipy(self):
        result = friedman([list(row) for row in zip(A, B, C)], ("a", "b", "c"))
        self.assertEqual((result["n"], result["df"]), (6, 2))
        self.assertAlmostEqual(result["statistic"], 2.9523809523809468, places=10)
        self.assertAlmostEqual(result["p_value"], 0.22850653346992042, places=10)

    def test_perfect_ordering(self):
        result = friedman([[1, 2, 3]] * 3, ("x", "y", "z"))
        self.assertAlmostEqual(result["statistic"], 6.0)
        self.assertAlmostEqual(result["p_value"], math.exp(-3))
        self.assertEqual(result["mean_ranks"], {"x": 1.0, "y": 2.0, "z": 3.0})

    def test_all_tied_blocks(self):
        result = friedman([[0.5, 0.5]] * 4, ("x", "y"))
        self.assertEqual((result["statistic"], result["p_value"]), (0.0, 1.0))

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            friedman([[1.0]], ("x",))
        with self.assertRaises(ValueError):
            friedman([[1.0, 2.0, 3.0]], ("x", "y"))
        self.assertIsNone(friedman([], ("x", "y"))["p_value"])


if __name__ == "__main__":
    unittest.main()
