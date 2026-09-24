"""Tests for stage 5 (the facts about each name) and the neighbourhood tables.

Run from the project root:   python3 -m unittest discover -s pipeline/tests -t .

Two kinds. The rules (which value wins, when a fact is dropped, what is written) are tested on small
hand-made inputs. Then the whole stage runs on a small fake database, and every fact it writes is
compared with a second calculation done in Python straight from the tables, sharing no code with the
SQL, so a query that joins the wrong column (say, Scotland's deprivation on the 2021 zones) or the
wrong year gives a different answer.
"""
import contextlib
import csv
import io
import json
import sqlite3
import statistics
import sys
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path
from unittest import mock

from pipeline import config, db, fake_data, nbhd_tables, s1_counts, s5_facts, sql
from pipeline.names import forename_clean, surname_key

MIN = config.FACT_MIN_IN_CATEGORY
GB = ("E92000001", "S92000003", "W92000004")


def extract(*items):
    """Saved-extract rows for one name: each item is (values, n) or (values, n, sums)."""
    return [(v, n, list(rest[0]) if rest else []) for v, n, *rest in items]


class PickMode(unittest.TestCase):
    def test_a_clear_winner_is_returned_without_a_tie(self):
        self.assertEqual(s5_facts.pick_mode({"a": 5, "b": 3}, "x"), ("a", False))

    def test_a_tie_is_broken_the_same_way_every_time_and_both_outcomes_occur(self):
        counts = {"a": 4, "b": 4, "c": 1}
        outcomes = {s5_facts.pick_mode(counts, f"name{i}|oac")[0] for i in range(60)}
        self.assertEqual(outcomes, {"a", "b"})                    # never the loser, and neither always
        self.assertEqual(s5_facts.pick_mode(counts, "smith|oac"), s5_facts.pick_mode(counts, "smith|oac"))
        self.assertTrue(s5_facts.pick_mode(counts, "smith|oac")[1])


class ReferenceYear(unittest.TestCase):
    def test_the_latest_register_year_with_enough_bearers(self):
        counts = {("register", 2024, "a"): 120, ("register", 2025, "a"): 99, ("register", 2026, "a"): 100,
                  ("register", 2020, "b"): 100, ("register", 2026, "b"): 99,
                  ("census", 1901, "c"): 500, ("register", 2026, "c"): 40,        # listed for its census bearers only
                  ("register", 2026, "d"): 900}                                   # not one of the names asked for
        self.assertEqual(s5_facts.reference_years(counts, ["a", "b", "c"]), {"a": 2026, "b": 2020})


