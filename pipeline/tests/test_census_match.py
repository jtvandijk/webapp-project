"""Tests for stage 1's check on the census: how the people of each year divide up, and what stops the run.
Run from the project root:   python3 -m unittest discover -s pipeline/tests -t ."""
import contextlib
import io
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import config, fake_data, s1_counts, sql


class CensusMatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "census.db"
        fake_data.generate(persons=8000, surnames=100, seed=8, path=cls.db_path, quiet=True)
        cls.cfg = dict(config.settings("fake"), database=str(cls.db_path))
        cls.conn = sqlite3.connect(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def damaged(self, *statements):
        """A copy of the fake database with something broken on purpose; returns an open connection to it."""
        path = Path(self.tmp.name) / f"damaged_{len(list(Path(self.tmp.name).glob('damaged_*')))}.db"
        shutil.copy(self.db_path, path)
        conn = sqlite3.connect(path)
        for statement in statements:
            conn.execute(statement)
        conn.commit()
        self.addCleanup(conn.close)
        return conn

    def run_report(self, conn):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            s1_counts.report_census_match(s1_counts.census_match(conn, self.cfg))
        return out.getvalue()

    def test_the_people_divide_up_as_an_independent_count_says(self):
        found = s1_counts.census_match(self.conn, self.cfg)
        self.assertEqual(set(found), set(config.CENSUS_YEARS))
        for year, (people, joined, nowhere, counted) in found.items():
            valid = {r[0] for r in self.conn.execute(f"SELECT conparid FROM conpar{config.CENSUS_PARISH_BOUNDARIES[year]}")}
            parish_column = "conparid1901" if year == 1921 else "gid"           # written out: the real 1921 table differs
            rows = self.conn.execute(f"""SELECT a.{parish_column} FROM gb{year} c JOIN gb{year}_att a ON a.recid = c.recid AND a.source = c.source""").fetchall()
            self.assertEqual(people, self.conn.execute(f"SELECT COUNT(*) FROM gb{year}").fetchone()[0], year)
            self.assertEqual((joined, nowhere, counted),
                             (len(rows), sum(g == 0 for (g,) in rows), sum(g in valid and g != 0 for (g,) in rows)), year)
            self.assertGreater(nowhere, 0)                                # the fake data has people with no parish, as the real census does
            self.assertEqual(joined - nowhere - counted, 0)               # and everybody else is found in the boundaries

    def test_counted_is_exactly_what_the_counts_use(self):
        found = s1_counts.census_match(self.conn, self.cfg)
        for year in (1851, 1911, 1921):
            counted_by_the_counts = sum(n for _, n in self.conn.execute(sql.census_counts(self.cfg, year)))
            self.assertEqual(found[year][3], counted_by_the_counts, year)

    def test_people_with_parish_id_0_are_reported_as_expected_and_never_stop_the_run(self):
        text = self.run_report(self.conn)                                # raises if it stops
        self.assertIn("parish id 0", text)
        self.assertIn("soldiers, sailors", text)
        self.assertNotIn("MORE attributes rows", text)
        # even if a great many people are in no parish (a war year), that is not an error: only unexplained ones are
        many = self.damaged("UPDATE gb1901_att SET gid = 0 WHERE recid % 2 = 0")
        self.assertIn("parish id 0", self.run_report(many))

    def test_a_parish_table_that_has_a_row_for_id_0_does_not_make_those_people_counted(self):
        # the real parish tables probably have a pseudo-parish 0 ("not in a parish"); joining to it must not count anybody
        with_zero = self.damaged("INSERT INTO conpar1851 VALUES (0, 0.0, 0.0, 'Not in a parish', 'None')",
                                 "INSERT INTO conpar1901 VALUES (0, 0.0, 0.0, 'Not in a parish', 'None')")
        for year in (1851, 1901, 1921):
            healthy, zero_row = s1_counts.census_match(self.conn, self.cfg)[year], s1_counts.census_match(with_zero, self.cfg)[year]
            self.assertEqual(zero_row, healthy, year)
            self.assertEqual(zero_row[3], sum(n for _, n in with_zero.execute(sql.census_counts(self.cfg, year))), year)
        self.run_report(with_zero)                                                # and it is still not an error

    def test_a_person_with_two_attributes_rows_stops_the_run_but_a_sliver_is_only_noted(self):
        many = self.damaged("INSERT INTO gb1901_att SELECT * FROM gb1901_att WHERE recid % 10 = 0")      # about 10% twice
        with self.assertRaises(SystemExit) as stopped:
            self.run_report(many)
        self.assertIn("appears more than once", str(stopped.exception))
        self.assertIn("1901", str(stopped.exception))
        few = self.damaged("INSERT INTO gb1901_att SELECT * FROM gb1901_att WHERE recid % 500 = 0")       # about 0.2%
        self.assertIn("MORE attributes rows", self.run_report(few))

    def test_the_wrong_boundaries_for_a_year_stop_the_run(self):
        with mock.patch.dict(config.CENSUS_PARISH_BOUNDARIES, {1911: 1851}):     # 1911 people carry 1901 ids, not 1851 ones
            with self.assertRaises(SystemExit) as stopped:
                self.run_report(self.conn)
        self.assertIn("more than 20%", str(stopped.exception))
        self.assertIn("boundaries", str(stopped.exception))

    def test_a_parish_table_with_a_repeated_parish_id_that_people_carry_is_refused(self):
        s1_counts.check_parish_tables(self.conn, self.cfg)                       # the healthy one passes
        twice = self.damaged("INSERT INTO conpar1901 SELECT * FROM conpar1901 WHERE conparid = 5001")
        with self.assertRaises(SystemExit) as stopped:
            s1_counts.check_parish_tables(twice, self.cfg)
        people = twice.execute("SELECT COUNT(*) FROM gb1901_att WHERE gid = 5001").fetchone()[0]
        self.assertGreater(people, 0)
        self.assertIn("1 parish ids that appear more than once", str(stopped.exception))
        self.assertIn(f"{people:,} people carry them", str(stopped.exception))
        self.assertIn("1901", str(stopped.exception))

    def test_a_repeated_parish_id_that_nobody_carries_is_only_noted(self):
        # the shapefiles have stray pieces of shapes with an id of their own, twice; no census person has that id
        twice = self.damaged("INSERT INTO conpar1901 VALUES (9999, 500000.0, 200000.0, '-', '-')",
                             "INSERT INTO conpar1901 VALUES (9999, 500001.0, 200001.0, '-', '-')")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            s1_counts.check_parish_tables(twice, self.cfg)                       # does not stop
        self.assertIn("1 parish ids on more than one row, but nobody in 1901 carries them", out.getvalue())
        self.assertIn("nothing is counted twice", out.getvalue())

    def test_people_who_carry_a_repeated_id_are_counted_by_the_sql(self):
        twice = self.damaged("INSERT INTO conpar1901 SELECT * FROM conpar1901 WHERE conparid IN (5001, 5002)")
        for year in (1901, 1911, 1921):
            column = "conparid1901" if year == 1921 else "gid"
            expected = twice.execute(f"SELECT COUNT(*) FROM gb{year}_att WHERE {column} IN (5001, 5002)").fetchone()[0]
            self.assertEqual(twice.execute(sql.people_in_repeated_parish_ids(self.cfg, year)).fetchone()[0], expected, year)
        self.assertEqual(twice.execute(sql.people_in_repeated_parish_ids(self.cfg, 1851)).fetchone()[0], 0)   # 1851 uses the other table

    def test_in_1911_and_1921_people_with_no_parish_id_are_people_not_in_a_parish_but_in_another_year_they_are_unexplained(self):
        # 1911 and 1921 record "not in a parish" as no id at all; the other years as id 0
        nulled = self.damaged("UPDATE gb1921_att SET conparid1901 = NULL WHERE recid % 40 = 1", "UPDATE gb1911_att SET gid = NULL WHERE recid % 40 = 1", "UPDATE gb1901_att SET gid = NULL WHERE recid % 40 = 1")
        healthy, found = s1_counts.census_match(self.conn, self.cfg), s1_counts.census_match(nulled, self.cfg)
        k21 = self.conn.execute("SELECT COUNT(*) FROM gb1921_att WHERE recid % 40 = 1 AND conparid1901 <> 0").fetchone()[0]      # had a parish
        k11 = self.conn.execute("SELECT COUNT(*) FROM gb1911_att WHERE recid % 40 = 1 AND gid <> 0").fetchone()[0]
        k01 = self.conn.execute("SELECT COUNT(*) FROM gb1901_att WHERE recid % 40 = 1 AND gid <> 0").fetchone()[0]
        z01 = self.conn.execute("SELECT COUNT(*) FROM gb1901_att WHERE recid % 40 = 1 AND gid = 0").fetchone()[0]                # had id 0
        self.assertGreater(min(k21, k11, k01, z01), 0)
        self.assertEqual(found[1921][2], healthy[1921][2] + k21)                # more people "in no parish" ...
        self.assertEqual(found[1921][3], healthy[1921][3] - k21)                # ... and fewer counted
        self.assertEqual(found[1921][1] - found[1921][2] - found[1921][3], 0)   # nobody is unexplained
        self.assertEqual(found[1911][2], healthy[1911][2] + k11)                # 1911 too
        self.assertEqual(found[1911][1] - found[1911][2] - found[1911][3], 0)
        self.assertEqual(found[1901][2], healthy[1901][2] - z01)                # 1901: a missing id is not id 0 (those who had 0 are now missing) ...
        self.assertEqual(found[1901][1] - found[1901][2] - found[1901][3], k01 + z01)     # ... so all of them are unexplained
        report = self.run_report(nulled)
        self.assertIn("1921:", report)
        self.assertRegex([line for line in report.splitlines() if line.strip().startswith("1921:")][0], r"0\.00% not counted")
        self.assertNotRegex([line for line in report.splitlines() if line.strip().startswith("1901:")][0], r"0\.00% not counted")

    def test_only_the_1911_and_1921_sql_treat_a_missing_id_as_no_parish(self):
        tre = config.settings("tre")
        self.assertIn("a.conparid1901 = 0 OR a.conparid1901 IS NULL", sql.census_match(tre, 1921))
        self.assertIn("a.gid = 0 OR a.gid IS NULL", sql.census_match(tre, 1911))
        for year in (1851, 1861, 1881, 1891, 1901):
            self.assertNotIn("IS NULL", sql.census_match(tre, year), year)
        self.assertIn("HAVING COUNT(*) > 1", sql.people_in_repeated_parish_ids(tre, 1901))
        self.assertIn("FROM census.gb1901_att a", sql.people_in_repeated_parish_ids(tre, 1901))
        self.assertIn("FROM spatial.conpar1851", sql.people_in_repeated_parish_ids(tre, 1861))

    def test_an_empty_census_table_is_refused_with_a_clear_message(self):
        empty = self.damaged("DELETE FROM gb1851")
        with self.assertRaises(SystemExit) as stopped:
            self.run_report(empty)
        self.assertIn("1851 has no rows", str(stopped.exception))

    def test_the_sql_for_the_tre_uses_the_right_tables(self):
        query = sql.census_match(config.settings("tre"), 1921)
        self.assertIn("census.gb1921 c", query)
        self.assertIn("census.gb1921_att a", query)
        self.assertIn("LEFT JOIN spatial.conpar1901 p", query)                   # 1921 uses the 1901 boundaries
        self.assertIn("SELECT COUNT(*) FROM census.gb1851", sql.census_rows(config.settings("tre"), 1851))

    def test_1921_reads_its_parish_from_conparid1901_and_every_other_year_from_gid(self):
        # the ids recorded for 1921 do not link to the standard parishes; conparid1901 (point in polygon) does
        tre = config.settings("tre")
        for make in (sql.census_match, sql.census_counts, sql.census_cells,
                     sql.census_forename_counts, sql.census_parish_counts):
            for year in config.ALL_CENSUS_YEARS:
                query = make(tre, year)
                column = "conparid1901" if year == 1921 else "gid"
                other = "gid" if year == 1921 else "conparid1901"
                self.assertIn(f"a.{column}", query, (make.__name__, year))
                self.assertNotIn(f"a.{other}", query, (make.__name__, year))
        # and the fake attributes table of 1921 has the same column as the real one, and no gid
        columns = {r[1] for r in self.conn.execute("PRAGMA table_info(gb1921_att)")}
        self.assertIn("conparid1901", columns)
        self.assertNotIn("gid", columns)


if __name__ == "__main__":
    unittest.main()
