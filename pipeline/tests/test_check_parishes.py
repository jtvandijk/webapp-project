"""Tests for pipeline/check_parishes.py: the sanity report on parish ids. Each kind of damage is made on purpose in a copy
of the fake database, and the report has to name it; on the healthy database it has to find nothing.
Run from the project root:   python3 -m unittest discover -s pipeline/tests -t ."""
import csv
import shutil
import sqlite3
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from pipeline import check_parishes as cp
from pipeline import config, fake_data, sql

YEARS = config.ALL_CENSUS_YEARS


def id_column(year):
    return "conparid1901" if year == 1921 else "gid"      # written out: the real 1921 table differs


class CheckParishes(unittest.TestCase):
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
        path = Path(self.tmp.name) / f"damaged_{len(list(Path(self.tmp.name).glob('damaged_*')))}.db"
        shutil.copy(self.db_path, path)
        conn = sqlite3.connect(path)
        for statement in statements:
            conn.execute(statement)
        conn.commit()
        self.addCleanup(conn.close)
        return conn

    def report(self, conn=None, lookup=None):
        data = cp.gather(conn or self.conn, self.cfg, YEARS)
        lines, problems = cp.make_report(data, lookup)
        return data, "\n".join(lines), problems

    def flagged(self, problems, *words):
        return [p for p in problems if all(w in p for w in words)]

    # ----- the healthy database

    def test_a_healthy_database_has_nothing_to_look_at(self):
        _, text, problems = self.report()
        self.assertEqual(problems, [], text)
        self.assertIn("0 thing(s) to look at", text)

    def test_the_numbers_agree_with_counts_made_straight_from_the_tables(self):
        data, _, _ = self.report()
        for year in YEARS:
            boundaries = config.CENSUS_PARISH_BOUNDARIES[year]
            ids = {r[0] for r in self.conn.execute(f"SELECT conparid FROM conpar{boundaries}")}
            straight = Counter(r[0] for r in self.conn.execute(f"SELECT {id_column(year)} FROM gb{year}_att"))
            summary = cp.summarise_year(data["years"][year]["counts"], ids)
            self.assertEqual(summary["people"], sum(straight.values()), year)
            self.assertEqual(summary["zero"], straight[0], year)
            self.assertEqual(summary["found"], sum(n for i, n in straight.items() if i in ids), year)
            self.assertEqual(summary["distinct"], len([i for i in straight if i not in (None, 0)]), year)
            self.assertEqual((summary["lo"], summary["hi"]), (min(i for i in straight if i), max(straight)), year)
            self.assertEqual(data["years"][year]["column"], id_column(year), year)         # 1921 reads conparid1901

    def test_the_two_parish_tables_are_described(self):
        data, text, _ = self.report()
        for boundaries, table in data["tables"].items():
            summary = cp.summarise_table(table["rows"])
            rows = self.conn.execute(f"SELECT COUNT(*), MIN(conparid), MAX(conparid) FROM conpar{boundaries}").fetchone()
            self.assertEqual((summary["rows"], summary["lo"], summary["hi"]), rows)
        self.assertIn("the two parish tables share no ids", text)
        self.assertIn("(id column: INTEGER)", text)

    def test_scotland_missing_in_1911_and_1921_is_said_only_for_those_years(self):
        _, text, _ = self.report()
        said = [line.split(":")[0].strip() for line in text.splitlines() if "expected for Scotland" in line]
        self.assertEqual(said, ["1911", "1921"])

    # ----- damage to the people

    def test_ids_that_are_not_in_the_parish_table_are_named_with_their_people(self):
        conn = self.damaged("UPDATE gb1901_att SET gid = 99999 WHERE recid % 3 = 0")
        data, text, problems = self.report(conn)
        found = self.flagged(problems, "1901", "not in conpar1901")
        self.assertTrue(found, text)
        self.assertIn("99999 (", found[0])
        people = conn.execute("SELECT COUNT(*) FROM gb1901_att WHERE gid = 99999").fetchone()[0]
        self.assertIn(f"99999 ({people:,})", found[0])
        self.assertFalse(self.flagged(problems, "1911"), "only the damaged year is flagged")

    def test_a_few_ids_missing_are_noted_but_not_flagged(self):
        _, text, problems = self.report(self.damaged("UPDATE gb1901_att SET gid = 99999 WHERE recid = 3"))
        self.assertEqual(problems, [])
        self.assertIn("1901: 1 people have an id that is not in the table", text)

    def test_a_year_that_uses_the_other_tables_ids_says_so(self):
        # 1911 must use the 1901 parishes; giving its people the 1851 numbering is the mistake this check is for
        conn = self.damaged("UPDATE gb1911_att SET gid = gid - 5000 WHERE gid > 5000")
        _, text, problems = self.report(conn)
        found = self.flagged(problems, "1911", "OTHER parish table")
        self.assertTrue(found, text)
        self.assertTrue(self.flagged(problems, "1911", "not in conpar1901"), "and they are not in the right table either")

    def test_1921_is_checked_through_conparid1901(self):
        _, text, problems = self.report(self.damaged("UPDATE gb1921_att SET conparid1901 = conparid1901 - 5000 WHERE conparid1901 > 5000"))
        self.assertTrue(self.flagged(problems, "1921", "OTHER parish table"), text)
        self.assertTrue(self.flagged(problems, "1921", "conparid1901"), "the message names the column that is used")

    def test_people_without_a_parish_id_are_reported_apart_from_id_0(self):
        conn = self.damaged("UPDATE gb1881_att SET gid = NULL WHERE recid % 50 = 0")
        data, text, problems = self.report(conn)
        nulls = conn.execute("SELECT COUNT(*) FROM gb1881_att WHERE gid IS NULL").fetchone()[0]
        self.assertIn(f"1881: {nulls:,} people have no parish id at all (NULL)", text)
        self.assertEqual(cp.summarise_year(data["years"][1881]["counts"], set())["no_id"], nulls)

    def test_an_empty_attributes_table_is_flagged(self):
        _, _, problems = self.report(self.damaged("DELETE FROM gb1861_att"))
        self.assertTrue(self.flagged(problems, "1861", "no rows"))

    def test_id_0_is_expected_and_never_a_problem(self):
        conn = self.damaged("UPDATE gb1851_att SET gid = 0 WHERE recid % 2 = 0")
        _, text, problems = self.report(conn)
        self.assertEqual(problems, [], text)

    def test_ids_the_fix_list_moves_are_named_when_they_are_still_in_the_data(self):
        # pg_conpar_dic.txt: 6598 -> 6596 (and four others); if 6598 is still in gid, the fix did not reach that column
        _, text, problems = self.report(self.damaged("UPDATE gb1851_att SET gid = 6598 WHERE recid = 3"))
        found = self.flagged(problems, "1851", "still holds ids that the fix list", "6598 (should be 6596)")
        self.assertTrue(found, text)

    def test_scottish_ids_without_the_1901_shift_are_named(self):
        # in the 1901 numbering Scotland is 300,001 and up (200,001 + 100,000)
        conn = self.damaged("UPDATE gb1901_att SET gid = 200005 WHERE recid % 20 = 0")
        _, text, problems = self.report(conn)
        people = conn.execute("SELECT COUNT(*) FROM gb1901_att WHERE gid = 200005").fetchone()[0]
        self.assertTrue(self.flagged(problems, "1901", f"{people:,} people carry Scottish ids in the 200,000s"), text)
        self.assertFalse(self.flagged(problems, "1851", "Scottish ids"))

    # ----- damage to the parish tables

    def test_a_parish_id_on_two_rows_is_flagged(self):
        _, _, problems = self.report(self.damaged("INSERT INTO conpar1901 VALUES (5001, 400000.0, 400000.0, 'Twice', 'Kent')"))
        self.assertTrue(self.flagged(problems, "conpar1901", "more than one row", "5001"))

    def test_two_id_0_rows_are_not_a_repeat_and_are_not_places(self):
        # the 1851 shapefile has two shapes with id 0
        conn = self.damaged("INSERT INTO conpar1851 VALUES (0, 0.0, 0.0, '-', 'ABERDEEN')", "INSERT INTO conpar1851 VALUES (0, 1.0, 1.0, '-', '-')")
        data, text, problems = self.report(conn)
        self.assertEqual(problems, [], text)
        self.assertIn("id 0 on 2 rows", text)

    def test_tables_that_share_ids_are_flagged(self):
        _, _, problems = self.report(self.damaged("INSERT INTO conpar1901 VALUES (1, 400000.0, 400000.0, 'Same as 1851', 'Kent')"))
        self.assertTrue(self.flagged(problems, "share 1 parish ids"), problems)

    def test_no_name_and_blank_county_are_flagged(self):
        conn = self.damaged("UPDATE conpar1901 SET parish = '-' WHERE conparid = 5002", "UPDATE conpar1901 SET parish = '' WHERE conparid = 5003",
                            "UPDATE conpar1901 SET regcnty = NULL WHERE conparid = 5004")
        _, _, problems = self.report(conn)
        self.assertTrue(self.flagged(problems, "conpar1901", "2 parishes have no real name", "5002"))
        self.assertTrue(self.flagged(problems, "conpar1901", "1 parishes have no county"))

    def test_capital_counties_and_several_names_are_noted_not_flagged(self):
        conn = self.damaged("UPDATE conpar1901 SET regcnty = 'ROSS AND CROMARTY' WHERE conparid = 5005",
                            "UPDATE conpar1901 SET parish = 'Chelsfield, Orpington' WHERE conparid = 5006")
        _, text, problems = self.report(conn)
        self.assertEqual(problems, [], text)
        self.assertIn("1 counties are in ALL CAPITALS (e.g. ROSS AND CROMARTY)", text)
        self.assertIn("1 hold several parishes in one", text)

    def test_counties_named_in_only_one_table_are_listed(self):
        conn = self.damaged("UPDATE conpar1901 SET regcnty = 'London 1' WHERE conparid = 5007")
        _, text, _ = self.report(conn)
        self.assertIn("only in conpar1901: London 1", text)         # shown as spelt in the table

    def test_centroids_at_zero_or_off_the_grid_or_missing_are_flagged(self):
        conn = self.damaged("UPDATE conpar1901 SET x = 0, y = 0 WHERE conparid = 5001",
                            "UPDATE conpar1901 SET x = 99999999 WHERE conparid = 5002",
                            "UPDATE conpar1901 SET x = NULL WHERE conparid = 5003")
        _, _, problems = self.report(conn)
        self.assertTrue(self.flagged(problems, "conpar1901", "x = 0 and y = 0"))
        self.assertTrue(self.flagged(problems, "conpar1901", "outside the map grid"))
        self.assertTrue(self.flagged(problems, "conpar1901", "no x/y"))

    def test_fractional_ids_need_a_column_that_can_hold_them(self):
        # ids like 200136.3 (Coll) exist in the old lookup; an integer attributes column cannot hold them
        conn = self.damaged("INSERT INTO conpar1851 VALUES (200136.3, 150000.0, 750000.0, 'Coll', 'ARGYLL')")
        data, text, problems = self.report(conn)
        self.assertIn("1 ids are not whole numbers (e.g. 200136.3)", text)
        self.assertTrue(self.flagged(problems, "1851: the parish table has fractional ids", "cannot hold"), problems)
        data["years"][1851]["id_type"] = "double precision"
        _, problems = cp.make_report(data)
        self.assertFalse(self.flagged(problems, "1851: the parish table has fractional"))

    def test_a_text_id_column_is_flagged(self):
        data, _, _ = self.report()
        data["years"][1901]["id_type"] = "character varying"
        lines, problems = cp.make_report(data)
        self.assertTrue(self.flagged(problems, "1901", "holds text"), problems)

    # ----- the old lookup file

    def write_lookup(self, rows, header=("Country", "CONPARID", "RC1851", "Parish(s)"), bom=False):
        path = Path(self.tmp.name) / f"lookup_{len(list(Path(self.tmp.name).glob('lookup_*')))}.csv"
        with open(path, "w", newline="", encoding="utf-8-sig" if bom else "utf-8") as f:
            out = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
            out.writerow(header)
            out.writerows(rows)
        return path

    def lookup_rows(self):
        return [("ENG", pid, county, name)
                for boundaries in (1851, 1901)
                for pid, name, county in self.conn.execute(f"SELECT conparid, parish, regcnty FROM conpar{boundaries}")]

    def test_a_lookup_that_matches_finds_no_difference(self):
        lookup = cp.read_lookup(self.write_lookup(self.lookup_rows(), bom=True))
        _, text, problems = self.report(lookup=lookup)
        self.assertEqual(problems, [], text)
        self.assertIn("0 ids are not in the lookup", text)
        self.assertIn("0 parish names and 0 counties differ", text)
        self.assertIn("the lookup has 0 ids that are in neither parish table", text)

    def test_lookup_differences_are_counted_and_capitals_and_spaces_are_ignored(self):
        rows = [r for r in self.lookup_rows() if r[1] != 3]                                        # id 3 is missing from the lookup
        rows = [(c, i, "  " + county.upper(), name + " " if i == 4 else name) for c, i, county, name in rows]  # same names, another style
        rows = [(c, i, county, "Another name" if i == 6 else name) for c, i, county, name in rows]             # a real difference: id 6
        rows.append(("ENG", 5, "KENT", "Elsewhere"))                                                          # id 5 twice; one row is right
        rows.append(("SCT", 300001, "ABERDEEN", "Aberdeen"))                                                  # an id in neither table
        lookup = cp.read_lookup(self.write_lookup(rows))
        data, text, _ = self.report(lookup=lookup)
        found = cp.compare_lookup(data["tables"][1851]["rows"], lookup)
        self.assertEqual(found["missing"], [3])
        self.assertEqual([i for i, _, _ in found["parish"]], [6])
        self.assertEqual(found["county"], [], "capitals and spaces do not count as a difference")
        self.assertEqual(found["repeated"], [5])
        self.assertIn("conpar1851: 1 ids are not in the lookup (e.g. 3); 1 parish names and 0 counties differ", text)
        self.assertIn("conpar1901: 0 ids are not in the lookup", text)
        self.assertIn("id 6: parish \"Parish 0006\" here, \"another name\" in the lookup", text)
        self.assertIn("the lookup has 1 ids that are in neither parish table", text)
        self.assertIn("1 ids appear on more than one row of the lookup (e.g. 5)", text)

    def test_the_lookup_can_have_fractional_ids_and_other_column_order(self):
        path = self.write_lookup([("Coll", "ARGYLL", "200136.3", "SCT")], header=("Parish(s)", "RC1851", "CONPARID", "Country"))
        self.assertEqual(cp.read_lookup(path), [(200136.3, "ARGYLL", "Coll")])

    def test_a_file_without_the_id_column_is_refused_with_a_clear_message(self):
        with self.assertRaises(SystemExit) as stopped:
            cp.read_lookup(self.write_lookup([("a", "b")], header=("x", "y")))
        self.assertIn("CONPARID", str(stopped.exception))

    # ----- what runs in the TRE

    def test_the_sql_for_the_tre(self):
        tre = config.settings("tre")
        self.assertIn("FROM census.gb1921_att GROUP BY conparid1901", sql.census_parish_id_counts(tre, 1921))
        self.assertIn("FROM census.gb1911_att GROUP BY gid", sql.census_parish_id_counts(tre, 1911))
        self.assertIn("FROM spatial.conpar1901", sql.parish_table_rows(tre, 1921))
        self.assertIn("FROM spatial.conpar1851", sql.parish_table_rows(tre, 1861))
        types = sql.column_types(tre, "census.gb1921_att")
        self.assertIn("information_schema.columns", types)
        self.assertIn("table_schema = 'census'", types)
        self.assertIn("table_name = 'gb1921_att'", types)


if __name__ == "__main__":
    unittest.main()
