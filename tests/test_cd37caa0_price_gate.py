"""Release-gate regression for non-actionable two-sided decimal prices."""
import math
import unittest

from scripts.domain import no_vig


class ActionablePriceBoundaryTests(unittest.TestCase):
    def test_observed_thunderpick_quote_is_rejected_before_normalization(self):
        # Retained 2026-10-24 candidate evidence for Hotspawn 1082860.
        with self.assertRaisesRegex(ValueError, 'greater than 1.01'):
            no_vig([1.001, 12.0])

    def test_either_leg_at_or_below_the_boundary_is_rejected(self):
        for odds in ([1.01, 25.0], [25.0, 1.01], [1.0, 12.0], [0.5, 2.0]):
            with self.subTest(odds=odds), self.assertRaises(ValueError):
                no_vig(odds)

    def test_valid_pair_immediately_above_boundary_still_replays(self):
        probabilities = no_vig([1.02, 25.0])
        raw = [1 / 1.02, 1 / 25.0]
        expected = [value / sum(raw) for value in raw]
        self.assertTrue(math.isclose(sum(probabilities), 1.0, abs_tol=1e-12))
        for actual, wanted in zip(probabilities, expected):
            # The public contract normalizes to eight decimal places.
            self.assertTrue(math.isclose(actual, wanted, rel_tol=0, abs_tol=5e-9))

    def test_non_finite_or_malformed_pairs_remain_fail_closed(self):
        for odds in ([float('nan'), 2.0], [float('inf'), 2.0], [2.0, float('-inf')], [2.0], [2.0, 3.0, 4.0]):
            with self.subTest(odds=odds), self.assertRaises(ValueError):
                no_vig(odds)


if __name__ == '__main__':
    unittest.main()
