"""Tests for the map calculation, on invented points.

Run from the project root:   python3 -m unittest discover -s pipeline/tests -t .
"""
import importlib.util
import time
import unittest

import numpy as np

from pipeline import config, kde

# the same checker that decides whether a release is accepted (tools/validate_data.py)
_spec = importlib.util.spec_from_file_location("validate_data", config.ROOT / "tools" / "validate_data.py")
validate_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_data)


def contract_errors(collection):
    report = validate_data.Report()
    validate_data.check_map(collection, {1, 2, 3}, "test map", report)
    return report.errors

CARDIFF = (318000, 177000)
LONDON = (530000, 180000)


def cells_around(centre, spread_m, n_cells, total, seed=1):
    """Bearers scattered around a place, as (cell x, cell y, n)."""
    rng = np.random.default_rng(seed)
    x = centre[0] + rng.normal(0, spread_m, n_cells)
    y = centre[1] + rng.normal(0, spread_m, n_cells)
    ix = ((x - config.GRID["x0"]) // config.GRID["cell"]).astype(int)
    iy = ((y - config.GRID["y0"]) // config.GRID["cell"]).astype(int)
    return ix, iy, np.full(n_cells, total / n_cells)


def population():
    """A crude 'everybody' surface with a big city and a smaller one."""
    a = cells_around(LONDON, 20000, 400, 8_000_000, seed=2)
    b = cells_around(CARDIFF, 10000, 200, 400_000, seed=3)
    return kde.population_surface(np.r_[a[0], b[0]], np.r_[a[1], b[1]], np.r_[a[2], b[2]])


class MapCalculation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.land = kde.Land()
        cls.pop = population()

    def make(self, total, spread=12000, cells=150):
        ix, iy, n = cells_around(CARDIFF, spread, cells, total)
        return kde.make_map(kde.to_grid(ix, iy, n), kde.choose_bandwidth([(ix, iy, n)]), self.pop, self.land)

    def test_a_concentrated_name_gives_three_bands_around_the_right_place(self):
        bands = self.make(2000)
        self.assertIsNotNone(bands)
        self.assertTrue(all(not b.is_empty for b in bands), "all three levels should exist")
        collection = kde.geojson(bands)
        centre = bands[2].centroid
        lon, lat = kde._to_lonlat.transform(centre.x, centre.y)
        self.assertAlmostEqual(lon, -3.18, delta=0.4)
        self.assertAlmostEqual(lat, 51.48, delta=0.4)
        self.assertEqual(contract_errors(collection), [])

    def test_bands_do_not_overlap_and_stay_on_land(self):
        bands = self.make(2000)
        for i in range(3):
            for j in range(i + 1, 3):
                self.assertLess(bands[i].intersection(bands[j]).area, 1e5, f"levels {i + 1} and {j + 1} overlap")
        union = bands[0].union(bands[1]).union(bands[2])
        # simplifying the outline can move an edge by up to SIMPLIFY_M, so that is how far past the
        # coast a map may reach, and no further
        near_land = self.land.clip(union.buffer(50000)).buffer(config.SIMPLIFY_M + 10)
        self.assertLess(union.difference(near_land).area, 1e4, "part of the map is out in the sea")

    def test_small_names_show_as_clearly_as_big_ones(self):
        # the whole reason for comparing each name with its own peak
        small, big = self.make(150), self.make(150000)
        self.assertIsNotNone(small)
        self.assertGreater(small[2].area, 0, "a name with 150 bearers still gets a top level")
        self.assertGreater(big[2].area, 0)

    def test_many_different_names_never_crash_and_always_meet_the_contract(self):
        # names with one to six clusters, anywhere in the country, small and large: this is what
        # found a topology fault that a single tidy blob does not show
        rng = np.random.default_rng(11)
        made = 0
        for i in range(40):
            parts = []
            for _ in range(int(rng.integers(1, 7))):
                centre = (rng.uniform(100000, 600000), rng.uniform(50000, 950000))
                parts.append(cells_around(centre, rng.uniform(5000, 40000), int(rng.integers(20, 300)),
                                          float(rng.choice([120, 800, 5000, 60000])), seed=int(rng.integers(1e6))))
            ix, iy, n = (np.concatenate([p[k] for p in parts]) for k in range(3))
            ok = (ix >= 0) & (ix < config.GRID["nx"]) & (iy >= 0) & (iy < config.GRID["ny"])
            ix, iy, n = ix[ok], iy[ok], n[ok]
            bands = kde.make_map(kde.to_grid(ix, iy, n), kde.choose_bandwidth([(ix, iy, n)]), self.pop, self.land)
            if bands is None:
                continue                                     # nothing on land, nothing to draw: allowed
            self.assertEqual(contract_errors(kde.geojson(bands)), [], f"name {i}")
            made += 1
        self.assertGreater(made, 20, "most random names should produce a map")

    def test_weighting_dial(self):
        name = np.full((2, 2), 4.0)
        pop = np.array([[100.0, 1000.0], [10.0, 100.0]])         # people per km2
        land = np.array([[True, True], [True, False]])
        plain = kde.weigh(name, pop, land, power=0)
        self.assertTrue((plain == np.where(land, 4.0, 0.0)).all(), "power 0 is plain density (on land)")
        full = kde.weigh(name, pop, land, power=1)
        self.assertAlmostEqual(full[0, 0] / full[0, 1], 10.0)     # ten times fewer people: ten times higher
        self.assertAlmostEqual(full[1, 0], 4.0 / config.WEIGHT_FLOOR)   # 10 people/km2 counts as the floor
        self.assertEqual(full[1, 1], 0.0, "the sea is always zero")
        half = kde.weigh(name, pop, land, power=0.5)
        self.assertAlmostEqual(half[0, 0] / half[0, 1], 10 ** 0.5)

    def test_mass_levels_hold_the_stated_share_of_the_density(self):
        ix, iy, n = cells_around(CARDIFF, 15000, 200, 3000)
        surface = kde.weigh(kde.smooth(kde.to_grid(ix, iy, n), 10000), self.pop, self.land.grid, power=0)
        cuts = kde.level_cutoffs(surface, "mass")
        self.assertEqual(list(cuts), sorted(cuts), "level 1 has the lowest cut-off")
        for share, cut in zip(config.LEVEL_MASS, cuts):
            held = surface[surface > cut * surface.max()].sum() / surface.sum()
            self.assertAlmostEqual(held, share, delta=0.02)

    def test_the_land_mask_is_about_the_size_of_great_britain(self):
        self.assertAlmostEqual(self.land.grid.sum(), 229700, delta=3000)      # 1 km cells, about 230,000 km2

    def test_output_is_repeatable(self):
        self.assertEqual(kde.geojson(self.make(2000)), kde.geojson(self.make(2000)))

    def test_bandwidth_grows_with_size_between_the_limits(self):
        self.assertEqual(kde.size_bandwidth(100), config.BANDWIDTH_MIN_M)
        self.assertEqual(kde.size_bandwidth(30), config.BANDWIDTH_MIN_M)
        self.assertEqual(kde.size_bandwidth(100000), config.BANDWIDTH_MAX_M)
        self.assertEqual(kde.size_bandwidth(5_000_000), config.BANDWIDTH_MAX_M)
        sizes = [100, 300, 1000, 3000, 10000, 30000, 100000]
        widths = [kde.size_bandwidth(n) for n in sizes]
        self.assertEqual(widths, sorted(widths))
        self.assertAlmostEqual(kde.size_bandwidth(1000), 11333, delta=5)

    def test_a_name_gets_one_bandwidth_from_its_biggest_year(self):
        small = (np.array([300]), np.array([300]), np.array([150.0]))
        large = (np.array([300]), np.array([300]), np.array([15000.0]))
        self.assertEqual(kde.choose_bandwidth([small, large]), kde.size_bandwidth(15000))

    def test_one_map_is_fast(self):
        started = time.perf_counter()
        for _ in range(5):
            self.make(2000)
        per_map = (time.perf_counter() - started) / 5
        print(f"\n  one map takes {per_map * 1000:.0f} ms on this machine", end="")
        self.assertLess(per_map, 5.0)


if __name__ == "__main__":
    unittest.main()
