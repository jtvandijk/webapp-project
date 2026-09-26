"""Tests for stage 6 (pipeline/s6_assemble.py, merge_release.py): turning stage 4's maps.jsonl and stage
5's facts.csv into the per-name release files docs/data-contract.md describes. The field-mapping tests
(BuildFacts, BuildMaps, BuildCounts) work from hand-built rows, the same style as test_stage5.py's own
PlacesAreShownTidily; Stage6EndToEnd runs real stages 1-6 on a small fake database, the same style as
test_stage234.py's Stage234EndToEnd.

Run from the project root:   python3 -m unittest discover -s pipeline/tests -t .
"""
import contextlib
import csv
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from pipeline import config, fake_data, kde, merge_release, preview_web, s1_counts, s2_surfaces, s3_extracts, s4_maps, s5_facts, s6_assemble
from pipeline.names import chunk_of

sys.path.insert(0, str(config.ROOT))                                 # tools/ is not a package under pipeline/
import importlib.util
_spec = importlib.util.spec_from_file_location("validate_data", config.ROOT / "tools" / "validate_data.py")
validate_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_data)


def fact_row(fact, value, detail, ref_year=""):
    return {"surname": "smith", "fact": fact, "version": "v", "ref_year": ref_year, "n_bearers": "", "value": value,
            "detail": json.dumps(detail)}


class BuildFacts(unittest.TestCase):
    def test_oac_loac_fpc_are_group_and_distribution(self):
        rows = [fact_row("oac", "3b", {"distribution": {"3b": 0.6, "2a": 0.4}, "tie": True})]
        facts = s6_assemble.build_facts(rows)
        self.assertEqual(facts, {"oac": {"group": "3b", "distribution": {"3b": 0.6, "2a": 0.4}}})       # "tie" is not published

    def test_ahah_is_mode_and_distribution_as_a_list(self):
        rows = [fact_row("ahah", "6", {"distribution": [0.1] * 10})]
        facts = s6_assemble.build_facts(rows)
        self.assertEqual(facts["ahah"], {"mode": 6, "distribution": [0.1] * 10})
        self.assertIsInstance(facts["ahah"]["mode"], int)

    def test_imd_and_imd_score_merge_into_one_object(self):
        rows = [fact_row("imd", "4", {"distribution": [0.05] * 10}), fact_row("imd_score", "4.2", {"sd": 2.4})]
        facts = s6_assemble.build_facts(rows)
        self.assertEqual(facts["imd"], {"mode": 4, "distribution": [0.05] * 10, "mean": 4.2, "sd": 2.4})
        self.assertNotIn("imd_score", facts)                          # folded into imd, not its own key

    def test_imd_without_a_score_row_has_no_mean_or_sd(self):
        facts = s6_assemble.build_facts([fact_row("imd", "4", {"distribution": [0.05] * 10})])
        self.assertNotIn("mean", facts["imd"])
        self.assertNotIn("sd", facts["imd"])

    def test_ethnicity_becomes_eth_with_countries_from_codes(self):
        rows = [fact_row("ethnicity", "WBR", {"distribution": {"WBR": 0.7}, "codes": [["WBR-EN", 0.4]]})]
        facts = s6_assemble.build_facts(rows)
        self.assertEqual(facts["eth"], {"group": "WBR", "distribution": {"WBR": 0.7}, "countries": [["WBR-EN", 0.4]]})
        self.assertNotIn("ethnicity", facts)

    def test_ethnicity_unknown_is_published_not_omitted(self):
        facts = s6_assemble.build_facts([fact_row("ethnicity", "unknown", {})])
        self.assertEqual(facts["eth"]["group"], "unknown")

    def test_places_and_parishes_merge_and_rename_fields(self):
        rows = [fact_row("places", "", {"places": [{"msoa": "E02000001", "district": "E09000001"}]}),
               fact_row("parishes", "", {"parishes": [{"county": "Kent", "parish": "Dover"}], "years": [1851, 1901]})]
        facts = s6_assemble.build_facts(rows)
        self.assertEqual(facts["places"], {"register": [{"area": "E09000001", "name": "E02000001"}],
                                          "census": [{"area": "Kent", "name": "Dover"}]})
        self.assertNotIn("years", json.dumps(facts))                  # "years" is for the report, not published

    def test_places_alone_does_not_invent_an_empty_census_key(self):
        facts = s6_assemble.build_facts([fact_row("places", "", {"places": [{"msoa": "m", "district": "d"}]})])
        self.assertEqual(set(facts["places"]), {"register"})

    def test_forenames_register_and_census_merge(self):
        rows = [fact_row("forenames_register", "", {"f": ["mary"], "m": ["john"]}),
               fact_row("forenames_census", "", {"f": ["ann"], "m": ["george"], "years": [1851, 1911]})]
        facts = s6_assemble.build_facts(rows)
        self.assertEqual(facts["forenames"], {"register": {"f": ["mary"], "m": ["john"]},
                                             "census": {"f": ["ann"], "m": ["george"]}})

    def test_no_rows_gives_no_facts(self):
        self.assertEqual(s6_assemble.build_facts([]), {})


class BuildCounts(unittest.TestCase):
    def test_grouped_by_source_then_year_as_whole_numbers(self):
        rows = [{"source": "census", "year": "1851", "n": "120"}, {"source": "census", "year": "1861", "n": "130"},
               {"source": "register", "year": "2026", "n": "500"}]
        counts = s6_assemble.build_counts(rows)
        self.assertEqual(counts, {"census": {"1851": 120, "1861": 130}, "register": {"2026": 500}})
        self.assertIsInstance(counts["census"]["1851"], int)


class BuildMaps(unittest.TestCase):
    def test_a_build_row_is_used_as_is(self):
        collection = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"level": 1}, "geometry": {}}]}
        maps = s6_assemble.build_maps([{"period": "1851", "action": "build", "geojson": collection}])
        self.assertEqual(maps, {"1851": collection})

    def test_a_substitute_row_copies_its_references_geometry_and_marks_it(self):
        collection = {"type": "FeatureCollection", "features": ["x"]}
        rows = [{"period": "1901", "action": "build", "geojson": collection},
               {"period": "1911", "action": "substitute", "reference": "1901"}]
        maps = s6_assemble.build_maps(rows)
        self.assertEqual(maps["1911"], {"type": "FeatureCollection", "features": ["x"], "copyOf": "1901"})
        self.assertEqual(maps["1901"], collection)                     # the original itself carries no copyOf

    def test_the_copy_is_independent_of_the_original(self):
        collection = {"type": "FeatureCollection", "features": ["x"]}
        rows = [{"period": "1901", "action": "build", "geojson": collection},
               {"period": "1911", "action": "substitute", "reference": "1901"}]
        maps = s6_assemble.build_maps(rows)
        maps["1911"]["features"].append("y")
        self.assertEqual(maps["1901"]["features"], ["x"])              # mutating the copy must not touch the original

    def test_omit_rows_are_left_out(self):
        maps = s6_assemble.build_maps([{"period": "1861", "action": "omit", "reason": "too few bearers"}])
        self.assertEqual(maps, {})

    def test_only_a_build_row_counts_even_if_another_row_carries_stray_geojson(self):
        # stage 4 never writes geojson on an omit/substitute row today, so this cannot happen for real -
        # but if it ever did (a future change to s4_maps.py), the action, not the mere presence of a
        # geojson key, must decide what is a map
        stray = {"type": "FeatureCollection", "features": ["stray"]}
        maps = s6_assemble.build_maps([{"period": "1861", "action": "omit", "geojson": stray},
                                       {"period": "1911", "action": "substitute", "reference": "1861"}])
        self.assertEqual(maps, {})

    def test_a_substitute_whose_reference_did_not_build_is_left_out_rather_than_crash(self):
        # should not normally happen (rules.py only substitutes a reference year with enough bearers), but
        # the reference's own geometry can still fail weighting/repair - a defensive fallback, not a policy
        maps = s6_assemble.build_maps([{"period": "1901", "action": "omit", "reason": "geometry could not be repaired"},
                                       {"period": "1911", "action": "substitute", "reference": "1901"}])
        self.assertEqual(maps, {})