class ComputeRules(unittest.TestCase):
    def setUp(self):
        self.tally = defaultdict(Counter)
        self.ref = {"smith": 2025}

    def test_deciles_give_the_mode_and_ten_shares(self):
        (row,) = s5_facts.compute_deciles("ahah", {"smith": extract((("3",), 60), (("4",), 40))}, self.ref, self.tally)
        self.assertEqual((row["fact"], row["ref_year"], row["n_bearers"], row["value"]), ("ahah", 2025, 100, "3"))
        self.assertEqual(json.loads(row["detail"]), {"distribution": [0, 0, 0.6, 0.4, 0, 0, 0, 0, 0, 0]})
        self.assertEqual(row["version"], config.FACT_VERSIONS["ahah"])

    def test_a_fact_needs_enough_bearers_in_the_category_it_reports_not_in_total(self):
        for compute in (lambda e: s5_facts.compute_groups("oac", e, self.ref, self.tally),
                        lambda e: s5_facts.compute_deciles("imd", e, self.ref, self.tally)):
            self.assertEqual(compute({"smith": extract((("3",), MIN - 1))}), [])
            self.assertEqual(len(compute({"smith": extract((("3",), MIN))})), 1)
            # many bearers in total, but the most common category is just under the floor: nothing is reported
            spread = extract(*[((str(d),), MIN - 1) for d in range(1, 11)])
            self.assertEqual(compute({"smith": spread}), [])

    def test_coverage_counts_every_bearer_with_a_value_even_where_no_fact_is_reported(self):
        s5_facts.compute_groups("loac", {"smith": extract((("A1",), 2), (("B2",), 2))}, self.ref, self.tally)     # 4 bearers: below the floor
        s5_facts.compute_groups("loac", {"jones": extract((("A1",), 9), (("B2",), 1))}, {"jones": 2025}, self.tally)
        self.assertEqual(self.tally["loac"]["covered"], 4 + 10)
        self.assertEqual(self.tally["loac"]["with_value"], 1)                        # only jones gets a LOAC group

    def test_a_fact_that_few_bearers_have_is_still_reported_when_its_category_is_big_enough(self):
        # LOAC-like: only 11 bearers live in London, but 6 of them in the same group
        (row,) = s5_facts.compute_groups("loac", {"smith": extract((("A1",), MIN + 1), (("B2",), 3), (("C1",), 2))}, self.ref, self.tally)
        self.assertEqual((row["value"], row["n_bearers"]), ("A1", MIN + 1 + 5))

    def test_a_tie_is_flagged_in_the_detail(self):
        (row,) = s5_facts.compute_groups("oac", {"smith": extract((("3b",), 50), (("4a",), 50))}, self.ref, self.tally)
        self.assertTrue(json.loads(row["detail"])["tie"])
        self.assertIn(row["value"], ("3b", "4a"))
        self.assertEqual(self.tally["oac"]["ties"], 1)

    def test_the_deprivation_score_is_the_mean_and_sample_sd_of_the_percentile(self):
        pcts = [(i * 7) % 100 + 1 for i in range(120)]
        rows = extract((("1",), 50, (sum(pcts[:50]), sum(p * p for p in pcts[:50]))),
                       (("2",), 70, (sum(pcts[50:]), sum(p * p for p in pcts[50:]))))
        (row,) = s5_facts.compute_imd_score({"smith": rows}, self.ref, self.tally)
        self.assertEqual(row["value"], round(statistics.mean(pcts), 2))
        self.assertEqual(json.loads(row["detail"])["sd"], round(statistics.stdev(pcts), 2))

    def test_places_are_ordered_capped_and_need_a_few_people(self):
        areas = [((f"E02{i:03d}", "E09000001"), 40 - i) for i in range(14)] + [(("E02999", "E09000001"), config.FACT_MIN_IN_CATEGORY - 1)]
        (row,) = s5_facts.compute_places({"smith": extract(*areas)}, self.ref, self.tally)
        listed = [p["msoa"] for p in json.loads(row["detail"])["places"]]
        self.assertEqual(listed, [f"E02{i:03d}" for i in range(config.PLACES_TOP)])      # most common first, ten only
        self.assertNotIn("E02999", listed)
        self.assertEqual(row["value"], "")
        self.assertNotIn("n", json.loads(row["detail"])["places"][0])                    # no counts are written

    def test_a_small_name_still_lists_a_neighbourhood_that_has_enough_people(self):
        rows = extract((("E02001", "E09000001"), config.FACT_MIN_IN_CATEGORY + 1), (("E02002", "E09000001"), 1), (("E02003", "E09000001"), 2))
        (row,) = s5_facts.compute_places({"smith": rows}, self.ref, self.tally)
        self.assertEqual([p["msoa"] for p in json.loads(row["detail"])["places"]], ["E02001"])
        self.assertEqual(s5_facts.compute_places({"smith": extract((("E02009", "E09000001"), config.FACT_MIN_IN_CATEGORY - 1))}, self.ref, self.tally), [])

    def test_ethnicity_is_the_most_common_group_not_the_most_common_code(self):
        rows = extract((("WBR",), 40), (("WAO-PL",), 30), (("WAO-DE",), 30), (("WAOS-K",), 50))
        (row,) = s5_facts.compute_ethnicity({"smith": rows}, self.ref, self.tally)
        detail = json.loads(row["detail"])
        self.assertEqual((row["value"], row["n_bearers"]), ("WAO", 100))                 # 60 in WAO against 40 in WBR
        self.assertEqual(detail["distribution"], {"WAO": 0.6, "WBR": 0.4})
        self.assertEqual(detail["codes"], [["WBR", 0.4], ["WAO-DE", 0.3], ["WAO-PL", 0.3]])
        self.assertEqual(dict(self.tally["unmapped codes"]), {"WAOS-K": 50})             # not counted, and reported

    def test_a_name_with_no_census_group_big_enough_is_unknown_and_so_is_one_with_none(self):
        ref = {"smith": 2025, "jones": 2025, "brown": 2025, "green": 2025}
        found = s5_facts.compute_ethnicity({"smith": extract((("WBR",), MIN - 1)),
                                            "brown": extract((("WBR",), MIN - 1), (("AIN",), MIN - 1), (("WIR",), MIN - 1)),   # 12 people, no group big enough
                                            "green": extract((("WBR",), MIN + 2), (("AIN",), 3))},                           # 10 people, one group big enough
                                           ref, self.tally)
        got = {r["surname"]: r["value"] for r in found}
        self.assertEqual(got, {"smith": config.ETH_UNKNOWN, "jones": config.ETH_UNKNOWN, "brown": config.ETH_UNKNOWN, "green": "WBR"})
        self.assertEqual(self.tally["ethnicity"]["unknown"], 3)

    def test_forenames_need_a_few_people_and_are_listed_most_common_first(self):
        female = {f"name{i:02d}": 30 - i for i in range(12)}
        female["rare"] = config.FACT_MIN_IN_CATEGORY - 1
        (row,) = s5_facts.compute_forenames({"smith": {"F": female, "M": {"john": 5}}}, ["smith", "nobody"], self.tally)
        detail = json.loads(row["detail"])
        self.assertEqual(detail["f"], [f"name{i:02d}" for i in range(config.FORENAMES_TOP)])
        self.assertEqual(detail["m"], ["john"])
        self.assertEqual((row["ref_year"], row["n_bearers"], row["value"]), ("", "", ""))   # pooled: no reference year

    def test_census_forenames_use_the_same_rules_and_say_which_years_were_pooled(self):
        female = {f"name{i:02d}": 30 - i for i in range(12)}
        female["rare"] = MIN - 1
        (row,) = s5_facts.compute_forenames({"smith": {"F": female, "M": {"john": MIN}}}, ["smith", "nobody"], self.tally,
                                            "forenames_census", [1851, 1901])
        detail = json.loads(row["detail"])
        self.assertEqual((row["fact"], row["version"]), ("forenames_census", "census 1851-1901"))     # the years actually pooled
        self.assertEqual(detail["f"], [f"name{i:02d}" for i in range(config.FORENAMES_TOP)])
        self.assertEqual((detail["m"], detail["years"]), (["john"], [1851, 1901]))
        self.assertEqual((row["ref_year"], row["n_bearers"], row["value"]), ("", "", ""))

    def test_parishes_are_ordered_capped_titled_and_need_enough_people(self):
        parishes = {(f"county {i % 3}", f"parish {i:02d}"): [f"COUNTY {i % 3}", f"Parish {i:02d}", 40 - i] for i in range(14)}
        parishes[("kent", "tiny")] = ["KENT", "Tiny", MIN - 1]
        (row,) = s5_facts.compute_parishes({"smith": parishes}, ["smith", "nobody"], self.tally, [1851, 1861])
        detail = json.loads(row["detail"])
        self.assertEqual([p["parish"] for p in detail["parishes"]], [f"Parish {i:02d}" for i in range(config.PLACES_TOP)])
        self.assertEqual(detail["parishes"][0], {"county": "County 0", "parish": "Parish 00"})      # the county is written in title case
        self.assertNotIn("Tiny", [p["parish"] for p in detail["parishes"]])
        self.assertEqual(detail["years"], [1851, 1861])
        self.assertNotIn("n", detail["parishes"][0])                                                  # no counts are written
        self.assertEqual(s5_facts.compute_parishes({"smith": {("kent", "tiny"): ["KENT", "Tiny", MIN - 1]}}, ["smith"], self.tally, [1851]), [])

    def test_forename_cleaning_follows_the_old_rule(self):
        for raw, clean in [("Anne-Marie", "annemarie"), ("MARY", "mary"), ("J", ""), ("Zoë", "zoë"), ("o'neil", "oneil"),
                           ("12", ""), ("", ""), (None, ""), ("ann  marie", "ann marie")]:
            self.assertEqual(forename_clean(raw), clean, raw)

    def test_ethnicity_groups(self):
        for code, group in [("wao-de", "WAO"), ("OXX-DZ", "OXX"), ("acn", "ACN"), (" WBR ", "WBR"), ("waos-k", None), ("", None)]:
            self.assertEqual(s5_facts.eth_group(code), group, code)


