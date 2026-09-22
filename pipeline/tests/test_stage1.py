"""Tests for the names rule and for stage 1 (counting).

Run from the project root:   python3 -m unittest discover -s pipeline/tests -t .

The counting test builds a small fake database, runs the real SQL, and compares the answer with a
second, independent calculation done in Python straight from the tables. The two share no code,
so if the SQL joins the wrong table or misreads a year, they disagree.
"""
import sqlite3
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from pipeline import config, fake_data, s1_counts
from pipeline.names import surname_key


class SurnameKey(unittest.TestCase):
    def test_examples(self):
        for raw, key in [("Smith", "smith"), ("SMITH", "smith"), ("O'Brien", "obrien"),
                         ("Smith-Jones", "smithjones"), ("Müller", "muller"), (" de la Cruz ", "delacruz")]:
            self.assertEqual(surname_key(raw), key, raw)

    def test_junk_is_dropped(self):
        for raw in ["", None, "XXXX", "nan", "NaN", "1234", "--"]:
            self.assertEqual(surname_key(raw), "", raw)


class CountingMatchesAnIndependentCalculation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "test.db"
        fake_data.generate(persons=6000, surnames=300, seed=7, path=cls.db, quiet=True)
        cls.cfg = dict(config.settings("fake"), database=str(cls.db))
        conn = sqlite3.connect(cls.db)
        cls.counts = s1_counts.count_all(conn, conn, cls.cfg)  # one sqlite file serves both "databases"
        cls.conn = conn

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def test_register_counts(self):
        rows = self.conn.execute("""SELECT r.surname, r.first, r.last FROM register r
                                    JOIN postcode_lookup a ON a.postcode = r.postcode
                                    WHERE a.easting > 0 AND a.northing > 0
                                      AND a.ctry IN ('E92000001', 'S92000003', 'W92000004')""").fetchall()
        for year in (1997, 2005, 2016, 2026):
            expected = Counter(surname_key(s) for s, first, last in rows if first <= year <= last)
            expected.pop("", None)
            got = {k: n for (src, y, k), n in self.counts.items() if src == "register" and y == year}
            for key, n in expected.items():
                if n >= config.COUNT_FLOOR:
                    self.assertEqual(got.get(key), n, f"register {year} {key}")
            self.assertEqual(set(got), {k for k, n in expected.items() if n >= config.COUNT_FLOOR})

    def test_census_counts_use_the_right_parish_boundaries(self):
        # 1911 must use the 1901 parish numbering; joining the 1851 table by mistake would give nothing
        for year in config.CENSUS_YEARS:
            boundaries = config.CENSUS_PARISH_BOUNDARIES[year]
            valid = {r[0] for r in self.conn.execute(f"SELECT conparid FROM conpar{boundaries}")}
            people = self.conn.execute(f"""SELECT c.sname_clean_stand, a.gid FROM gb{year} c
                                           JOIN gb{year}_att a ON a.recid = c.recid AND a.source = c.source""").fetchall()
            expected = Counter(surname_key(s) for s, gid in people if gid in valid and gid != 0)
            got = {k: n for (src, y, k), n in self.counts.items() if src == "census" and y == year}
            self.assertEqual(got, {k: n for k, n in expected.items() if n >= config.COUNT_FLOOR}, f"census {year}")

    def test_match_rate_agrees_with_an_independent_count(self):
        rates = s1_counts.match_rate(self.conn, self.cfg)
        self.assertEqual(set(rates), set(config.REGISTER_YEARS))
        rows = self.conn.execute("SELECT r.first, r.last, a.easting, a.northing, a.ctry FROM register r "
                                 "LEFT JOIN postcode_lookup a ON a.postcode = r.postcode").fetchall()
        for year in (1997, 2010, 2026):
            here = [row for row in rows if row[0] <= year <= row[1]]
            usable = [row for row in here if row[2] and row[3] and row[4] in ("E92000001", "S92000003", "W92000004")]
            self.assertEqual(rates[year], (len(usable), len(here)), year)
            self.assertGreater(len(usable) / len(here), 0.9)
        self.assertLess(len(usable) / len(here), 1.0, "the fake data should contain unmatched rows")

    def test_a_lookup_in_the_wrong_format_is_stopped(self):
        rates = {y: (10, 100) for y in config.REGISTER_YEARS}          # only 10% find their postcode
        with self.assertRaises(SystemExit):
            s1_counts.report_match_rate(rates)

    def test_northern_ireland_is_left_out(self):
        ni = self.conn.execute("SELECT COUNT(*) FROM register r JOIN postcode_lookup a ON a.postcode = r.postcode "
                               "WHERE a.ctry = 'N92000002'").fetchone()[0]
        self.assertGreater(ni, 0, "the fake data should contain Northern Ireland rows")
        without = s1_counts.match_rate(self.conn, self.cfg)
        loose = dict(self.cfg, register=dict(self.cfg["register"], extra_where=""))
        with_ni = s1_counts.match_rate(self.conn, loose)
        self.assertGreater(sum(m for m, t in with_ni.values()), sum(m for m, t in without.values()))

    def test_a_postcode_lookup_with_a_repeated_postcode_is_refused(self):
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM postcode_lookup").fetchone()[0] > 0, True)
        self.assertEqual(s1_counts.db.fetch(self.conn, s1_counts.sql.duplicate_lookup_keys(self.cfg))[0][0], 0)
        self.conn.execute("INSERT INTO postcode_lookup SELECT * FROM postcode_lookup LIMIT 1")   # the same postcode again
        try:
            with self.assertRaises(SystemExit):
                s1_counts.check_lookup(self.conn, self.cfg)
        finally:
            self.conn.rollback()

    def test_scotland_is_missing_in_1911_and_1921(self):
        scottish_counties = {"Lanarkshire", "Midlothian", "Aberdeenshire", "Inverness-shire", "Angus", "Perthshire"}
        for year in config.SCOTLAND_MISSING_YEARS:
            boundaries = config.CENSUS_PARISH_BOUNDARIES[year]
            counties = {r[0] for r in self.conn.execute(
                f"SELECT DISTINCT regcnty FROM gb{year}_att a JOIN conpar{boundaries} p ON p.conparid = a.gid")}
            self.assertFalse(counties & scottish_counties, f"{year} should have no Scottish parishes")
        counties_1901 = {r[0] for r in self.conn.execute(
            "SELECT DISTINCT regcnty FROM gb1901_att a JOIN conpar1901 p ON p.conparid = a.gid")}
        self.assertTrue(counties_1901 & scottish_counties, "1901 (the reference year) should still have Scotland")

    def test_name_list_only_has_names_over_the_threshold(self):
        listed = s1_counts.name_list(self.counts)
        periods = {p["id"]: p for p in config.PERIODS}
        for key, ids in listed.items():
            for pid in ids:
                p = periods[pid]
                self.assertGreaterEqual(self.counts[(p["source"], p["year"], key)], config.THRESHOLD[p["source"]])


if __name__ == "__main__":
    unittest.main()