class BuildBundle(unittest.TestCase):
    def test_no_maps_means_no_bundle_at_all(self):
        # data-contract.md: a file with no map is not published
        self.assertIsNone(s6_assemble.build_bundle("smith", [{"period": "1851", "action": "omit"}], [], []))

    MAP_ROWS = [{"period": "1851", "action": "build", "geojson": {"type": "FeatureCollection", "features": []}}]

    def test_a_name_with_a_map_but_no_facts_still_gets_a_file(self):
        bundle = s6_assemble.build_bundle("smith", self.MAP_ROWS, [], [])
        self.assertEqual(bundle["schema"], 1)
        self.assertEqual(bundle["name"], "smith")
        self.assertNotIn("facts", bundle)                              # no facts rows -> no facts key at all

    def test_facts_stay_out_of_the_file_unless_asked_for(self):
        # decided 2026-09-26: a name file is counts and maps; the facts are one table
        facts = [fact_row("oac", "3b", {"distribution": {"3b": 1.0}})]
        self.assertNotIn("facts", s6_assemble.build_bundle("smith", self.MAP_ROWS, facts, []))
        self.assertEqual(s6_assemble.build_bundle("smith", self.MAP_ROWS, facts, [], include_facts=True)["facts"],
                         {"oac": {"group": "3b", "distribution": {"3b": 1.0}}})


class FactsTableRows(unittest.TestCase):
    def test_one_row_per_public_fact_sorted_with_the_same_json_as_in_a_name_file(self):
        rows = [fact_row("imd", "4", {"distribution": [0.1] * 10}), fact_row("imd_score", "4.2", {"sd": 2.4}),
                fact_row("oac", "3b", {"distribution": {"3b": 1.0}})]
        table = s6_assemble.facts_table_rows("smith", rows)
        self.assertEqual([r[:2] for r in table], [["smith", "imd"], ["smith", "oac"]])      # imd_score is folded into imd: no row of its own
        self.assertEqual(json.loads(table[0][2]), s6_assemble.build_facts(rows)["imd"])
        self.assertNotIn(" ", table[1][2])                                                # compact JSON

    def test_a_name_with_no_facts_has_no_rows(self):
        self.assertEqual(s6_assemble.facts_table_rows("smith", []), [])


