"""Tests for what happens to a name's map in each period (pipeline/rules.py): built, substituted
from another year, or left out.

Run from the project root:   python3 -m unittest discover -s pipeline/tests -t .
"""
import unittest

import numpy as np

from pipeline import config, kde, rules

GLASGOW = (259000, 665000)
LONDON = (530000, 180000)
PERIODS = {p["id"]: p for p in config.PERIODS}


def cells(*places):
    """Bearers as (cell x, cell y, n) from a list of ((easting, northing), n)."""
    g = config.GRID
    return (np.array([int((x - g["x0"]) // g["cell"]) for (x, y), n in places]),
            np.array([int((y - g["y0"]) // g["cell"]) for (x, y), n in places]),
            np.array([float(n) for (x, y), n in places]))


class Resolve(unittest.TestCase):
    def test_share_of_bearers_in_scotland(self):
        self.assertAlmostEqual(rules.scotland_share(cells((GLASGOW, 60), (LONDON, 40))), 0.6)
        self.assertEqual(rules.scotland_share(cells((LONDON, 500))), 0.0)

    def test_a_scottish_name_reuses_1901s_map_for_1911_and_1921(self):
        # plenty of bearers in 1911/1921 on their own (the Scots who moved south), but 70% of the
        # name was Scottish in 1901, so both years should copy 1901 rather than build their own
        by_period = {"1901": cells((GLASGOW, 700), (LONDON, 300)),
                     "1911": cells((LONDON, 900)), "1921": cells((LONDON, 950))}
        for year in ("1911", "1921"):
            r = rules.resolve(PERIODS[year], by_period)
            self.assertEqual(r.action, "substitute")
            self.assertEqual(r.reference, "1901")
            self.assertIn("70%", r.reason)

    def test_an_english_name_builds_its_own_1911_and_1921_maps(self):
        by_period = {"1901": cells((GLASGOW, 50), (LONDON, 950)),
                     "1911": cells((LONDON, 900)), "1921": cells((LONDON, 950))}
        self.assertEqual(rules.resolve(PERIODS["1911"], by_period).action, "build")
        self.assertEqual(rules.resolve(PERIODS["1921"], by_period).action, "build")

    def test_1901_is_not_itself_affected_by_the_scotland_rule(self):
        # 1901 has Scotland, so it is never a candidate for substitution, however Scottish the name
        self.assertEqual(rules.resolve(PERIODS["1901"], {"1901": cells((GLASGOW, 900))}).action, "build")

    def test_no_map_to_copy_falls_back_to_the_ordinary_threshold(self):
        # 1901 is itself too small to build a map (or to be copied), so 1911 must stand on its own
        by_period = {"1901": cells((GLASGOW, 20), (LONDON, 5)), "1911": cells((LONDON, 900))}
        self.assertEqual(rules.resolve(PERIODS["1911"], by_period).action, "build")
        by_period["1911"] = cells((LONDON, 10))
        r = rules.resolve(PERIODS["1911"], by_period)
        self.assertEqual(r.action, "omit")
        self.assertIn("10 bearers", r.reason)

    def test_the_threshold_is_per_source(self):
        # resolve() reads config.THRESHOLD[source] independently for each source - checked against
        # the live values (both 100 today) rather than hardcoded numbers, so this still holds if the
        # two are ever set differently again
        census_t, register_t = config.THRESHOLD["census"], config.THRESHOLD["register"]
        self.assertEqual(rules.resolve(PERIODS["1901"], {"1901": cells((LONDON, census_t))}).action, "build")
        self.assertEqual(rules.resolve(PERIODS["1901"], {"1901": cells((LONDON, census_t - 1))}).action, "omit")
        self.assertEqual(rules.resolve(PERIODS["2020"], {"2020": cells((LONDON, register_t - 1))}).action, "omit")
        self.assertEqual(rules.resolve(PERIODS["2020"], {"2020": cells((LONDON, register_t))}).action, "build")


class BuildMaps(unittest.TestCase):
    def setUp(self):
        self.land = kde.Land()
        # a flat, generous population everywhere, so weighting does not empty out the map
        flat = np.full((config.GRID["ny"], config.GRID["nx"]), 5000.0)
        self.pop = {pid: flat for pid in ("1901", "1911", "1921")}

    def test_a_substituted_period_gets_the_same_map_as_its_reference(self):
        by_period = {"1901": cells((GLASGOW, 5000), (LONDON, 2000)),
                     "1911": cells((LONDON, 3000)), "1921": cells((LONDON, 3200))}
        periods = [PERIODS["1901"], PERIODS["1911"], PERIODS["1921"]]
        bandwidth = kde.choose_bandwidth(list(by_period.values()))
        out = rules.build_maps(periods, by_period, bandwidth, self.pop, self.land)
        self.assertEqual(out["1901"][1].action, "build")
        self.assertEqual((out["1911"][1].action, out["1921"][1].action), ("substitute", "substitute"))
        self.assertEqual(kde.geojson(out["1911"][0]), kde.geojson(out["1901"][0]))
        self.assertEqual(kde.geojson(out["1921"][0]), kde.geojson(out["1901"][0]))

    def test_the_reference_year_is_built_even_when_not_asked_for(self):
        by_period = {"1901": cells((GLASGOW, 5000), (LONDON, 2000)), "1911": cells((LONDON, 3000))}
        bandwidth = kde.choose_bandwidth(list(by_period.values()))
        out = rules.build_maps([PERIODS["1911"]], by_period, bandwidth, self.pop, self.land)
        self.assertEqual(set(out), {"1911"})            # only what was asked for comes back
        self.assertEqual(out["1911"][1].action, "substitute")
        self.assertIsNotNone(out["1911"][0])             # but it has a real map, borrowed from 1901

    def test_a_reference_is_only_built_once(self):
        # 1911 and 1921 both copy 1901; make_map should run once for 1901, not twice
        by_period = {"1901": cells((GLASGOW, 5000), (LONDON, 2000)),
                     "1911": cells((LONDON, 3000)), "1921": cells((LONDON, 3200))}
        periods = [PERIODS["1901"], PERIODS["1911"], PERIODS["1921"]]
        bandwidth = kde.choose_bandwidth(list(by_period.values()))
        timings = {}
        rules.build_maps(periods, by_period, bandwidth, self.pop, self.land, timings=timings)
        self.assertEqual(set(timings), {"1901"})         # the only fresh build


if __name__ == "__main__":
    unittest.main()
