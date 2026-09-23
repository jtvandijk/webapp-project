"""Tests for stages 2-4 (population surfaces, point extracts, maps) - built to run end to end on a
small fake database, the same way test_stage1.py checks stage 1.

Run from the project root:   python3 -m unittest discover -s pipeline/tests -t .
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from pipeline import config, fake_data, kde, s1_counts, s2_surfaces, s3_extracts, s4_maps
from pipeline.names import chunk_of


class Stage234EndToEnd(unittest.TestCase):
    """Runs real stage 1-4 code, in process (not via the command-line scripts), on a small fake
    database - checking the pieces fit together, not any one piece in isolation (test_kde.py and
    test_rules.py already do that for the map calculation itself)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "test.db"
        fake_data.generate(persons=8000, surnames=200, seed=3, path=db_path, quiet=True)
        cls.cfg = dict(config.settings("fake"), database=str(db_path))
        cls.conn = sqlite3.connect(db_path)

        counts = s1_counts.count_all(cls.conn, cls.conn, cls.cfg)
        cls.listed = s1_counts.name_list(counts)          # {key: [period ids]}
        cls.names = sorted(cls.listed)
        assert cls.names, "fake data produced no names above threshold - check the seed"

        cls.land = kde.Land()
        cls.periods = config.PERIODS
        cls.chunks = 4

        # stage 2: one surface per period
        cls.surfaces = {p["id"]: s2_surfaces.build_surface(cls.conn, cls.cfg, p) for p in cls.periods}

        # stage 3: one query per period, split into chunk files on disk
        cls.chunks_dir = Path(cls.tmp.name) / "chunks"
        for p in cls.periods:
            s3_extracts.extract_period(cls.conn, cls.cfg, p, cls.names, cls.chunks, cls.chunks_dir)

        cls.surfaces_dir = Path(cls.tmp.name) / "surfaces"
        cls.maps_dir = Path(cls.tmp.name) / "maps"
        cls.stats_dir = Path(cls.tmp.name) / "stats"
        cls.surfaces_dir.mkdir()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def test_every_name_lands_in_exactly_one_chunk_consistently(self):
        # whatever chunk file a name's rows actually show up in must be the chunk chunk_of() itself
        # predicts for it - checked from the written files, not just by calling chunk_of() twice
        for period in self.periods:
            for chunk in range(self.chunks):
                path = self.chunks_dir / period["id"] / f"{chunk}.csv"
                found = {row.split(",")[0] for row in path.read_text().splitlines()[1:]}
                for name in found:
                    self.assertEqual(chunk_of(name, self.chunks), chunk)

    def test_stage4_processes_every_name_across_every_chunk(self):
        seen = set()
        for chunk in range(self.chunks):
            by_period = s4_maps.load_chunk(self.chunks_dir, self.periods, chunk)
            names_here = set().union(*(d.keys() for d in by_period.values()))
            for name in names_here:
                cells_by_period = {pid: by_period[pid].get(name) for pid in by_period}
                jsonl_rows, stats_rows = s4_maps.process_name(name, cells_by_period, self.periods,
                                                               self.surfaces, self.land)
                self.assertEqual(len(jsonl_rows), len(self.periods))
                self.assertEqual(len(stats_rows), len(self.periods))
                seen.add(name)
        self.assertEqual(seen, set(self.names))         # every listed name was processed exactly once

    def test_a_build_row_carries_real_geojson_an_omit_row_does_not(self):
        chunk = chunk_of(self.names[0], self.chunks)
        by_period = s4_maps.load_chunk(self.chunks_dir, self.periods, chunk)
        cells_by_period = {pid: by_period[pid].get(self.names[0]) for pid in by_period}
        jsonl_rows, stats_rows = s4_maps.process_name(self.names[0], cells_by_period, self.periods,
                                                       self.surfaces, self.land)
        builds = [r for r in jsonl_rows if r["action"] == "build"]
        omits = [r for r in jsonl_rows if r["action"] == "omit"]
        for row in builds:
            self.assertIn("geojson", row)
            self.assertGreater(len(row["geojson"]["features"]), 0)
        for row in omits:
            self.assertNotIn("geojson", row)
            self.assertIn("reason", row)

    def test_a_build_with_no_surviving_blob_is_recorded_as_omit(self):
        # real question raised (2026-09-23): r.action == "build" is decided from the raw bearer
        # count alone (rules.resolve()), before weighting/blob-dropping/geometry ever run - it is a
        # plan, not a guarantee. MIN_BLOB_SHARE/MIN_BLOB_BEARERS can legitimately drop every blob for
        # a name that otherwise clears the threshold (bands comes back None) - that must not look
        # identical to a genuine successful build with no signal anything went wrong. Forced here
        # with an absurdly high MIN_BLOB_BEARERS so a real, well-over-threshold name still loses
        # everything to blob-dropping.
        period = self.periods[0]
        cells_by_period = {period["id"]: (np.array([300]), np.array([300]), np.array([500.0]))}
        pop_surfaces = {period["id"]: self.surfaces[period["id"]]}
        with mock.patch.object(config, "MIN_BLOB_BEARERS", 1_000_000):
            jsonl_rows, stats_rows = s4_maps.process_name("test", cells_by_period, [period], pop_surfaces, self.land)
        self.assertEqual(jsonl_rows[0]["action"], "omit")
        self.assertEqual(jsonl_rows[0]["reason"], "no concentration survived weighting/blob-dropping")
        self.assertNotIn("geojson", jsonl_rows[0])
        self.assertEqual(stats_rows[0][2], "omit")             # jsonl and stats agree on the reclassified action

    def test_a_build_with_unfixable_geometry_is_recorded_as_omit(self):
        # the other way "build" can end up with nothing to show: bands is real, but every one of
        # its levels fails GeoJSON conversion (kde._repair() giving up on a genuinely unfixable
        # shape - see its docstring for the real incident this covers). Forced here by making
        # kde.geojson() itself return None, the same as a total repair failure would.
        period = self.periods[0]
        cells_by_period = {period["id"]: (np.array([300]), np.array([300]), np.array([500.0]))}
        pop_surfaces = {period["id"]: self.surfaces[period["id"]]}
        with mock.patch.object(s4_maps.kde, "geojson", return_value=None):
            jsonl_rows, stats_rows = s4_maps.process_name("test", cells_by_period, [period], pop_surfaces, self.land)
        self.assertEqual(jsonl_rows[0]["action"], "omit")
        self.assertEqual(jsonl_rows[0]["reason"], "geometry could not be repaired")
        self.assertNotIn("geojson", jsonl_rows[0])
        self.assertEqual(stats_rows[0][2], "omit")

    def test_a_substitute_row_names_its_reference_and_carries_no_geojson_of_its_own(self):
        found_one = False
        for chunk in range(self.chunks):
            by_period = s4_maps.load_chunk(self.chunks_dir, self.periods, chunk)
            for name in set().union(*(d.keys() for d in by_period.values())):
                cells_by_period = {pid: by_period[pid].get(name) for pid in by_period}
                jsonl_rows, _ = s4_maps.process_name(name, cells_by_period, self.periods, self.surfaces, self.land)
                for row in jsonl_rows:
                    if row["action"] == "substitute":
                        found_one = True
                        self.assertNotIn("geojson", row)
                        self.assertIn("reference", row)
        # not asserting this must happen (depends on the fake data's random Scottish shares), just
        # documenting what is checked when it does; the other two tests already require >=1 chunk
        # of real names to exist, so this is a bonus check, not the only coverage of "substitute"

    def test_one_names_failure_does_not_take_the_rest_of_the_chunk_down(self):
        # real incident (2026-09-23): a shapely/GEOS error on one real name crashed the whole chunk,
        # losing the other ~150 unrelated names' work with it - process_name() failing for one name
        # must not stop the others in the same chunk from being written and the chunk from finishing
        chunk = 0
        for period in self.periods:
            np.save(self.surfaces_dir / f"{period['id']}.npy", self.surfaces[period["id"]])

        real_process_name = s4_maps.process_name
        by_period = s4_maps.load_chunk(self.chunks_dir, self.periods, chunk)
        names_here = sorted(set().union(*(d.keys() for d in by_period.values())))
        self.assertGreaterEqual(len(names_here), 2, "need at least 2 names in this chunk to test isolation")
        unlucky = names_here[0]

        def flaky(name, cells_by_period, periods, pop_surfaces, land):
            if name == unlucky:
                raise RuntimeError("simulated GEOS failure")
            return real_process_name(name, cells_by_period, periods, pop_surfaces, land)

        argv = ["s4_maps", "--chunk", str(chunk), "--chunks", str(self.chunks), "--force",
               "--chunks-dir", str(self.chunks_dir), "--surfaces-dir", str(self.surfaces_dir),
               "--out-dir", str(self.maps_dir), "--stats-dir", str(self.stats_dir)]
        with mock.patch.object(s4_maps, "process_name", flaky), mock.patch.object(sys, "argv", argv):
            s4_maps.main()          # must not raise

        done_text = (self.maps_dir / f"chunk_{chunk}.done").read_text()
        self.assertIn(unlucky, done_text)
        self.assertIn("FAILED", done_text)
        errors_text = (self.maps_dir / f"chunk_{chunk}.errors.log").read_text()
        self.assertIn(unlucky, errors_text)
        self.assertIn("RuntimeError", errors_text)

        written_names = set()
        for line in (self.maps_dir / f"chunk_{chunk}.jsonl").read_text().splitlines():
            written_names.add(json.loads(line)["surname"])
        self.assertNotIn(unlucky, written_names)
        for other in names_here[1:]:
            self.assertIn(other, written_names)


if __name__ == "__main__":
    unittest.main()