class SplitByChunk(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch = mock.patch.object(config, "WORK", Path(self.tmp.name))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def write_counts(self, rows):
        path = config.WORK / "counts.csv"
        with open(path, "w", newline="") as f:
            out = csv.DictWriter(f, fieldnames=s6_assemble.COUNTS_HEADER)
            out.writeheader()
            out.writerows(rows)
        return path

    def test_every_row_lands_in_the_chunk_chunk_of_predicts(self):
        rows = [{"source": "register", "year": "2026", "surname": n, "n": "10"} for n in ("smith", "jones", "patel", "khan")]
        self.write_counts(rows)
        s6_assemble.split_by_chunk("counts", s6_assemble.COUNTS_HEADER, 5)
        for row in rows:
            chunk = chunk_of(row["surname"], 5)
            found = s6_assemble.load_chunk_csv("counts", chunk)
            self.assertIn(row["surname"], found, row)

    def test_every_chunk_file_is_written_even_when_empty(self):
        self.write_counts([{"source": "register", "year": "2026", "surname": "smith", "n": "10"}])
        s6_assemble.split_by_chunk("counts", s6_assemble.COUNTS_HEADER, 5)
        for chunk in range(5):
            self.assertTrue((config.WORK / "counts" / "chunks" / f"{chunk}.csv").exists())

    def test_is_current_only_after_a_split_that_matches(self):
        self.write_counts([{"source": "register", "year": "2026", "surname": "smith", "n": "10"}])
        self.assertFalse(s6_assemble.split_current("counts", 5))
        s6_assemble.split_by_chunk("counts", s6_assemble.COUNTS_HEADER, 5)
        self.assertTrue(s6_assemble.split_current("counts", 5))
        self.assertFalse(s6_assemble.split_current("counts", 7), "a different chunk count must not read as current")

    def test_a_split_older_than_its_source_is_not_current(self):
        # stage 5 or 1 re-run since --prepare: reusing the old split would assemble yesterday's facts
        source = self.write_counts([{"source": "register", "year": "2026", "surname": "smith", "n": "10"}])
        s6_assemble.split_by_chunk("counts", s6_assemble.COUNTS_HEADER, 5)
        self.assertTrue(s6_assemble.split_current("counts", 5))
        marker = config.WORK / "counts" / "chunks" / "CHUNKS"
        later = marker.stat().st_mtime + 100
        os.utime(source, (later, later))
        self.assertFalse(s6_assemble.split_current("counts", 5))

    def test_facts_is_read_from_work_facts_facts_csv_not_work_facts_csv(self):
        # real slip this guards against: counts.csv is flat (work/counts.csv) but facts.csv is not
        # (work/facts/facts.csv, alongside report.txt/by_fact/extract) - a formula based on the stem alone
        # would silently look in the wrong place for one of the two
        (config.WORK / "facts").mkdir()
        with open(config.WORK / "facts" / "facts.csv", "w", newline="") as f:
            out = csv.DictWriter(f, fieldnames=s6_assemble.FACTS_HEADER)
            out.writeheader()
            out.writerow(fact_row("oac", "3b", {}))
        s6_assemble.split_by_chunk("facts", s6_assemble.FACTS_HEADER, 3)
        self.assertIn("smith", s6_assemble.load_chunk_csv("facts", chunk_of("smith", 3)))

    def test_a_missing_source_file_stops_with_a_clear_message(self):
        with self.assertRaises(SystemExit) as stopped:
            s6_assemble.split_by_chunk("facts", s6_assemble.FACTS_HEADER, 5)
        self.assertIn("facts", str(stopped.exception))


class AssembleChunkOperations(unittest.TestCase):
    """s6_assemble.main() one chunk at a time, on small hand-written inputs (one chunk, so everything lands in
    it): the done-marker, refusal and failure-isolation behaviour copied from stage 4's real incidents
    (2026-09-23), the same reasoning as test_stage234.py's own tests of them."""

    SHAPE = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"level": 1}, "geometry": {}}]}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patch = mock.patch.object(config, "WORK", self.root)
        patch.start()
        self.addCleanup(patch.stop)
        (self.root / "maps").mkdir()
        rows = [{"surname": "alpha", "period": "2026", "action": "build", "bearers": 500, "geojson": self.SHAPE},
                {"surname": "beta", "period": "2026", "action": "build", "bearers": 300, "geojson": self.SHAPE},
                {"surname": "gamma", "period": "2026", "action": "omit", "bearers": 40, "reason": "too few"}]
        (self.root / "maps" / "chunk_0.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        (self.root / "maps" / "chunk_0.done").write_text("3 names\n")            # stage 4's own marker: this chunk is finished
        (self.root / "facts").mkdir()
        with open(self.root / "facts" / "facts.csv", "w", newline="") as f:
            out = csv.DictWriter(f, fieldnames=s6_assemble.FACTS_HEADER)
            out.writeheader()
            out.writerow({**fact_row("oac", "3b", {"distribution": {"3b": 1.0}}), "surname": "alpha"})
            out.writerow({**fact_row("oac", "2a", {"distribution": {"2a": 1.0}}), "surname": "gamma"})       # gamma has no map: not published
        with open(self.root / "counts.csv", "w", newline="") as f:
            out = csv.DictWriter(f, fieldnames=s6_assemble.COUNTS_HEADER)
            out.writeheader()
            for name in ("alpha", "beta", "gamma"):
                out.writerow({"source": "register", "year": "2026", "surname": name, "n": "500"})

    def run_stage(self, *args):
        with mock.patch.object(sys, "argv", ["s6_assemble", *args]):
            s6_assemble.main()

    def prepared(self):
        self.run_stage("--prepare", "--chunks", "1")

    def assemble(self, *extra):
        self.run_stage("--chunk", "0", "--chunks", "1", *extra)

    def written(self):
        return sorted(p.stem for p in (self.root / "release" / "names").glob("*/*.json"))

    def test_a_name_with_a_map_gets_a_file_and_a_name_with_none_does_not(self):
        self.prepared()
        self.assemble()
        self.assertEqual(self.written(), ["alpha", "beta"])                       # gamma is omit-only: not published
        self.assertEqual((self.root / "release" / "index_parts" / "chunk_0.txt").read_text().split(), ["alpha", "beta"])
        marker = (self.root / "release" / "chunk_0.done").read_text()
        self.assertIn("2 names", marker)
        self.assertIn("1 with no map (not published)", marker)                   # said, so it is not a silent drop

    def facts_part(self):
        with open(self.root / "release" / "facts_parts" / "chunk_0.csv", newline="") as f:
            return list(csv.DictReader(f))

    def test_counts_are_in_the_name_file_and_facts_go_to_the_facts_part_not_the_file(self):
        self.prepared()
        self.assemble()
        alpha = json.loads((self.root / "release" / "names" / "al" / "alpha.json").read_text())
        self.assertEqual(alpha["counts"], {"register": {"2026": 500}})
        self.assertNotIn("facts", alpha)                                         # by default a name file is counts and maps
        rows = self.facts_part()
        self.assertEqual([(r["name"], r["fact"]) for r in rows], [("alpha", "oac")])
        self.assertEqual(json.loads(rows[0]["data"]), {"group": "3b", "distribution": {"3b": 1.0}})

    def test_an_unpublished_name_has_no_facts_row(self):
        # gamma has a fact row in facts.csv but no map, so no file: it must not turn up in the facts either
        self.prepared()
        self.assemble()
        self.assertNotIn("gamma", [r["name"] for r in self.facts_part()])

    def test_facts_in_names_puts_them_in_the_file_as_well(self):
        self.prepared()
        self.assemble("--facts-in-names")
        alpha = json.loads((self.root / "release" / "names" / "al" / "alpha.json").read_text())
        beta = json.loads((self.root / "release" / "names" / "be" / "beta.json").read_text())
        self.assertEqual(alpha["facts"]["oac"]["group"], "3b")
        self.assertNotIn("facts", beta)                                          # beta has no fact rows at all
        self.assertEqual([r["name"] for r in self.facts_part()], ["alpha"])      # and the table has them too

    def test_a_finished_chunk_is_skipped_and_force_redoes_it(self):
        self.prepared()
        self.assemble()
        (self.root / "release" / "names" / "al" / "alpha.json").unlink()
        self.assemble()                                                          # marker + index still there: skipped
        self.assertNotIn("alpha", self.written())
        self.assemble("--force")
        self.assertIn("alpha", self.written())

    def test_a_chunk_stage_4_has_not_finished_is_refused_and_nothing_is_written(self):
        (self.root / "maps" / "chunk_0.done").unlink()                           # stage 4 is still writing (or was killed)
        self.prepared()
        with self.assertRaises(SystemExit) as stopped:
            self.assemble()
        self.assertIn("Stage 4 has not finished chunk 0", str(stopped.exception))
        self.assertEqual(self.written(), [])
        self.assertFalse((self.root / "release" / "chunk_0.done").exists())

    def test_a_finished_chunk_is_redone_when_stage_4_or_prepare_made_its_input_again(self):
        for stale in ("maps/chunk_0.jsonl", "facts/chunks/0.csv", "counts/chunks/0.csv"):
            with self.subTest(input_made_again=stale):
                self.prepared()
                for path in ("maps/chunk_0.jsonl", "facts/chunks/0.csv", "counts/chunks/0.csv"):
                    os.utime(self.root / path, (1_000_000_000, 1_000_000_000))       # long ago, whatever an earlier round did to them
                self.assemble("--force")
                marker = self.root / "release" / "chunk_0.done"
                (self.root / "release" / "names" / "al" / "alpha.json").unlink()
                self.assemble()
                self.assertNotIn("alpha", self.written(), "unchanged inputs: the finished chunk is skipped")
                later = marker.stat().st_mtime + 10
                os.utime(self.root / stale, (later, later))
                self.assemble()
                self.assertIn("alpha", self.written(), f"{stale} is newer than the finished chunk: it has to be redone")

    def test_a_done_marker_from_a_different_chunks_value_is_not_trusted(self):
        self.prepared()
        self.assemble()
        (self.root / "release" / "names" / "al" / "alpha.json").unlink()
        (self.root / "release" / "chunk_0.done").write_text("2 names, 0.1s, chunks=99\n")
        self.assemble()                                                          # must redo, not skip
        self.assertIn("alpha", self.written())
        self.assertIn("chunks=1", (self.root / "release" / "chunk_0.done").read_text())

    def test_a_missing_index_makes_a_done_marker_untrustworthy_too(self):
        self.prepared()
        self.assemble()
        (self.root / "release" / "index_parts" / "chunk_0.txt").unlink()
        (self.root / "release" / "names" / "al" / "alpha.json").unlink()
        self.assemble()
        self.assertIn("alpha", self.written())

    def test_a_missing_facts_part_makes_a_done_marker_untrustworthy_too(self):
        self.prepared()
        self.assemble()
        (self.root / "release" / "facts_parts" / "chunk_0.csv").unlink()
        (self.root / "release" / "names" / "al" / "alpha.json").unlink()
        self.assemble()
        self.assertIn("alpha", self.written())
        self.assertTrue((self.root / "release" / "facts_parts" / "chunk_0.csv").exists())

    def test_running_a_chunk_before_prepare_is_refused_with_the_command_to_run(self):
        with self.assertRaises(SystemExit) as stopped:
            self.assemble()
        self.assertIn("--prepare", str(stopped.exception))

    def test_a_prepare_made_for_a_different_number_of_chunks_is_refused(self):
        self.run_stage("--prepare", "--chunks", "2")
        with self.assertRaises(SystemExit) as stopped:
            self.assemble()                                                      # asks for 1 chunk, split into 2
        self.assertIn("--prepare", str(stopped.exception))

    def test_prepare_is_skipped_when_current_and_redone_with_force(self):
        self.prepared()
        chunk_file = self.root / "counts" / "chunks" / "0.csv"
        chunk_file.write_text("edited\n")
        self.prepared()                                                          # current: must not overwrite
        self.assertEqual(chunk_file.read_text(), "edited\n")
        self.run_stage("--prepare", "--chunks", "1", "--force")
        self.assertIn("alpha", chunk_file.read_text())

    def test_one_names_failure_does_not_take_the_rest_of_the_chunk_down(self):
        self.prepared()
        real = s6_assemble.build_bundle

        def flaky(name, *args, **kwargs):
            if name == "alpha":
                raise RuntimeError("simulated unexpected shape")
            return real(name, *args, **kwargs)
        with mock.patch.object(s6_assemble, "build_bundle", flaky):
            self.assemble()                                                      # must not raise
        self.assertEqual(self.written(), ["beta"])
        self.assertIn("FAILED", (self.root / "release" / "chunk_0.done").read_text())
        self.assertIn("RuntimeError", (self.root / "release" / "chunk_0.errors.log").read_text())

    def test_free_maps_is_off_by_default(self):
        self.prepared()
        self.assemble()
        self.assertTrue((self.root / "maps" / "chunk_0.jsonl").exists())

    def test_free_maps_deletes_only_this_chunks_raw_maps_after_a_clean_chunk(self):
        self.prepared()
        (self.root / "maps" / "chunk_1.jsonl").write_text("not this chunk's\n")
        self.assemble("--free-maps")
        self.assertFalse((self.root / "maps" / "chunk_0.jsonl").exists())
        self.assertTrue((self.root / "maps" / "chunk_1.jsonl").exists())        # another chunk's file is never touched
        self.assertEqual(self.written(), ["alpha", "beta"])                     # and what was assembled is still there

    def test_free_maps_keeps_the_raw_maps_if_any_name_failed(self):
        self.prepared()
        real = s6_assemble.build_bundle

        def flaky(name, *args, **kwargs):
            if name == "alpha":
                raise RuntimeError("simulated")
            return real(name, *args, **kwargs)
        with mock.patch.object(s6_assemble, "build_bundle", flaky):
            self.assemble("--free-maps")
        self.assertTrue((self.root / "maps" / "chunk_0.jsonl").exists(), "the raw rows are still needed to see why alpha failed")


class StreamingAtRealScale(unittest.TestCase):
    """Stage 6 meets real sizes: the facts table has millions of rows and a chunk's maps are gigabytes once parsed, so
    neither may be held whole in memory (the login node for --prepare, a 2 GB job for a chunk task)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patch = mock.patch.object(config, "WORK", self.root)
        patch.start()
        self.addCleanup(patch.stop)

    def write_jsonl(self, rows):
        (self.root / "maps").mkdir(exist_ok=True)
        (self.root / "maps" / "chunk_0.jsonl").write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows))

    def row(self, name, period, **more):
        return {"surname": name, "period": period, "action": "build", "bearers": 100, **more}

    def test_the_maps_are_read_one_name_at_a_time_not_all_at_once(self):
        self.write_jsonl([self.row(n, p) for n in ("alpha", "beta", "gamma") for p in ("1851", "1861", "1901")])
        parsed = []
        real = json.loads

        def counting(text, *args, **kwargs):
            parsed.append(text)
            return real(text, *args, **kwargs)
        lines_read = [0]

        class CountingFile:
            def __init__(self, path):
                self.handle = open(path)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.handle.close()

            def __iter__(self):
                for line in self.handle:
                    lines_read[0] += 1
                    yield line
        with mock.patch.object(s6_assemble.json, "loads", counting), mock.patch.object(s6_assemble, "open", CountingFile, create=True):
            first = next(s6_assemble.iter_maps_by_name(self.root / "maps", 0))
        self.assertEqual(first[0], "alpha")
        self.assertEqual([r["period"] for r in first[1]], ["1851", "1861", "1901"])
        self.assertLessEqual(len(parsed), 3 + 1, "reading the first name parsed the whole file")
        self.assertLessEqual(lines_read[0], 3 + 1, "reading the first name read the whole file (one line ahead is the most a group-by needs)")

    def test_a_name_is_found_without_parsing_its_line_and_odd_lines_are_parsed_properly(self):
        with mock.patch.object(s6_assemble.json, "loads", side_effect=AssertionError("should not parse")):
            self.assertEqual(s6_assemble._surname_of('{"surname":"smith","period":"1851","geojson":{"a":1}}\n'), "smith")
        self.assertEqual(s6_assemble._surname_of('{ "period": "1851", "surname": "jones" }\n'), "jones")       # another layout: parsed

    def test_a_maps_file_with_a_name_coming_back_or_out_of_order_is_refused(self):
        for order in (["alpha", "beta", "alpha"], ["beta", "alpha"]):
            self.write_jsonl([self.row(n, "1851") for n in order])
            with self.assertRaises(SystemExit) as stopped:
                list(s6_assemble.iter_maps_by_name(self.root / "maps", 0))
            self.assertIn("sorted order", str(stopped.exception), order)

    def test_an_empty_maps_file_is_no_names_not_an_error(self):
        self.write_jsonl([])
        self.assertEqual(list(s6_assemble.iter_maps_by_name(self.root / "maps", 0)), [])

    def test_the_split_keeps_quotes_commas_and_newlines_inside_a_cell_and_the_row_order(self):
        (self.root / "facts").mkdir()
        awkward = json.dumps({"note": 'say "hi", then\nleave', "list": [1, 2, 3]})
        rows = [fact_row("oac", "3b", {"n": i}) for i in range(5)] + [fact_row("places", "", {"x": 1})]
        rows[2]["detail"] = awkward
        with open(self.root / "facts" / "facts.csv", "w", newline="") as f:
            out = csv.DictWriter(f, fieldnames=s6_assemble.FACTS_HEADER)
            out.writeheader()
            out.writerows(rows)
        self.assertEqual(s6_assemble.split_by_chunk("facts", s6_assemble.FACTS_HEADER, 1), 6)
        with open(self.root / "facts" / "chunks" / "0.csv", newline="") as f:
            back = list(csv.DictReader(f))
        self.assertEqual([r["detail"] for r in back], [r["detail"] for r in rows])          # the awkward cell and the order survive

    def test_the_split_reads_one_row_at_a_time(self):
        # measured, not assumed: how many source rows had been read when the FIRST data row was written. A stream has read
        # the header and that one row (2); loading the whole source first would have read all 51
        (self.root / "facts").mkdir()
        with open(self.root / "facts" / "facts.csv", "w", newline="") as f:
            out = csv.DictWriter(f, fieldnames=s6_assemble.FACTS_HEADER)
            out.writeheader()
            out.writerows([{**fact_row("oac", "3b", {}), "surname": f"name{i}"} for i in range(50)])
        read, at_write = [0], []
        real_reader, real_writer = csv.reader, csv.writer

        def counting_reader(handle):
            def rows():
                for row in real_reader(handle):
                    read[0] += 1
                    yield row
            return rows()

        def counting_writer(handle):
            inner = real_writer(handle)

            class Counting:
                def writerow(self, row):
                    at_write.append(read[0])
                    inner.writerow(row)
            return Counting()
        chunks = 4
        with mock.patch.object(s6_assemble.csv, "reader", counting_reader), mock.patch.object(s6_assemble.csv, "writer", counting_writer):
            self.assertEqual(s6_assemble.split_by_chunk("facts", s6_assemble.FACTS_HEADER, chunks), 50)
        self.assertEqual(len(at_write), chunks + 50)                    # a header per chunk file, then a write per row
        self.assertEqual(at_write[chunks], 2)                           # the first data row was written after reading the header and it

    def test_a_source_with_the_wrong_columns_is_refused_not_split_wrongly(self):
        (self.root / "facts").mkdir()
        (self.root / "facts" / "facts.csv").write_text("name,fact,data\nsmith,oac,{}\n")          # the PUBLIC table's columns, not stage 5's
        with self.assertRaises(SystemExit) as stopped:
            s6_assemble.split_by_chunk("facts", s6_assemble.FACTS_HEADER, 3)
        self.assertIn("expected", str(stopped.exception))


class Stage6EndToEnd(unittest.TestCase):
    """Runs real stages 1-6 on a small fake database - checking the pieces fit together, the same way
    test_stage234.py's Stage234EndToEnd does for stages 2-4."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        db_path = cls.root / "test.db"
        fake_data.generate(persons=8000, surnames=200, seed=1, path=db_path, quiet=True)     # seed chosen to include a Scottish substitute (see the copyOf test below)
        cls.chunks = 4
        cls.patches = [mock.patch.object(config, "WORK", cls.root), mock.patch.dict(config.PROFILES["fake"], {"database": str(db_path)}),
                       mock.patch.object(config, "RUN_CHUNKS", cls.chunks)]
        for p in cls.patches:
            p.start()

        with mock.patch.object(sys, "argv", ["s1_counts"]):
            s1_counts.main()
        with mock.patch.object(sys, "argv", ["s2_surfaces"]):
            s2_surfaces.main()
        with mock.patch.object(sys, "argv", ["s3_extracts", "--chunks", str(cls.chunks)]):
            s3_extracts.main()
        for chunk in range(cls.chunks):
            with mock.patch.object(sys, "argv", ["s4_maps", "--chunk", str(chunk), "--chunks", str(cls.chunks)]):
                s4_maps.main()
        with mock.patch.object(sys, "argv", ["s5_facts"]):
            s5_facts.main()

        with mock.patch.object(sys, "argv", ["s6_assemble", "--prepare", "--chunks", str(cls.chunks)]):
            s6_assemble.main()
        for chunk in range(cls.chunks):
            with mock.patch.object(sys, "argv", ["s6_assemble", "--chunk", str(chunk), "--chunks", str(cls.chunks)]):
                s6_assemble.main()
        with mock.patch.object(sys, "argv", ["merge_release", "--chunks", str(cls.chunks), "--reference",
                                            str(config.ROOT / "pipeline" / "reference" / "scotland_outline.geojson")]):
            merge_release.main()          # no --synthetic: this is fake data standing in for a real run, not a
                                          # flagged sample release - s6_assemble's own bundles never set that key

    @classmethod
    def tearDownClass(cls):
        for p in cls.patches:
            p.stop()
        cls.tmp.cleanup()

    def all_files(self):
        return sorted((self.root / "release" / "names").glob("*/*.json"))

    def test_every_listed_name_gets_a_file_and_no_others_do(self):
        with open(self.root / "names.csv", newline="") as f:
            listed = {row["surname"] for row in csv.DictReader(f)}
        found = {p.stem for p in self.all_files()}
        self.assertTrue(listed, "fake data produced no names above threshold - check the seed")
        self.assertEqual(found, listed)

    def test_a_file_sits_in_the_folder_named_after_its_first_two_letters(self):
        for path in self.all_files():
            self.assertEqual(path.parent.name, path.stem[:2])

    def test_the_index_lists_exactly_the_files_that_exist(self):
        found = {p.stem for p in self.all_files()}
        listed = set()
        for path in (self.root / "release" / "index").glob("*.json"):
            listed |= set(json.loads(path.read_text()))
        self.assertEqual(listed, found)

    def test_a_bundle_carries_counts_for_every_year_not_only_mapped_ones(self):
        with open(self.root / "counts.csv", newline="") as f:
            by_name = {}
            for row in csv.DictReader(f):
                by_name.setdefault(row["surname"], set()).add((row["source"], row["year"]))
        for path in self.all_files()[:20]:               # a sample is enough; every file goes through the same code
            bundle = json.loads(path.read_text())
            got = {(source, year) for source, years in bundle["counts"].items() for year in years}
            self.assertEqual(got, by_name[bundle["name"]], bundle["name"])

    def test_scotland_periods_that_are_copies_name_a_period_with_its_own_geometry(self):
        # not asserting a copy must exist at all - depends on the fake data's random Scottish shares, the
        # same call test_stage234.py's own substitute test makes - just that when one does, it is genuine:
        # the period it names is itself present, in this same file, and is not itself a copy
        checked_at_least_one = False
        for path in self.all_files():
            bundle = json.loads(path.read_text())
            for pid in ("1911", "1921"):
                m = bundle["maps"].get(pid)
                if m is None or "copyOf" not in m:
                    continue
                checked_at_least_one = True
                reference = bundle["maps"].get(m["copyOf"])
                self.assertIsNotNone(reference, f"{bundle['name']} {pid}: copyOf names a period with no map of its own")
                self.assertNotIn("copyOf", reference, f"{bundle['name']} {pid}: copyOf names a copy, not an original")
        if not checked_at_least_one:
            self.skipTest("no substituted period in this fake-data run - nothing to check")

    def test_preview_web_draws_real_assembled_files(self):
        # the hand-built bundle in PreviewWebTests has one simple triangle; this is the real GeoJSON stage 4
        # wrote (multipolygons, holes, real lon/lat) going through the same page
        out = self.root / "web.html"
        with mock.patch.object(sys, "argv", ["preview_web", "--sample", "3", "--seed", "1", "--out", str(out),
                                            "--names-dir", str(self.root / "release" / "names")]):
            preview_web.main()
        page = out.read_text()
        self.assertEqual(page.count("<h2>"), 3)
        self.assertGreaterEqual(page.count("<svg"), 3)
        self.assertGreaterEqual(page.count("<path"), 3)
        self.assertNotIn("nan", page.lower().replace("nation", ""))            # no NaN coordinates from a bad projection

    def facts_table(self):
        with open(self.root / "release" / "facts.csv", newline="") as f:
            return list(csv.DictReader(f))

    def test_name_files_hold_counts_and_maps_and_the_facts_are_one_table(self):
        for path in self.all_files():
            self.assertNotIn("facts", json.loads(path.read_text()), path.name)
        table = self.facts_table()
        self.assertTrue(table, "the fake data should have given some facts")
        self.assertEqual([(r["name"], r["fact"]) for r in table], sorted((r["name"], r["fact"]) for r in table))   # sorted, so it can be streamed
        self.assertLessEqual({r["name"] for r in table}, {p.stem for p in self.all_files()})                   # only published names
        for row in table:
            json.loads(row["data"])                                                                            # every data cell is JSON

    def test_the_facts_table_has_the_same_facts_as_stage_5_made(self):
        with open(self.root / "facts" / "facts.csv", newline="") as f:
            made = {(r["surname"], r["fact"]) for r in csv.DictReader(f)}
        published = {p.stem for p in self.all_files()}
        wanted = {(name, {"ethnicity": "eth", "parishes": "places", "places": "places", "imd_score": "imd",
                          "forenames_register": "forenames", "forenames_census": "forenames"}.get(fact, fact))
                  for name, fact in made if name in published}
        self.assertEqual({(r["name"], r["fact"]) for r in self.facts_table()}, wanted)

    def test_validate_data_accepts_the_whole_release(self):
        manifest = json.loads((self.root / "release" / "manifest.json").read_text())
        lookups = self.minimal_lookups(manifest)
        (self.root / "release" / "lookups.json").write_text(json.dumps(lookups))
        report = validate_data.Report()
        validate_data.check_manifest(manifest, self.root / "release", report)
        validate_data.check_lookups(lookups, report)
        self.assertEqual(report.errors, [], report.errors)
        for path in self.all_files():
            validate_data.check_bundle(path, manifest, lookups, manifest["threshold"], report)
        self.assertEqual(report.errors, [], report.errors)
        rows = validate_data.check_facts_table(self.root / "release" / "facts.csv", {p.stem for p in self.all_files()}, lookups, report)
        self.assertEqual(report.errors, [], report.errors)
        self.assertEqual(rows, len(self.facts_table()))

    def minimal_lookups(self, manifest):
        """Just enough lookups.json for every code actually produced in this run to be found - lookups.json
        itself is out of scope for stage 6 (its wording needs a person, not the database), but validating
        assemble's own output still needs some lookup table to check group codes against."""
        codes = {"oac": set(), "loac": set(), "fpc": set(), "eth": set()}
        for row in self.facts_table():
            fact, data = row["fact"], json.loads(row["data"])
            if fact in ("oac", "loac", "fpc"):
                codes[fact].add(data["group"])
            if fact == "eth":
                codes["eth"].add(str(data["group"]))
        lookups = {"schema": 1, "eth": {c: {"name": c} for c in codes["eth"]}, "scales": {}}
        for scheme in ("oac", "loac"):
            lookups[scheme] = {"supergroups": {"x": {"name": "x", "colour": "#000"}},
                               "groups": {c: {"name": c, "colour": "#000", "supergroup": "x"} for c in codes[scheme]}}
        lookups["fpc"] = {"groups": {c: {"name": c, "colour": "#000"} for c in codes["fpc"]}}
        for scale in ("imd", "ahah"):
            lookups["scales"][scale] = {"colours": ["#000"] * 10}
        return lookups


class ValidatorCopyOfChecks(unittest.TestCase):
    """tools/validate_data.py's rules for a map that is a copy of another year's (copyOf) - the validator's
    own logic, checked on hand-built bundles, separately from Stage6EndToEnd (which only shows that what
    assemble writes passes, never that a bad file would be caught)."""

    MANIFEST = {"schema": 1, "release": {"version": "t", "synthetic": False}, "threshold": 100,
               "sources": {"census": {"label": "c", "short": "c", "counts": "c", "coverage": [1851, 1921]}},
               "periods": [{"id": "1901", "year": 1901, "source": "census"}, {"id": "1911", "year": 1911, "source": "census"},
                           {"id": "1921", "year": 1921, "source": "census"}],
               "levels": [{"level": 1}, {"level": 2}, {"level": 3}]}
    SHAPE = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"level": 1},
             "geometry": {"type": "Polygon", "coordinates": [[[-3, 55], [-2, 55], [-2, 56], [-3, 55]]]}}]}

    def errors_for(self, counts, maps):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "names" / "sm" / "smith.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"schema": 1, "name": "smith", "counts": {"census": counts}, "maps": maps}))
            report = validate_data.Report()
            validate_data.check_bundle(path, self.MANIFEST, {}, 100, report)
            return report.errors

    def copy(self, of):
        return {**self.SHAPE, "copyOf": of}

    def test_a_valid_copy_passes_even_when_its_own_years_count_is_below_the_threshold(self):
        # the whole reason a copy exists: this year's own count (Scotland missing) is not a fair picture -
        # so the disclosure guard has to look at the year whose geometry is actually shown
        errors = self.errors_for({"1901": 500, "1911": 40}, {"1901": self.SHAPE, "1911": self.copy("1901")})
        self.assertEqual(errors, [])

    def test_a_copy_whose_reference_year_is_below_the_threshold_is_refused(self):
        errors = self.errors_for({"1901": 40, "1911": 500}, {"1901": self.SHAPE, "1911": self.copy("1901")})
        self.assertTrue([e for e in errors if "maps.1911" in e and "below the threshold" in e], errors)

    def test_a_plain_map_below_the_threshold_is_still_refused(self):
        errors = self.errors_for({"1901": 40}, {"1901": self.SHAPE})
        self.assertTrue([e for e in errors if "maps.1901" in e and "below the threshold" in e], errors)

    def test_copyof_naming_a_period_that_is_not_in_the_manifest_is_refused(self):
        errors = self.errors_for({"1901": 500, "1911": 500}, {"1901": self.SHAPE, "1911": self.copy("1999")})
        self.assertTrue([e for e in errors if "maps.1911" in e and "not a period in the manifest" in e], errors)

    def test_copyof_naming_a_period_with_no_map_in_this_file_is_refused(self):
        errors = self.errors_for({"1901": 500, "1911": 500}, {"1911": self.copy("1901")})
        self.assertTrue([e for e in errors if "maps.1911" in e and "no map of its own" in e], errors)

    def test_a_copy_of_a_copy_is_refused(self):
        maps = {"1901": self.SHAPE, "1911": self.copy("1901"), "1921": self.copy("1911")}
        errors = self.errors_for({"1901": 500, "1911": 500, "1921": 500}, maps)
        self.assertTrue([e for e in errors if "maps.1921" in e and "itself a copy" in e], errors)


