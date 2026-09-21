"""Tests for the rules that leave a map out (pipeline/rules.py).

Run from the project root:   python3 -m unittest discover -s pipeline/tests -t .
"""
import unittest

import numpy as np

from pipeline import config, rules

GLASGOW = (259000, 665000)
LONDON = (530000, 180000)
PERIODS = {p["id"]: p for p in config.PERIODS}


def cells(*places):
    """Bearers as (cell x, cell y, n) from a list of ((easting, northing), n)."""
    g = config.GRID
    return (np.array([int((x - g["x0"]) // g["cell"]) for (x, y), n in places]),
            np.array([int((y - g["y0"]) // g["cell"]) for (x, y), n in places]),
            np.array([float(n) for (x, y), n in places]))


class ScotlandRule(unittest.TestCase):
    def test_share_of_bearers_in_scotland(self):
        self.assertAlmostEqual(rules.scotland_share(cells((GLASGOW, 60), (LONDON, 40))), 0.6)
        self.assertEqual(rules.scotland_share(cells((LONDON, 500))), 0.0)

    def test_a_scottish_name_gets_no_1911_map_even_with_plenty_of_bearers(self):
        # 1911 has 900 bearers (the Scots who moved south), but 70% of the name was Scottish in 1901
        by_period = {"1901": cells((GLASGOW, 700), (LONDON, 300)), "1911": cells((LONDON, 900))}
        reason = rules.skip_reason(PERIODS["1911"], by_period)
        self.assertIsNotNone(reason)
        self.assertIn("70%", reason)

    def test_an_english_name_keeps_its_1911_map(self):
        by_period = {"1901": cells((GLASGOW, 50), (LONDON, 950)), "1911": cells((LONDON, 900))}
        self.assertIsNone(rules.skip_reason(PERIODS["1911"], by_period))

    def test_only_the_years_without_scotland_are_checked(self):
        scottish = {"1901": cells((GLASGOW, 900)), "1921": cells((GLASGOW, 900))}
        self.assertIsNone(rules.skip_reason(PERIODS["1921"], scottish))      # 1921 is assumed to include Scotland
        self.assertIsNone(rules.skip_reason(PERIODS["1901"], scottish))

    def test_the_threshold_comes_first(self):
        by_period = {"2020": cells((LONDON, 99))}
        self.assertIn("99 bearers", rules.skip_reason(PERIODS["2020"], by_period))
        self.assertIn("0 bearers", rules.skip_reason(PERIODS["2021"], by_period))
        by_period = {"2020": cells((LONDON, 100))}
        self.assertIsNone(rules.skip_reason(PERIODS["2020"], by_period))


if __name__ == "__main__":
    unittest.main()
