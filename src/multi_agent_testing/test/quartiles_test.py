import unittest

from ..experiment.quartiles import QUARTILE_LABELS, RankedPuzzle, assign_quartiles, map_score, rank_split


def _puzzles(means):
    return [RankedPuzzle(str(i), m) for i, m in enumerate(means)]


class AssignQuartilesTest(unittest.TestCase):
    def test_equal_sizes_and_order(self):
        labels, spec = assign_quartiles(_puzzles([float(i) for i in range(8)]))
        self.assertEqual(spec.sizes, (2, 2, 2, 2))
        self.assertEqual([labels[str(i)] for i in range(8)],
                         ["D1", "D1", "D2", "D2", "D3", "D3", "D4", "D4"])
        self.assertEqual(spec.cut_points, (2.0, 4.0, 6.0))
        self.assertEqual(spec.boundary_ties, (0, 0, 0))

    def test_sizes_differ_by_at_most_one(self):
        for n in range(4, 30):
            _, spec = assign_quartiles(_puzzles([i / 10 for i in range(n)]))
            self.assertEqual(sum(spec.sizes), n)
            self.assertLessEqual(max(spec.sizes) - min(spec.sizes), 1)

    def test_ties_broken_by_puzzle_id(self):
        # Six puzzles share 4.0; the rank split must still give equal groups.
        means = [3.0, 3.5, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0]
        labels, spec = assign_quartiles(_puzzles(means))
        self.assertEqual(spec.sizes, (2, 2, 2, 2))
        self.assertEqual(labels["2"], "D2")  # lower id among the tied values
        self.assertEqual(labels["7"], "D4")
        self.assertEqual(spec.cut_points, (4.0, 4.0, 4.0))
        self.assertEqual(spec.boundary_ties, (0, 2, 2))

    def test_input_order_does_not_matter(self):
        puzzles = _puzzles([5.0, 3.0, 4.5, 3.9, 4.1, 6.2, 3.3, 4.4])
        a, _ = assign_quartiles(puzzles)
        b, _ = assign_quartiles(list(reversed(puzzles)))
        self.assertEqual(a, b)

    def test_rejects_small_or_duplicate_input(self):
        with self.assertRaises(ValueError):
            assign_quartiles(_puzzles([1.0, 2.0, 3.0]))
        with self.assertRaises(ValueError):
            assign_quartiles([RankedPuzzle("1", 1.0)] * 4)


class MapScoreTest(unittest.TestCase):
    CUTS = (3.98, 4.24, 4.53)

    def test_boundaries(self):
        self.assertEqual(map_score(3.0, self.CUTS), "D1")
        self.assertEqual(map_score(3.9799, self.CUTS), "D1")
        self.assertEqual(map_score(3.98, self.CUTS), "D2")
        self.assertEqual(map_score(4.24, self.CUTS), "D3")
        self.assertEqual(map_score(4.53, self.CUTS), "D4")
        self.assertEqual(map_score(7.0, self.CUTS), "D4")

    def test_labels(self):
        self.assertEqual(QUARTILE_LABELS, ("D1", "D2", "D3", "D4"))

    def test_rejects_bad_cuts(self):
        with self.assertRaises(ValueError):
            map_score(4.0, (4.0, 3.0, 5.0))
        with self.assertRaises(ValueError):
            map_score(4.0, (4.0, 5.0))


class RankSplitTest(unittest.TestCase):
    def test_matches_assign_quartiles(self):
        means = [4.3, 3.9, 5.0, 4.1, 4.6, 3.7, 4.4, 4.0, 4.8]
        labels, _ = assign_quartiles(_puzzles(means))
        self.assertEqual(rank_split(means, list(range(len(means)))),
                         [labels[str(i)] for i in range(len(means))])

    def test_scale_free(self):
        # A system two guesses worse in the same order gets the same labels.
        means = [3.8, 4.0, 4.2, 4.6]
        self.assertEqual(rank_split([m + 2 for m in means], [1, 2, 3, 4]), ["D1", "D2", "D3", "D4"])

    def test_ties_by_key_then_position(self):
        # Equal values: tie key 9 ranks after key 1; the repeated key 5 keeps
        # its input order, as in a bootstrap sample that draws a puzzle twice.
        self.assertEqual(rank_split([4.0, 4.0, 3.0, 3.0], [9, 1, 5, 5]), ["D4", "D3", "D1", "D2"])

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            rank_split([1.0, 2.0, 3.0], [1, 2, 3])
        with self.assertRaises(ValueError):
            rank_split([1.0, 2.0, 3.0, 4.0], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