class ValidatorFactsTable(unittest.TestCase):
    """tools/validate_data.py's checks of facts.csv (name, fact, data), on hand-built tables."""

    LOOKUPS = {"oac": {"groups": {"3b": {}}}, "eth": {"WBR": {}}}

    def errors_for(self, text, names=("alpha", "beta")):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.csv"
            path.write_text(text)
            report = validate_data.Report()
            validate_data.check_facts_table(path, set(names), self.LOOKUPS, report)
            return report.errors

    GOOD = 'name,fact,data\nalpha,oac,"{""group"":""3b""}"\nbeta,eth,"{""group"":""WBR""}"\n'

    def test_a_good_table_passes(self):
        self.assertEqual(self.errors_for(self.GOOD), [])

    def test_a_wrong_header_is_refused(self):
        self.assertTrue([e for e in self.errors_for("surname,fact,data\n") if "header" in e])

    def test_a_name_with_no_file_is_refused(self):
        errors = self.errors_for(self.GOOD + 'zulu,oac,"{""group"":""3b""}"\n')
        self.assertTrue([e for e in errors if "zulu" in e and "no file" in e], errors)

    def test_an_unsorted_or_repeated_row_is_refused(self):
        unsorted = 'name,fact,data\nbeta,eth,"{""group"":""WBR""}"\nalpha,oac,"{""group"":""3b""}"\n'
        self.assertTrue([e for e in self.errors_for(unsorted) if "sorted" in e])
        repeated = 'name,fact,data\nalpha,oac,"{""group"":""3b""}"\nalpha,oac,"{""group"":""3b""}"\n'
        self.assertTrue([e for e in self.errors_for(repeated) if "sorted" in e])

    def test_data_that_is_not_json_is_refused(self):
        self.assertTrue([e for e in self.errors_for("name,fact,data\nalpha,oac,not json\n") if "not valid JSON" in e])

    def test_a_group_code_that_is_not_in_lookups_is_refused_just_as_inside_a_name_file(self):
        errors = self.errors_for('name,fact,data\nalpha,oac,"{""group"":""9z""}"\n')
        self.assertTrue([e for e in errors if "9z" in e and "not in lookups" in e], errors)

    def test_a_row_with_the_wrong_number_of_columns_is_refused(self):
        self.assertTrue([e for e in self.errors_for("name,fact,data\nalpha,oac\n") if "3 columns" in e])