class TheSqlForTheTre(unittest.TestCase):
    """The real database is Postgres and cannot be run here, so at least check that the SQL names the
    right tables and columns, and that Scotland's deprivation is joined on the 2011 zones."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = config.settings("tre")

    def test_deprivation_uses_the_2011_zones_for_scotland_only(self):
        query = sql.fact_counts(self.cfg, "imd", 2025)
        self.assertIn("registers_lookup.nbhd_imd", query)
        self.assertIn("CASE WHEN a.ctry25cd = 'S92000003' THEN a.lsoa11cd ELSE a.lsoa21cd END", query)

    def test_each_fact_joins_the_column_that_matches_its_table(self):
        self.assertIn("t.area_code = a.oa21cd", sql.fact_counts(self.cfg, "oac", 2025))
        self.assertIn("t.area_code = a.oa21cd", sql.fact_counts(self.cfg, "loac", 2025))
        self.assertIn("t.area_code = a.lsoa21cd", sql.fact_counts(self.cfg, "ahah", 2025))
        self.assertIn("registers_lookup.nbhd_fpc", sql.fact_counts(self.cfg, "fpc", 2025))
        self.assertIn("t.area_code = a.lsoa21cd", sql.fact_counts(self.cfg, "fpc", 2025))        # the same zones as AHAH
        self.assertIn("a.msoa21cd, a.lad25cd", sql.fact_counts(self.cfg, "places", 2025))

    def test_the_census_facts_use_the_parish_boundaries_of_their_year_and_the_sex_in_the_att_table(self):
        forenames = sql.census_forename_counts(self.cfg, 1921)
        self.assertIn("census.gb1921 c", forenames)
        self.assertIn("census.gb1921_att a", forenames)
        self.assertIn("spatial.conpar1901 p", forenames)                    # 1921 uses the 1901 boundaries
        self.assertIn("UPPER(SUBSTR(TRIM(a.sex), 1, 1))", forenames)
        self.assertIn("p.conparid <> 0", forenames)                         # the same people as the census counts
        parishes = sql.census_parish_counts(self.cfg, 1851)
        self.assertIn("spatial.conpar1851 p", parishes)
        self.assertIn("GROUP BY c.sname, p.regcnty, p.parish", parishes)     # by name, not by id
        self.assertIn("regexp_replace(lower(c.sname)", sql.census_parish_counts(self.cfg, 1851, surnames=["smith"]))

    def test_ethnicity_comes_from_the_estimate_table_and_forenames_from_the_gender_table(self):
        self.assertIn("registers_derived.lcr_consol_ethest", sql.fact_counts(self.cfg, "eth", 2025))
        self.assertNotIn("lcr_consol2026", sql.fact_counts(self.cfg, "eth", 2025))
        forenames = sql.forename_counts(self.cfg)
        self.assertIn("registers_lookup.lookup_monica", forenames)
        self.assertIn("ROW_NUMBER()", forenames)

    def test_every_query_has_the_same_population_as_the_counts(self):
        for fact in config.FACT_QUERIES:
            query = sql.fact_counts(self.cfg, fact, 2025)
            self.assertIn("a.east1m > 0 AND a.north1m > 0", query)            # a usable postcode
            self.assertIn("a.ctry25cd IN ('E92000001', 'S92000003', 'W92000004')", query)   # Great Britain
            self.assertIn("regexp_replace(lower(r.surname)", sql.fact_counts(self.cfg, fact, 2025, surnames=["smith"]))


class Stage5EndToEnd(unittest.TestCase):
    """Runs the real stages 1 and 5 through their command-line entry points on a small fake database."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.db_path = root / "test.db"
        fake_data.generate(persons=50000, surnames=120, seed=5, path=cls.db_path, quiet=True)
        cls.patches = [mock.patch.object(config, "WORK", root),
                       mock.patch.dict(config.PROFILES["fake"], {"database": str(cls.db_path)})]
        for patch in cls.patches:
            patch.start()
        with mock.patch.object(sys, "argv", ["s1_counts"]):
            s1_counts.main()
        cls.out = root / "facts"
        cls.by_year = {}
        cls.census_cache = {}
        with mock.patch.object(config, "FORENAMES_KEEP", 100_000), mock.patch.object(config, "PARISHES_KEEP", 100_000):
            cls.run_stage5()                                             # no cut, so the lists can be compared exactly
        cls.conn = sqlite3.connect(cls.db_path)
        cls.cfg = dict(config.settings("fake"), database=str(cls.db_path))
        cls.facts = defaultdict(dict)                       # fact -> name -> row
        with open(cls.out / "facts.csv", newline="") as f:
            for row in csv.DictReader(f):
                cls.facts[row["fact"]][row["surname"]] = row
        cls.counts = s5_facts.load_counts()
        cls.names = s5_facts.load_names()
        cls.ref = s5_facts.reference_years(cls.counts, cls.names)
        cls.tables = {k: dict(cls.conn.execute(f"SELECT area_code, {col} FROM nbhd_{k}"))
                      for k, col in (("oac", "oac_group"), ("loac", "loac_group"), ("ahah", "ahah_decile"), ("imd", "imd_decile"),
                                  ("fpc", "fpc_group"))}

    @classmethod
    def run_stage5(cls, *extra):
        with mock.patch.object(sys, "argv", ["s5_facts", "--out-dir", str(cls.out), *extra]):
            s5_facts.main()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        for patch in cls.patches:
            patch.stop()
        cls.tmp.cleanup()

    # -- the independent calculation ------------------------------------------------------------

    def people(self, year, key):
        """(forename, eth, oa, lsoa, lsoa 2011, msoa, district, country) of each register row of this name in this
        year that counts: a usable postcode, in Great Britain. One query per year, kept."""
        if year not in self.by_year:
            grouped = defaultdict(list)
            for row in self.conn.execute("""SELECT r.surname, r.forename, r.eth, a.oa21cd, a.lsoa21cd, a.lsoa11cd, a.msoa21cd,
                                                   a.lad25cd, a.ctry
                                            FROM register r JOIN postcode_lookup a ON a.postcode = r.postcode
                                            WHERE r.first <= ? AND r.last >= ? AND a.easting > 0 AND a.northing > 0
                                              AND a.ctry IN (?, ?, ?)""", (year, year, *GB)):
                grouped[surname_key(row[0])].append(row[1:])
            self.by_year[year] = grouped
        return self.by_year[year].get(key, [])

    def expected(self, fact, key):
        """Counter of the values of one fact among the bearers of a name in its reference year."""
        found = Counter()
        for _, eth, oa, lsoa, lsoa11, msoa, district, country in self.people(self.ref[key], key):
            if fact in ("oac", "loac"):
                value = self.tables[fact].get(oa)
            elif fact in ("ahah", "fpc"):
                value = self.tables[fact].get(lsoa)
            elif fact == "imd":
                value = self.tables["imd"].get(lsoa11 if country == "S92000003" else lsoa)
            elif fact == "ethnicity":
                group = (eth or "").split("-")[0].strip().upper()
                value = group if group in config.ETH_GROUPS else None
            if value is not None:
                found[str(value)] += 1
        return found

    # -- what was written -----------------------------------------------------------------------

    def test_the_output_has_the_documented_shape(self):
        with open(self.out / "facts.csv", newline="") as f:
            self.assertEqual(next(csv.reader(f)), s5_facts.FIELDS)
        for fact, rows in self.facts.items():
            self.assertTrue(rows, fact)
            for row in rows.values():
                json.loads(row["detail"])
                version = config.FACT_VERSIONS[fact]
                if fact in ("forenames_census", "parishes"):          # these say which census years were pooled
                    version = version.format(first=min(config.CENSUS_YEARS), last=max(config.CENSUS_YEARS))
                self.assertEqual(row["version"], version)
        self.assertEqual(set(self.facts), {"oac", "loac", "ahah", "imd", "imd_score", "fpc", "places", "ethnicity", "forenames_register",
                                           "forenames_census", "parishes"})
        report = (self.out / "report.txt").read_text()
        self.assertTrue(report.startswith("names in this run"))
        self.assertIn("bearers covered", report)
        self.assertIn("LOAC covers London only", " ".join(report.split()))            # the reason its share is low, by design

    def test_only_names_with_a_reference_year_get_a_contemporary_fact(self):
        for fact in ("oac", "loac", "ahah", "imd", "imd_score", "fpc", "places", "ethnicity"):
            self.assertLessEqual(set(self.facts[fact]), set(self.ref), fact)
            for key, row in self.facts[fact].items():
                self.assertEqual(int(row["ref_year"]), self.ref[key], (fact, key))

    def test_classifications_match_an_independent_count(self):
        checked = Counter()
        for fact in ("oac", "loac", "ahah", "imd", "fpc"):
            wanted = {k for k in self.ref if max(self.expected(fact, k).values(), default=0) >= MIN}
            self.assertEqual(set(self.facts[fact]), wanted, fact)              # the same names, no more and no fewer
            for key, row in self.facts[fact].items():
                counts, total = self.expected(fact, key), sum(self.expected(fact, key).values())
                detail = json.loads(row["detail"])
                self.assertEqual(int(row["n_bearers"]), total, (fact, key))
                top = [v for v, n in counts.items() if n == max(counts.values())]
                self.assertIn(row["value"], top, (fact, key))
                self.assertEqual(bool(detail.get("tie")), len(top) > 1, (fact, key))
                shares = detail["distribution"]
                if fact in ("ahah", "imd"):
                    shares = {str(d + 1): s for d, s in enumerate(shares) if s}
                self.assertEqual(shares, {v: round(n / total, 3) for v, n in counts.items()}, (fact, key))
                checked[fact] += 1
        self.assertTrue(all(checked[f] >= 5 for f in ("oac", "loac", "ahah", "imd", "fpc")), checked)

    def test_scottish_deprivation_really_is_joined_on_the_2011_zones(self):
        scots = [k for k in self.facts["imd"] if any(p[-1] == "S92000003" for p in self.people(self.ref[k], k))]
        self.assertTrue(scots)
        for key in scots:
            counts = self.expected("imd", key)
            self.assertEqual(int(self.facts["imd"][key]["n_bearers"]), sum(counts.values()))
        # had the 2021 column been used, no Scottish row would find a deprivation value at all
        by_2021 = sum(1 for p in self.people(self.ref[scots[0]], scots[0]) if p[-1] == "S92000003" and p[3] in self.tables["imd"])
        self.assertEqual(by_2021, 0)

    def test_deprivation_score_is_the_mean_and_spread_of_the_percentile(self):
        pct = dict(self.conn.execute("SELECT area_code, imd_pctile FROM nbhd_imd"))
        for key, row in self.facts["imd_score"].items():
            values = [pct[p[3] if p[-1] != "S92000003" else p[4]] for p in self.people(self.ref[key], key)
                      if (p[3] if p[-1] != "S92000003" else p[4]) in pct]
            self.assertEqual(float(row["value"]), round(statistics.mean(values), 2), key)
            self.assertEqual(json.loads(row["detail"])["sd"], round(statistics.stdev(values), 2), key)

    def test_places_match_an_independent_count(self):
        listed = {k for k in self.ref if any(n >= config.FACT_MIN_IN_CATEGORY for n in Counter(p[5] for p in self.people(self.ref[k], k) if p[5]).values())}
        self.assertEqual(set(self.facts["places"]), listed)
        for key, row in self.facts["places"].items():
            counts = Counter(p[5] for p in self.people(self.ref[key], key) if p[5])
            top = sorted(((m, n) for m, n in counts.items() if n >= config.FACT_MIN_IN_CATEGORY), key=lambda mn: (-mn[1], mn[0]))
            self.assertEqual([p["msoa"] for p in json.loads(row["detail"])["places"]],
                             [m for m, _ in top[:config.PLACES_TOP]], key)

    def test_ethnicity_matches_an_independent_count_and_unknown_is_used(self):
        unknown = [k for k, r in self.facts["ethnicity"].items() if r["value"] == config.ETH_UNKNOWN]
        self.assertTrue(unknown)                                            # the fake data has surnames with no estimate
        self.assertEqual(set(self.facts["ethnicity"]), set(self.ref))       # every name with a reference year has an answer
        for key, row in self.facts["ethnicity"].items():
            counts = self.expected("ethnicity", key)
            if max(counts.values(), default=0) < MIN:
                self.assertEqual((row["value"], row["detail"]), (config.ETH_UNKNOWN, "{}"), key)
            else:
                self.assertIn(row["value"], [v for v, n in counts.items() if n == max(counts.values())], key)
        self.assertIn("waos-k".upper(), (self.out / "report.txt").read_text())   # the unusable code is reported

    def test_forenames_are_pooled_over_every_year(self):
        gender = dict(self.conn.execute("SELECT forename, gender FROM forename_gender"))
        rows = self.conn.execute("""SELECT r.surname, r.forename FROM register r JOIN postcode_lookup a ON a.postcode = r.postcode
                                    WHERE a.easting > 0 AND a.northing > 0 AND a.ctry IN (?, ?, ?)""", GB).fetchall()
        pooled = defaultdict(Counter)
        for surname, forename in rows:
            key = surname_key(surname)
            if key in self.facts["forenames_register"] and forename in gender:
                pooled[(key, gender[forename])][forename_clean(forename)] += 1
        for key, row in self.facts["forenames_register"].items():
            detail = json.loads(row["detail"])
            for sex in ("F", "M"):
                common = sorted(((f, n) for f, n in pooled[(key, sex)].items() if n >= config.FACT_MIN_IN_CATEGORY),
                                key=lambda fn: (-fn[1], fn[0]))
                self.assertEqual(detail[sex.lower()], [f for f, _ in common[:config.FORENAMES_TOP]], (key, sex))

    # -- the historic facts ---------------------------------------------------------------------

    def census_people(self):
        """{name: [(year, forename, sex, county, parish)]} for the census people that count (their parish is found in the
        boundaries of their year, and is not id 0), straight from the tables."""
        if not self.census_cache:
            grouped = defaultdict(list)
            for year in config.CENSUS_YEARS:
                boundaries = config.CENSUS_PARISH_BOUNDARIES[year]
                for surname, forename, sex, county, parish in self.conn.execute(f"""
                        SELECT c.sname_clean_stand, c.pname, a.sex, p.regcnty, p.parish FROM gb{year} c
                        JOIN gb{year}_att a ON a.recid = c.recid AND a.source = c.source
                        JOIN conpar{boundaries} p ON p.conparid = a.gid WHERE p.conparid <> 0"""):
                    grouped[surname_key(surname)].append((year, forename, sex, county, parish))
            self.census_cache.update(grouped)
        return self.census_cache

    def test_historic_forenames_are_pooled_over_the_census_years(self):
        people, expected = self.census_people(), {}
        for key in self.names:
            lists = {}
            for sex in ("F", "M"):
                counts = Counter(forename_clean(f) for _, f, s, _, _ in people.get(key, []) if s == sex and forename_clean(f))
                common = sorted(((f, n) for f, n in counts.items() if n >= MIN), key=lambda fn: (-fn[1], fn[0]))
                lists[sex.lower()] = [f for f, _ in common[:config.FORENAMES_TOP]]
            if lists["f"] or lists["m"]:
                expected[key] = lists
        self.assertGreater(len(expected), 20)
        self.assertEqual(set(self.facts["forenames_census"]), set(expected))
        for key, row in self.facts["forenames_census"].items():
            detail = json.loads(row["detail"])
            self.assertEqual({"f": detail["f"], "m": detail["m"]}, expected[key], key)
            self.assertEqual(detail["years"], config.CENSUS_YEARS)

    def test_parishes_are_pooled_by_name_across_the_two_boundary_versions(self):
        people, expected, merged_across_versions = self.census_people(), {}, 0
        for key in self.names:
            counts, versions = Counter(), defaultdict(set)
            for year, _, _, county, parish in people.get(key, []):
                counts[(county.lower(), parish.lower())] += 1
                versions[(county.lower(), parish.lower())].add(config.CENSUS_PARISH_BOUNDARIES[year])
            merged_across_versions += sum(len(v) == 2 for v in versions.values())
            listed = sorted(((n, c, p) for (c, p), n in counts.items() if n >= MIN), key=lambda item: (-item[0], item[1], item[2]))
            if listed:
                expected[key] = [(c.title(), p.title()) for _, c, p in listed[:config.PLACES_TOP]]
        self.assertGreater(merged_across_versions, 20)         # the fake 1851 and 1901 boundaries number the same parishes differently
        self.assertEqual(set(self.facts["parishes"]), set(expected))
        for key, row in self.facts["parishes"].items():
            listed = json.loads(row["detail"])["parishes"]
            self.assertEqual([(p["county"], p["parish"].title()) for p in listed], expected[key], key)
            self.assertEqual(len({(p["county"], p["parish"]) for p in listed}), len(listed), key)      # a parish is listed once

    def test_only_the_chosen_sources_are_worked_out_and_open_a_database(self):
        chosen, real = self.names[:2], db.connect
        for sources, expected, forbidden in (("register", {"oac", "forenames_register"}, {"forenames_census", "parishes"}),
                                             ("census", {"forenames_census", "parishes"}, {"oac", "forenames_register", "places"})):
            opened = []
            out = Path(self.tmp.name) / f"sources_{sources}"

            def spy(group, profile=None):
                opened.append(group)
                return real(group, profile)
            with mock.patch.object(db, "connect", spy), \
                    mock.patch.object(sys, "argv", ["s5_facts", "--out-dir", str(out), "--sources", sources, "--names", *chosen]):
                s5_facts.main()
            with open(out / "facts.csv", newline="") as f:
                got = {r["fact"] for r in csv.DictReader(f)}
            self.assertTrue(expected <= got, (sources, got))
            self.assertFalse(got & forbidden, (sources, got))
            self.assertEqual(set(opened), {sources})                 # the other database is never opened

    def test_leaving_out_a_census_year_pools_the_others_and_says_so(self):
        out = Path(self.tmp.name) / "years_left_out"
        years = [1851, 1861, 1881, 1891, 1901, 1911]                 # 1921 is not loaded yet
        with mock.patch.object(sys, "argv", ["s5_facts", "--out-dir", str(out), "--sources", "census", "--names", *self.names[:3],
                                             "--census-years", *map(str, years)]):
            s5_facts.main()
        with open(out / "facts.csv", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(json.loads(row["detail"])["years"], years)
        self.assertFalse((out / "extract" / "parishes_1921.csv").exists())      # 1921 was never queried

    # -- re-running -----------------------------------------------------------------------------

    def test_the_same_names_give_the_same_facts_again_including_broken_ties(self):
        before = (self.out / "facts.csv").read_bytes()
        self.run_stage5("--compute-only")
        self.assertEqual((self.out / "facts.csv").read_bytes(), before)

    def test_a_saved_extract_is_reused_until_the_names_change(self):
        year = max(self.ref.values())
        keys = sorted(k for k, y in self.ref.items() if y == year)
        args = (self.conn, self.cfg, "oac", year, keys, self.out)
        self.assertIsNone(s5_facts.extract_fact(*args))                           # already there
        self.assertIsInstance(s5_facts.extract_fact(*args, refresh=True), int)    # asked again
        self.assertIsInstance(s5_facts.extract_fact(self.conn, self.cfg, "oac", year, keys[:-1], self.out), int)
        s5_facts.extract_fact(*args)                                              # put it back as it was

    def test_compute_only_refuses_extracts_made_for_other_names(self):
        done = next((self.out / "extract").glob("oac_*.done"))
        original = done.read_text()
        done.write_text("names=000000000000\n")
        try:
            with self.assertRaises(SystemExit) as stopped:
                self.run_stage5("--compute-only", "--facts", "oac")
            self.assertIn("oac", str(stopped.exception))
        finally:
            done.write_text(original)

    def test_a_few_named_names_are_worked_out_on_their_own(self):
        chosen = sorted(self.facts["oac"])[:2] + sorted(self.facts["ethnicity"])[:1]
        out = Path(self.tmp.name) / "facts_names"
        with mock.patch.object(sys, "argv", ["s5_facts", "--out-dir", str(out), "--names", *[n.upper() for n in chosen]]):
            s5_facts.main()
        with open(out / "facts.csv", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual({r["surname"] for r in rows}, set(chosen))
        for row in rows:          # the same answer as in the full run, whichever names are asked for with it
            if row["fact"] != "forenames_register":
                self.assertEqual(row["value"], self.facts[row["fact"]][row["surname"]]["value"], (row["surname"], row["fact"]))
        with mock.patch.object(sys, "argv", ["s5_facts", "--out-dir", str(out), "--names", "nosuchname"]):
            with self.assertRaises(SystemExit) as stopped:
                s5_facts.main()
        self.assertIn("nosuchname", str(stopped.exception))

    def test_a_table_with_a_repeated_key_stops_everything_before_any_query(self):
        with mock.patch.object(db, "fetch", return_value=[(3,)]):
            with self.assertRaises(SystemExit) as stopped:
                s5_facts.check_tables(self.conn, self.cfg, ["oac", "forenames"])
        self.assertIn("appear more than once", str(stopped.exception))


class NeighbourhoodTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "test.db"
        fake_data.generate(persons=8000, surnames=100, seed=9, path=cls.db_path, quiet=True)
        cls.conn = sqlite3.connect(cls.db_path)
        cls.cfg = dict(config.settings("fake"), database=str(cls.db_path))

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def test_the_sql_creates_tables_with_the_columns_in_config(self):
        script = nbhd_tables.ddl(self.cfg, csv_dir="somewhere", replace=True)
        loading = [line for line in script.splitlines() if line.startswith("\\copy")]
        self.assertEqual(len(loading), len(config.NBHD_TABLE_COLUMNS))
        self.assertEqual(len(loading), 5)
        memory = sqlite3.connect(":memory:")
        memory.executescript("\n".join(line for line in script.splitlines() if not line.startswith("\\")))
        for key, columns in config.NBHD_TABLE_COLUMNS.items():
            made = [row[1] for row in memory.execute(f"PRAGMA table_info(nbhd_{key})")]
            self.assertEqual(made, [c for c, _ in columns])
            self.assertIn(f"nbhd_{key}.csv", "".join(loading))

    def test_the_tre_sql_uses_the_tre_table_names(self):
        script = nbhd_tables.ddl(config.settings("tre"))
        self.assertIn("CREATE TABLE registers_lookup.nbhd_imd", script)

    @unittest.skipUnless((config.ROOT / "work" / "neighbourhood" / "manifest.json").exists(),
                         "the prepared tables (tools/prep_neighbourhood.py) are not on this machine")
    def test_the_prepared_files_have_exactly_the_columns_the_tables_expect(self):
        for key, columns in config.NBHD_TABLE_COLUMNS.items():
            with open(config.ROOT / "work" / "neighbourhood" / f"nbhd_{key}.csv", newline="") as f:
                self.assertEqual(next(csv.reader(f)), [c for c, _ in columns], key)

    def test_the_postcode_lookup_gives_what_the_tables_give_for_the_postcodes_codes(self):
        table = {k: {r[0]: r for r in self.conn.execute(f"SELECT * FROM nbhd_{k}")} for k in ("oac", "loac", "ahah", "imd", "fpc")}
        sample = self.conn.execute("""SELECT postcode, ctry, oa21cd, lsoa21cd, lsoa11cd, easting, northing FROM postcode_lookup
                                      WHERE oa21cd <> '' ORDER BY ctry, postcode LIMIT 400""").fetchall()
        sample += self.conn.execute("SELECT postcode, ctry, oa21cd, lsoa21cd, lsoa11cd, easting, northing FROM postcode_lookup "
                                    "WHERE ctry = 'S92000003' AND oa21cd <> '' LIMIT 200").fetchall()
        found = nbhd_tables.lookup(self.conn, self.cfg, [row[0] for row in sample])
        seen_scottish = 0
        for postcode, ctry, oa, lsoa, lsoa11, east, north in sample:
            row = found[postcode]
            self.assertEqual(row["oac_group"], table["oac"][oa][2] if oa in table["oac"] else None, postcode)
            self.assertEqual(row["loac_group"], table["loac"][oa][2] if oa in table["loac"] else None, postcode)
            self.assertEqual(row["ahah_decile"], table["ahah"][lsoa][4] if lsoa in table["ahah"] else None, postcode)
            self.assertEqual(row["fpc_group"], table["fpc"][lsoa][2] if lsoa in table["fpc"] else None, postcode)
            self.assertEqual(row["fpc_cluster"], table["fpc"][lsoa][1] if lsoa in table["fpc"] else None, postcode)
            zone = lsoa11 if ctry == "S92000003" else lsoa                    # Scotland's deprivation is on the 2011 zones
            self.assertEqual(row["imd_decile"], table["imd"][zone][6] if zone in table["imd"] else None, postcode)
            self.assertEqual(row["imd_pctile"], table["imd"][zone][5] if zone in table["imd"] else None, postcode)
            self.assertEqual(bool(row["counts"]), bool(east and north and east > 0 and north > 0 and ctry in GB), postcode)
            seen_scottish += ctry == "S92000003"
        self.assertGreater(seen_scottish, 20)

    def test_the_postcode_lookup_says_plainly_what_is_missing_and_why(self):
        self.assertEqual(nbhd_tables.standard_postcode(" SW1A 1AA"), "sw1a1aa")
        self.assertEqual(nbhd_tables.standard_postcode("g1-1aa"), "g11aa")
        blank = self.conn.execute("SELECT postcode FROM postcode_lookup WHERE (oa21cd = '' OR oa21cd IS NULL) AND easting > 0 "
                                  "AND ctry = 'E92000001' LIMIT 1").fetchone()[0]
        ni = self.conn.execute("SELECT postcode FROM postcode_lookup WHERE ctry = 'N92000002' LIMIT 1").fetchone()[0]
        found = nbhd_tables.lookup(self.conn, self.cfg, [blank, ni, "zz99 9zz"])
        self.assertNotIn("zz999zz", found)
        self.assertIn("not in the postcode directory", "\n".join(nbhd_tables.describe(self.cfg, "ZZ99 9ZZ", None)))
        self.assertIn("the postcode has no such code", "\n".join(nbhd_tables.describe(self.cfg, blank, found[blank])))
        self.assertIn("counted by the pipeline: NO", "\n".join(nbhd_tables.describe(self.cfg, ni, found[ni])))
        scot = nbhd_tables.lookup(self.conn, self.cfg, [self.conn.execute(
            "SELECT postcode FROM postcode_lookup WHERE ctry = 'S92000003' AND oa21cd <> '' LIMIT 1").fetchone()[0]])
        (row,) = scot.values()
        text = "\n".join(nbhd_tables.describe(self.cfg, row["postcode"], row))
        self.assertIn("[joined on lsoa11cd] (Scotland is on the 2011 data zones)", text)     # and the rest on lsoa21cd
        self.assertIn("[joined on lsoa21cd]", text)

    @unittest.skipUnless((config.ROOT / "raw-indicators" / "oac21" / "uk_oac_final.csv").exists(),
                         "the raw downloads (raw-indicators/) are not on this machine")
    def test_the_audit_tools_show_prints_what_the_download_says(self):
        try:
            from tools import audit_neighbourhood
        except ImportError:
            self.skipTest("openpyxl is not installed")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            audit_neighbourhood.Audit(config.ROOT / "raw-indicators", config.ROOT / "work" / "neighbourhood").show(["E00000001", "E01000001", "nonsense"])
        text = out.getvalue()
        self.assertIn("supergroup 3, group 3c, subgroup 3c2", text)          # City of London, straight from the download
        self.assertIn("rank 26,525 of 33,755", text)
        self.assertIn("published decile 8", text)
        self.assertIn("in none of the downloads", text)

    def test_the_check_reports_per_country_and_finds_a_missing_country(self):
        # the fake tables are gappy on purpose (and one dropped London LSOA is a tenth of the rows), hence 0.75
        with mock.patch.object(nbhd_tables, "LOW", 0.75):
            self.assertEqual(nbhd_tables.check(self.conn, self.cfg, 2020), [])
        self.conn.execute("CREATE TEMP TABLE keep AS SELECT * FROM nbhd_imd")
        try:
            self.conn.execute("DELETE FROM nbhd_imd WHERE imd_country = 'Scotland'")
            with mock.patch.object(nbhd_tables, "LOW", 0.75):
                problems = nbhd_tables.check(self.conn, self.cfg, 2020)
            self.assertTrue(any("Scotland" in p and "IMD" in p for p in problems), problems)
        finally:
            self.conn.execute("DELETE FROM nbhd_imd")
            self.conn.execute("INSERT INTO nbhd_imd SELECT * FROM keep")
            self.conn.execute("DROP TABLE keep")


class SafeguardedData(unittest.TestCase):
    """The financial precarity classification's lookup from area to group may not be published. Its download
    and its table are kept out of git by .gitignore (twice), and these tests fail if that ever stops being true."""

    def test_the_ignore_rules_for_the_safeguarded_files_are_still_there(self):
        rules = {line.strip() for line in (config.ROOT / ".gitignore").read_text().splitlines()}
        for rule in ("/raw-indicators/", "/raw-indicators/fpc/", "/work/", "**/nbhd_fpc.csv"):
            self.assertIn(rule, rules, f"{rule} is missing from .gitignore: the financial precarity data could be published")

    @unittest.skipUnless((config.ROOT / ".git").exists(), "not a git checkout")
    def test_nothing_safeguarded_is_tracked_by_git(self):
        import subprocess
        try:
            tracked = subprocess.run(["git", "ls-files"], cwd=config.ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git is not available")
        offending = [p for p in tracked if p.startswith(("raw-indicators/", "work/")) or "nbhd_fpc" in p or "fpc_final" in p or "fpc_label" in p]
        self.assertEqual(offending, [], "these files are tracked by git but must never be published")


if __name__ == "__main__":
    unittest.main()
