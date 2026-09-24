"""Tests for pipeline/check_surnames.py: the raw census surname (surname_key) against the old cleaned column.
Run from the project root:   python3 -m unittest discover -s pipeline/tests -t ."""
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pipeline import check_surnames as cs
from pipeline import config, fake_data, sql
from pipeline.names import surname_key


class KindOf(unittest.TestCase):
    def test_each_kind_of_raw_value(self):
        for raw, kind in [("SMITH (SMYTH)", "brackets"), ("SMITH (OR SMYTH)", "brackets"), ("SMITH OR SMYTH", "or"), ("smith or smyth", "or"),
                          ("J. SMITH", "initial"), ("J SMITH", "initial"), ("SMITH2", "digits"), ("SMI..", "dots"), ("SMITH", "other"),
                          ("ORMEROD", "other"), (None, "other")]:
            self.assertEqual(cs.kind_of(raw), kind, raw)


class CheckSurnames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "census.db"
        fake_data.generate(persons=8000, surnames=100, seed=8, path=cls.db_path, quiet=True)
        base = config.settings("fake")
        cls.fake = dict(base, database=str(cls.db_path))
        # the real table has a raw column (sname) next to the cleaned one; the fake one has only the cleaned one
        cls.with_raw = dict(cls.fake, census=dict(base["census"], surname="sname"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def database(self, *statements):
        """A copy of the fake database with a raw surname column on gb1881 (same as the cleaned one, in capitals), then the statements."""
        path = Path(self.tmp.name) / f"raw_{len(list(Path(self.tmp.name).glob('raw_*')))}.db"
        shutil.copy(self.db_path, path)
        conn = sqlite3.connect(path)
        conn.execute("ALTER TABLE gb1881 ADD COLUMN sname TEXT")
        conn.execute("UPDATE gb1881 SET sname = UPPER(sname_clean_stand)")
        for statement in statements:
            conn.execute(statement)
        conn.commit()
        self.addCleanup(conn.close)
        return conn

    def report(self, conn, years=(1881,)):
        data = cs.gather(conn, self.with_raw, list(years))
        lines, problems = cs.make_report(data)
        return data, "\n".join(lines), problems

    def people(self, conn, where):
        return conn.execute(f"SELECT COUNT(*) FROM gb1881 WHERE {where}").fetchone()[0]

    def test_where_raw_and_cleaned_are_the_same_nothing_is_reported(self):
        conn = sqlite3.connect(self.db_path)
        self.addCleanup(conn.close)
        data = cs.gather(conn, self.fake, config.ALL_CENSUS_YEARS)             # raw and cleaned are one column in the fake tables
        lines, problems = cs.make_report(data)
        self.assertEqual(problems, [], "\n".join(lines))
        self.assertTrue(all(cs.summarise(pairs)["total"]["differ"] == 0 for pairs in data.values()))

    def test_capitals_alone_are_no_difference(self):
        conn = self.database()
        data, text, problems = self.report(conn)
        self.assertEqual(problems, [], text)
        self.assertEqual(cs.summarise(data[1881])["total"]["same"], self.people(conn, "1 = 1"))

    def test_each_kind_of_difference_is_counted_with_the_right_people(self):
        conn = self.database(
            "UPDATE gb1881 SET sname = 'J. ' || UPPER(sname_clean_stand) WHERE recid % 10 = 0",             # initial
            "UPDATE gb1881 SET sname = UPPER(sname_clean_stand) || ' (OR SMYTH)' WHERE recid % 10 = 1",      # brackets
            "UPDATE gb1881 SET sname = UPPER(sname_clean_stand) || ' OR SMYTH' WHERE recid % 10 = 2",        # or
            "UPDATE gb1881 SET sname = '??', sname_clean_stand = NULL WHERE recid % 10 = 3",                 # junk both ways: no difference
            "UPDATE gb1881 SET sname_clean_stand = NULL WHERE recid % 10 = 4")                               # old cleaning emptied it
        data, text, problems = self.report(conn)
        s = cs.summarise(data[1881])
        expected = {"initial": self.people(conn, "recid % 10 = 0"), "brackets": self.people(conn, "recid % 10 = 1"),
                    "or": self.people(conn, "recid % 10 = 2"), "emptied by the old cleaning": self.people(conn, "recid % 10 = 4")}
        self.assertEqual(dict(s["kinds"]), expected)
        self.assertEqual(s["total"]["differ"], sum(expected.values()))
        self.assertEqual(s["total"]["same"] + s["total"]["differ"], s["total"]["people"])
        self.assertTrue(problems, "half the people under another name is worth a look")
        self.assertIn("initial:", text)

    def test_the_biggest_differences_are_listed_biggest_first_with_both_readings(self):
        conn = self.database("UPDATE gb1881 SET sname = 'J. ' || UPPER(sname_clean_stand) WHERE recid % 4 = 0")
        data, text, _ = self.report(conn)
        biggest = cs.summarise(data[1881])["biggest"]
        self.assertEqual([b[0] for b in biggest], sorted((b[0] for b in biggest), reverse=True))
        people, raw, clean, label = biggest[0]
        self.assertEqual(label, "initial")
        self.assertEqual(surname_key(raw), "j" + surname_key(clean))
        self.assertIn(f"raw key {surname_key(raw)!r}", text)

    def test_a_small_difference_is_shown_but_not_flagged(self):
        conn = self.database("UPDATE gb1881 SET sname = 'J. ' || UPPER(sname_clean_stand) WHERE recid = 7")
        data, text, problems = self.report(conn)
        self.assertEqual(problems, [], text)
        self.assertEqual(cs.summarise(data[1881])["total"]["differ"], 1)

    def test_a_year_without_the_raw_column_is_skipped_not_an_error(self):
        conn = self.database()
        data, text, _ = self.report(conn, years=(1851, 1881))
        self.assertIsNone(data[1851])
        self.assertTrue([line for line in text.splitlines() if line.split()[:1] == ["1851"] and "skipped" in line], text)
        self.assertIsNotNone(data[1881])

    def test_a_cleaned_column_that_was_never_filled_is_flagged(self):
        conn = self.database("UPDATE gb1881 SET sname_clean_stand = NULL WHERE recid % 10 <> 0")
        _, text, problems = self.report(conn)
        self.assertTrue([p for p in problems if "cleaning was probably never run" in p], text)

    def test_cleaned_values_that_still_hold_spaces_or_hyphens_are_counted(self):
        conn = self.database("UPDATE gb1881 SET sname_clean_stand = sname_clean_stand || ' jones' WHERE recid % 10 = 5")
        data, text, _ = self.report(conn)
        self.assertEqual(cs.summarise(data[1881])["total"]["cleaned_with_other_characters"], self.people(conn, "recid % 10 = 5"))
        self.assertIn("still holds a space, hyphen or other non-letter", text)

    def test_an_empty_table_is_flagged(self):
        _, _, problems = self.report(self.database("DELETE FROM gb1881"))
        self.assertTrue([p for p in problems if "no rows" in p])

    def test_the_sql_for_the_tre(self):
        query = sql.surname_pairs(config.settings("tre"), 1881)
        self.assertIn("SELECT sname, sname_clean_stand, COUNT(*) FROM census.gb1881 GROUP BY sname, sname_clean_stand", query)


if __name__ == "__main__":
    unittest.main()