class DemoReleaseTool(unittest.TestCase):
    """tools/build_demo_release.py: fake data through stages 1-6 and the preview page, in a folder of its own."""

    def run_tool(self, folder, **env):
        return subprocess.run([sys.executable, str(config.ROOT / "tools" / "build_demo_release.py"), "--folder", str(folder), "--persons", "8000"],
                              cwd=config.ROOT, env={**os.environ, **env}, capture_output=True, text=True)

    def test_it_builds_a_release_and_a_page_whatever_the_shell_says_and_rebuilds_its_own_folder(self):
        # the shell of someone working in the TRE has GBNAMES_PROFILE=tre and run.settings' variables set; a typo in one
        # of them would stop a run that read it, and the profile would point at the real database - neither may matter here
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "demo"
            done = self.run_tool(folder, GBNAMES_PROFILE="tre", GBNAMES_SOURCES="nonsense", GBNAMES_CHUNKS="many")
            self.assertEqual(done.returncode, 0, done.stderr[-2000:])
            page = (folder / "preview_web" / "preview.html").read_text()
            self.assertIn("<svg", page)
            self.assertTrue(list((folder / "release" / "names").glob("*/*.json")))
            self.assertTrue((folder / "release" / "facts.csv").exists())
            (folder / "stray.txt").write_text("left over")                    # a folder it made itself is cleared and rebuilt
            self.assertEqual(self.run_tool(folder).returncode, 0)
            self.assertFalse((folder / "stray.txt").exists())

    def test_it_will_not_empty_a_folder_it_did_not_make(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "precious"
            folder.mkdir()
            (folder / "thesis.txt").write_text("keep me")
            done = self.run_tool(folder)
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("not being cleared", done.stderr + done.stdout)
            self.assertEqual((folder / "thesis.txt").read_text(), "keep me")


class ValidatorWithoutLookups(unittest.TestCase):
    """--skip-lookups: a release straight out of stage 6 has no lookups.json (its wording is a person's job, later), and the
    validator is the only thing that can check 390,000 files before they leave the TRE - so it has to run without one,
    and still catch everything that is not "is this group code in lookups.json"."""

    SHAPE = ValidatorCopyOfChecks.SHAPE

    def release(self, tmp, counts=None, maps=None, facts_csv='name,fact,data\nsmith,oac,"{""group"":""ZZ9""}"\n'):
        root = Path(tmp)
        (root / "names" / "sm").mkdir(parents=True)
        (root / "index").mkdir()
        (root / "masks").mkdir()
        (root / "masks" / "scotland.json").write_text(json.dumps({"type": "FeatureCollection", "features": []}))
        (root / "manifest.json").write_text(json.dumps(merge_release.build_manifest("t")))
        bundle = {"schema": 1, "name": "smith", "counts": counts or {"census": {"1901": 500}}, "maps": maps or {"1901": self.SHAPE}}
        (root / "names" / "sm" / "smith.json").write_text(json.dumps(bundle))
        (root / "index" / "sm.json").write_text(json.dumps(["smith"]))
        (root / "facts.csv").write_text(facts_csv)
        return root

    def validate(self, root, *flags):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["validate_data", str(root), *flags]), contextlib.redirect_stdout(out):
            code = validate_data.main()
        return code, out.getvalue()

    def test_without_the_flag_a_missing_lookups_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, text = self.validate(self.release(tmp))
            self.assertEqual(code, 1)
            self.assertIn("lookups.json", text)

    def test_with_the_flag_a_good_release_passes_and_says_what_it_did_not_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, text = self.validate(self.release(tmp), "--skip-lookups")
            self.assertEqual(code, 0, text)
            self.assertIn("not checked (--skip-lookups)", text)
            self.assertIn("OK: 1 names", text)                             # the unknown group code ZZ9 was not held against anyone

    def test_with_the_flag_everything_else_is_still_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, text = self.validate(self.release(tmp, counts={"census": {"1901": 40}}), "--skip-lookups")     # below the threshold
            self.assertEqual(code, 1)
            self.assertIn("below the threshold", text)
        with tempfile.TemporaryDirectory() as tmp:
            code, text = self.validate(self.release(tmp, facts_csv='name,fact,data\nnobody,oac,"{""group"":""3b""}"\n'), "--skip-lookups")
            self.assertEqual(code, 1)
            self.assertIn("no file", text)                                 # facts for a name that is not published
        with tempfile.TemporaryDirectory() as tmp:
            bad = {"1901": {**self.SHAPE, "features": [{**self.SHAPE["features"][0], "geometry": {"type": "Polygon", "coordinates": [[[400000, 500000], [400100, 500000], [400100, 500100], [400000, 500000]]]}}]}}
            code, text = self.validate(self.release(tmp, maps=bad), "--skip-lookups")                          # British National Grid metres
            self.assertEqual(code, 1)
            self.assertIn("not longitude/latitude", text)

    def test_with_the_flag_a_broken_manifest_still_stops_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.release(tmp)
            manifest = json.loads((root / "manifest.json").read_text())
            manifest["masks"]["scotland"]["url"] = "masks/not_there.json"
            (root / "manifest.json").write_text(json.dumps(manifest))
            code, text = self.validate(root, "--skip-lookups")
            self.assertEqual(code, 1)
            self.assertIn("does not exist", text)

    def test_the_lookups_checks_are_only_skipped_not_invented(self):
        errors = []
        report = validate_data.Report()
        validate_data.check_facts({"oac": {"group": "ZZ9"}, "eth": {"group": "QQQ"}}, None, "x", report)
        self.assertEqual(report.errors, [])
        validate_data.check_facts({"oac": {"group": "ZZ9"}}, {"oac": {"groups": {"3b": {}}}}, "x", report)      # with lookups it is still an error
        self.assertTrue([e for e in report.errors if "ZZ9" in e])


class MergeReleaseTests(unittest.TestCase):
    def test_index_groups_by_first_two_letters_and_sorts(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = Path(tmp) / "parts"
            parts.mkdir()
            (parts / "chunk_0.txt").write_text("smith\nsmythe\nsmyth\nsmithers\n")
            (parts / "chunk_1.txt").write_text("jones\nsmithson\nsmitherman\nsmithy\nsmithe\nsmithfield\n")
            by_prefix = merge_release.build_index(parts, Path(tmp) / "out")
            self.assertEqual(set(by_prefix), {"sm", "jo"})
            self.assertEqual(by_prefix["jo"], {"jones"})
            written = json.loads((Path(tmp) / "out" / "index" / "sm.json").read_text())
            self.assertEqual(len(written), 9)
            self.assertEqual(written, sorted(written))       # tools/validate_data.py refuses an unsorted index; nine names make a lucky set order a 1 in 362,880 chance

    def write_part(self, folder, number, rows):
        path = Path(folder) / f"chunk_{number}.csv"
        with open(path, "w", newline="") as f:
            out = csv.writer(f)
            out.writerow(["name", "fact", "data"])
            out.writerows(rows)

    def test_the_facts_table_merges_sorted_parts_into_one_sorted_file_with_one_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = Path(tmp) / "parts"
            parts.mkdir()
            self.write_part(parts, 0, [["alpha", "oac", "{}"], ["gamma", "imd", "{}"], ["gamma", "oac", "{}"]])
            self.write_part(parts, 1, [["beta", "oac", "{}"], ["delta", "eth", "{}"]])
            self.write_part(parts, 2, [["beta", "ahah", "{}"], ["zeta", "oac", "{}"]])
            out = Path(tmp) / "facts.csv"
            n = merge_release.build_facts_table(parts, out)
            with open(out, newline="") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], ["name", "fact", "data"])
            self.assertEqual(n, 7)
            self.assertEqual([tuple(r[:2]) for r in rows[1:]], [("alpha", "oac"), ("beta", "ahah"), ("beta", "oac"), ("delta", "eth"),
                                                                ("gamma", "imd"), ("gamma", "oac"), ("zeta", "oac")])
            self.assertEqual(sum(r == ["name", "fact", "data"] for r in rows), 1)            # the parts' own headers are not repeated

    def test_a_json_cell_with_commas_and_quotes_survives_the_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = Path(tmp) / "parts"
            parts.mkdir()
            data = json.dumps({"group": "3b", "distribution": {"3b": 0.5, "2a": 0.5}, "note": 'say "hi", ok'})
            self.write_part(parts, 0, [["alpha", "oac", data]])
            merge_release.build_facts_table(parts, Path(tmp) / "facts.csv")
            with open(Path(tmp) / "facts.csv", newline="") as f:
                self.assertEqual(json.loads(list(csv.DictReader(f))[0]["data"]), json.loads(data))

    def test_scotland_mask_is_reprojected_to_longitude_latitude(self):
        mask = merge_release.build_scotland_mask(config.ROOT / "pipeline" / "reference" / "scotland_outline.geojson")
        self.assertEqual(mask["type"], "FeatureCollection")
        self.assertTrue(mask["features"])
        lon, lat = mask["features"][0]["geometry"]["coordinates"][0][0][0][:2]
        self.assertTrue(-9 <= lon <= 2.5 and 49.5 <= lat <= 61.5, (lon, lat))     # the GB box, not BNG metres

    def test_manifest_marks_1911_and_1921_with_the_scotland_mask(self):
        manifest = merge_release.build_manifest("1.2.3")
        by_id = {p["id"]: p for p in manifest["periods"]}
        for pid in ("1911", "1921"):
            self.assertEqual(by_id[pid]["mask"], "scotland", pid)
        self.assertNotIn("mask", by_id["1901"])
        self.assertEqual(manifest["release"]["version"], "1.2.3")


class PreviewWebTests(unittest.TestCase):
    def test_project_keeps_britain_inside_the_panel_box_and_flips_y_so_north_is_up(self):
        x_low, y_low = preview_web._project(-8.0, 50.0)           # south-west corner-ish
        x_high, y_high = preview_web._project(-8.0, 60.0)         # further north, same longitude
        self.assertLess(y_high, y_low)                             # further north -> smaller y (nearer the top)
        self.assertTrue(0 <= x_low <= preview_web.PANEL_W)

    def test_rings_handles_polygon_and_multipolygon_alike(self):
        polygon = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
        multi = {"type": "MultiPolygon", "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 0]]], [[[2, 2], [3, 2], [3, 3], [2, 2]]]]}
        self.assertEqual(len(list(preview_web._rings(polygon))), 1)
        self.assertEqual(len(list(preview_web._rings(multi))), 2)

    def test_a_copied_map_says_which_year_it_shows(self):
        shape = {"type": "FeatureCollection", "features": []}
        block = preview_web.maps_block({"maps": {"1901": shape, "1911": {**shape, "copyOf": "1901"}}})
        self.assertIn("1911 - shows 1901&#x27;s map", block)          # html-escaped apostrophe
        self.assertNotIn("1901 - shows", block)                        # the original itself is not labelled a copy

    def test_a_maps_caption_carries_that_years_bearers(self):
        shape = {"type": "FeatureCollection", "features": []}
        block = preview_web.maps_block({"maps": {"1901": shape, "2026": shape}, "counts": {"census": {"1901": 1234}, "register": {"2026": 56}}})
        self.assertIn("1901: 1,234", block)
        self.assertIn("2026: 56", block)

    def test_counts_are_one_line_per_source_with_every_year(self):
        block = preview_web.counts_block({"counts": {"census": {"1851": 68, "1861": 81}, "register": {"1997": 1200}}})
        self.assertIn("1851: 68", block)
        self.assertIn("1861: 81", block)
        self.assertIn("1997: 1,200", block)
        self.assertEqual(block.count("<p"), 2)                          # one line each for census and register, not a row per year

    def test_facts_read_as_text_not_json(self):
        bundle = {"facts": {"forenames": {"register": {"f": ["mary", "ann"], "m": ["john"]}},
                            "oac": {"group": "3b", "distribution": {"2a": 0.10, "3b": 0.85, "6c": 0.004}},
                            "ahah": {"mode": 6, "distribution": [0.1, 0.9] + [0.0] * 8},
                            "eth": {"group": "WBR", "countries": [["WBR-EN", 0.4]]},
                            "places": {"census": [{"area": "Kent", "name": "Dover"}]}}}
        table = preview_web.facts_table(bundle)
        self.assertIn("f: mary, ann; m: john", table)                       # names run on
        self.assertIn("3b 85%, 2a 10%, 6c &lt;1%", table)                    # biggest share first, a tiny one as <1%
        self.assertIn("1: 10%, 2: 90%", table)                              # a decile distribution in order
        self.assertIn("WBR-EN 40%", table)
        self.assertIn("Kent / Dover", table)
        self.assertNotIn("{", table)                                        # no JSON braces on the page

    def test_a_panel_is_drawn_over_the_coastline_when_there_is_one(self):
        shape = {"type": "FeatureCollection", "features": []}
        with_land = preview_web.panel(shape, "1901", land=True)
        self.assertIn('href="#gbland"', with_land)                               # drawn from the one definition on the page
        self.assertLess(with_land.index("gbland"), with_land.index("</svg>"))
        self.assertNotIn("gbland", preview_web.panel(shape, "1901"))
        self.assertIn('href="#gbland"', preview_web.maps_block({"maps": {"1901": shape}}, land=True))
        self.assertIn('<path id="gbland" d="M1,2L3,4Z"/>', preview_web.land_defs("M1,2L3,4Z"))
        self.assertEqual(preview_web.land_defs(""), "")

    def test_the_page_defines_the_coastline_once_however_many_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            names_dir = Path(tmp) / "names"
            (names_dir / "sm").mkdir(parents=True)
            shape = {"type": "FeatureCollection", "features": []}
            (names_dir / "sm" / "smith.json").write_text(json.dumps({"schema": 1, "name": "smith", "counts": {},
                                                                     "maps": {"1901": shape, "1911": shape, "1921": shape}}))
            out = Path(tmp) / "out.html"
            with mock.patch.object(sys, "argv", ["preview_web", "--names", "smith", "--names-dir", str(names_dir), "--out", str(out)]):
                preview_web.main()
            page = out.read_text()
            self.assertEqual(page.count('id="gbland"'), 1)
            self.assertEqual(page.count('href="#gbland"'), 3)

    def test_the_coastline_is_a_few_pieces_of_longitude_latitude_and_becomes_one_path(self):
        doc = json.loads((config.REFERENCE / "gb_outline_lonlat.geojson").read_text())
        lon_lat = [p for f in doc["features"] for ring in preview_web._rings(f["geometry"]) for p in ring]
        self.assertTrue(all(-9 <= lon <= 2.5 and 49.5 <= lat <= 61.5 for lon, lat in lon_lat))     # not British National Grid metres
        self.assertLess((config.REFERENCE / "gb_outline_lonlat.geojson").stat().st_size, 60_000)   # a rough outline, not the 470 KB coast
        path = preview_web.land_path()
        self.assertTrue(path.startswith("M") and path.count("Z") >= 5)
        self.assertEqual(preview_web.land_path(Path("/nonexistent.geojson")), "")                  # no coastline file: maps still draw, without it

    def test_a_bundle_with_no_map_is_reported_but_does_not_crash(self):
        self.assertEqual(preview_web.maps_block({"maps": {}}), "<p><i>no maps at all - should not happen for a published file</i></p>")

    def test_facts_table_shows_every_fact_and_no_technical_keys_leak_in(self):
        table = preview_web.facts_table({"facts": {"oac": {"group": "3b"}}})
        self.assertIn("oac", table)
        self.assertIn("3b", table)

    def test_read_facts_table_picks_out_only_the_wanted_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.csv"
            path.write_text('name,fact,data\nalpha,oac,"{""group"":""3b""}"\nbeta,oac,"{""group"":""2a""}"\nbeta,eth,"{""group"":""WBR""}"\n')
            found = preview_web.read_facts_table(path, ["beta"])
            self.assertEqual(found, {"beta": {"oac": {"group": "2a"}, "eth": {"group": "WBR"}}})
            self.assertEqual(preview_web.read_facts_table(Path(tmp) / "missing.csv", ["beta"]), {})

    def test_the_page_shows_facts_from_the_table_when_the_name_file_has_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            names_dir = Path(tmp) / "names"
            (names_dir / "sm").mkdir(parents=True)
            (names_dir / "sm" / "smith.json").write_text(json.dumps({"schema": 1, "name": "smith", "counts": {}, "maps": {}}))
            (Path(tmp) / "facts.csv").write_text('name,fact,data\nsmith,oac,"{""group"":""7q""}"\n')
            out = Path(tmp) / "out.html"
            with mock.patch.object(sys, "argv", ["preview_web", "--names", "smith", "--names-dir", str(names_dir),
                                                "--facts-file", str(Path(tmp) / "facts.csv"), "--out", str(out)]):
                preview_web.main()
            self.assertIn("7q", out.read_text())

    def test_end_to_end_on_a_hand_built_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            names_dir = Path(tmp) / "names"
            (names_dir / "sm").mkdir(parents=True)
            bundle = {"schema": 1, "name": "smith", "counts": {"register": {"2026": 500}},
                     "maps": {"2026": {"type": "FeatureCollection",
                                       "features": [{"type": "Feature", "properties": {"level": 1},
                                                     "geometry": {"type": "Polygon", "coordinates": [[[-3, 55], [-2, 55], [-2, 56], [-3, 55]]]}}]}},
                     "facts": {"oac": {"group": "3b"}}}
            (names_dir / "sm" / "smith.json").write_text(json.dumps(bundle))
            out = Path(tmp) / "out.html"
            with mock.patch.object(sys, "argv", ["preview_web", "--names", "smith", "--names-dir", str(names_dir), "--out", str(out)]):
                preview_web.main()
            page = out.read_text()
            self.assertIn("smith", page)
            self.assertIn("<svg", page)
            self.assertIn("3b", page)

    def test_a_name_with_no_file_is_reported_not_crashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.html"
            with mock.patch.object(sys, "argv", ["preview_web", "--names", "nosuchname", "--names-dir", tmp, "--out", str(out)]):
                preview_web.main()          # must not raise
            self.assertNotIn("<h2>nosuchname</h2>", out.read_text())     # the name is still echoed in the command line at the top


if __name__ == "__main__":
    unittest.main()
