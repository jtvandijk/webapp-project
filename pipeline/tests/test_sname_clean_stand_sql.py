"""Tests for tools/sql/census_sname_clean_stand.sql, the script that makes the cleaned census surname, and for
make_sname_clean_stand.sh, which runs it for the years that lack it. The first class reads the script as text and always
runs. The others run it in a real Postgres, and are skipped where pgserver and psycopg2 are not installed
(pip install pgserver psycopg2-binary). Run from the project root:   python3 -m unittest discover -s pipeline/tests -t ."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from pipeline import config

SCRIPT = config.ROOT / "tools" / "sql" / "census_sname_clean_stand.sql"
WRAPPER = config.ROOT / "tools" / "sql" / "make_sname_clean_stand.sh"


def _code(text):
    """The script without its -- comments."""
    return "\n".join(line.split("--")[0] for line in text.splitlines())


class TheScriptAsText(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text()
        cls.code = _code(cls.text)

    def test_it_touches_only_the_two_tables_of_its_year(self):
        self.assertEqual(set(re.findall(r"census\.\w+", self.code)), {"census.gb1921", "census.sname_1921"})
        self.assertNotIn("sample", self.code)            # the old function had one step pointed at gb1881_sample

    def test_changing_the_year_gives_a_script_for_that_year_only(self):
        other = _code(self.text.replace("1921", "1881"))
        self.assertEqual(set(re.findall(r"census\.\w+", other)), {"census.gb1881", "census.sname_1881"})

    def test_the_steps_of_the_old_function_come_in_order(self):
        steps = [int(n) for n in re.findall(r"^-- (\d+)\) ", self.text, flags=re.M)]
        self.assertEqual(steps, list(range(18)))

    def test_every_statement_has_balanced_quotes(self):
        for statement in self.code.split(";\n"):
            self.assertEqual(statement.count("'") % 2, 0, statement)

    def test_it_only_changes_the_census_table_by_adding_the_one_column(self):
        changes = re.findall(r"^\s*(ALTER TABLE|UPDATE|DROP TABLE|DELETE FROM|TRUNCATE)\s+(?:IF EXISTS\s+)?(census\.gb1921)\b", self.code, flags=re.M)
        self.assertEqual([c for c in changes if c[0] != "UPDATE"], [("ALTER TABLE", "census.gb1921")])
        self.assertEqual(len(re.findall(r"UPDATE census\.gb1921 g\s+SET sname_clean_stand = ", self.code)), 1)

    def test_nothing_secret_or_machine_specific_is_in_it(self):
        for word in ("password", "host=", "postgresql://", "/users/"):
            self.assertNotIn(word, SCRIPT.read_text().lower())
        for word in ("postgresql://", "/users/", "set -x"):                    # set -x would print the password
            self.assertNotIn(word, WRAPPER.read_text().lower())

    def test_the_wrapper_names_every_census_year_and_no_other(self):
        listed = re.search(r'ALL_YEARS="([\d ]+)"', WRAPPER.read_text()).group(1).split()
        self.assertEqual([int(y) for y in listed], config.ALL_CENSUS_YEARS)


try:
    import pgserver
    import psycopg2
except ImportError:                                      # pragma: no cover - depends on the machine
    pgserver = psycopg2 = None

PSQL_FOLDER = (Path(pgserver.__file__).parent / "pginstall" / "bin") if pgserver else None


@unittest.skipUnless(pgserver, "needs pgserver and psycopg2 (pip install pgserver psycopg2-binary)")
class TheScriptInPostgres(unittest.TestCase):
    NAMES = ["SMITH", "Smith", "SMITH ", "J. SMITH", "A B SMITH", "A. B. SMITH", "SMITH (OR SMYTH)", "SMITH (SMYTH)",
             "SMITH OR SMYTH", "O BRIEN", "O'BRIEN", "D ARCY", "MC DONALD", "MAC-DONALD", "SMITH  JONES", "SM..", "SMITH2",
             "DE LA CRUZ", "NK", "X", "??", "", None]
    EXPECTED = {"SMITH": "smith", "Smith": "smith", "SMITH ": "smith", "J. SMITH": "smith", "A B SMITH": "smith",
                "A. B. SMITH": "bsmith",             # kept on purpose: only the first dot is turned into a space, as in the old function
                "SMITH (OR SMYTH)": "smith", "SMITH (SMYTH)": "smith", "SMITH OR SMYTH": "smith", "O BRIEN": "obrien",
                "O'BRIEN": "obrien", "D ARCY": "darcy", "MC DONALD": "mcdonald", "MAC-DONALD": "macdonald",
                "SMITH  JONES": "smithjones", "SM..": "sm", "SMITH2": "smith", "DE LA CRUZ": "delacruz",
                "NK": None, "X": None, "??": None, "": None, None: None}

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.server = pgserver.get_server(cls.tmp, cleanup_mode="stop")
        cls.conn = psycopg2.connect(cls.server.get_uri())
        cls.conn.autocommit = True
        cls.script = SCRIPT.read_text()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.server.cleanup()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        cur = self.conn.cursor()
        cur.execute("DROP SCHEMA IF EXISTS census CASCADE")
        cur.execute("CREATE SCHEMA census")
        cur.execute("CREATE TABLE census.gb1921 (recid int, source text, sname text)")
        rows = [(i, "ew", name) for i, name in enumerate(self.NAMES + self.NAMES[:5], start=1)]      # the first five twice
        cur.executemany("INSERT INTO census.gb1921 VALUES (%s, %s, %s)", rows)

    def run_script(self):
        """As psql -1 does: the whole file in one transaction, all of it undone on an error."""
        self.conn.autocommit = False
        try:
            self.conn.cursor().execute(self.script)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            self.conn.autocommit = True

    def cleaned(self):
        cur = self.conn.cursor()
        cur.execute("SELECT sname, sname_clean_stand FROM census.gb1921")
        return cur.fetchall()

    def test_every_person_gets_the_name_the_old_function_gave(self):
        self.run_script()
        people = self.cleaned()
        self.assertEqual(len(people), len(self.NAMES) + 5)
        for raw, clean in people:
            self.assertEqual(clean, self.EXPECTED[raw], repr(raw))

    def test_each_different_name_is_cleaned_once_and_counted(self):
        self.run_script()
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*), SUM(n) FROM census.sname_1921")
        self.assertEqual(cur.fetchone(), (len(self.NAMES), len(self.NAMES) + 5))
        cur.execute("SELECT n FROM census.sname_1921 WHERE sname = 'SMITH'")
        self.assertEqual(cur.fetchone()[0], 2)

    def test_the_other_columns_of_the_census_table_are_left_alone(self):
        self.run_script()
        cur = self.conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'census' AND table_name = 'gb1921' ORDER BY ordinal_position")
        self.assertEqual([r[0] for r in cur.fetchall()], ["recid", "source", "sname", "sname_clean_stand"])
        cur.execute("SELECT recid, source, sname FROM census.gb1921 ORDER BY recid")
        self.assertEqual([r[2] for r in cur.fetchall()], self.NAMES + self.NAMES[:5])

    def test_a_second_run_stops_and_changes_nothing(self):
        self.run_script()
        before = sorted(self.cleaned(), key=repr)
        with self.assertRaises(psycopg2.Error):
            self.run_script()                            # the column is already there
        self.assertEqual(sorted(self.cleaned(), key=repr), before)
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM census.sname_1921")
        self.assertEqual(cur.fetchone()[0], len(self.NAMES))       # the helper table is as the first run left it


@unittest.skipUnless(pgserver and shutil.which("bash") and (PSQL_FOLDER / "psql").exists(),
                     "needs pgserver, psycopg2, bash and its psql (pip install pgserver psycopg2-binary)")
class TheWrapper(unittest.TestCase):
    """make_sname_clean_stand.sh, run for real with the psql that comes with pgserver."""
    PASSWORD = "not-a-real-password-7431"

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.server = pgserver.get_server(cls.tmp, cleanup_mode="stop")
        cls.conn = psycopg2.connect(cls.server.get_uri())
        cls.conn.autocommit = True

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.server.cleanup()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        cur = self.conn.cursor()
        cur.execute("DROP SCHEMA IF EXISTS census CASCADE")
        cur.execute("CREATE SCHEMA census")
        for year in (1881, 1901, 1921):                  # the other census years have no table at all
            cur.execute(f"CREATE TABLE census.gb{year} (recid int, source text, sname text)")
            cur.execute(f"INSERT INTO census.gb{year} VALUES (1, 'ew', 'J. SMITH'), (2, 'ew', 'O BRIEN'), (3, 'ew', NULL)")
        cur.execute("ALTER TABLE census.gb1881 ADD COLUMN sname_clean_stand text")     # this year already has it ...
        cur.execute("UPDATE census.gb1881 SET sname_clean_stand = 'kept'")             # ... and it must stay as it is

    def run_wrapper(self, *args, **settings):
        env = dict(os.environ, PATH=f"{PSQL_FOLDER}{os.pathsep}{os.environ['PATH']}", PGHOST_ICEM=self.tmp, PGPORT_ICEM="5432",
                   PGDATABASE_ICEM="postgres", PGUSER_ICEM="postgres", PGPASSWORD_ICEM=self.PASSWORD)
        env.update(settings)
        env = {k: v for k, v in env.items() if v is not None}
        return subprocess.run(["bash", str(WRAPPER), *args], env=env, capture_output=True, text=True, cwd=self.tmp)

    def cleaned(self, year):
        cur = self.conn.cursor()
        cur.execute(f"SELECT sname_clean_stand FROM census.gb{year} ORDER BY recid")
        return [r[0] for r in cur.fetchall()]

    def has_column(self, year):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'census' AND table_name = %s "
                    "AND column_name = 'sname_clean_stand'", (f"gb{year}",))
        return cur.fetchone()[0] == 1

    def test_list_says_which_years_lack_the_column_and_changes_nothing(self):
        out = self.run_wrapper("--list")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("1881: has sname_clean_stand", out.stdout)
        self.assertIn("1901: lacks sname_clean_stand", out.stdout)
        self.assertIn("1921: lacks sname_clean_stand", out.stdout)
        self.assertIn("1851: census.gb1851 does not exist", out.stdout)
        self.assertFalse(self.has_column(1901))
        self.assertFalse(self.has_column(1921))

    def test_with_no_years_named_it_makes_the_column_for_every_year_that_lacks_it(self):
        out = self.run_wrapper()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.cleaned(1901), ["smith", "obrien", None])
        self.assertEqual(self.cleaned(1921), ["smith", "obrien", None])
        self.assertEqual(self.cleaned(1881), ["kept", "kept", "kept"])                  # the year that had it is not touched
        self.assertIn("1881: has sname_clean_stand", out.stdout)
        self.assertIn("people_with_no_cleaned_name", out.stdout)                       # it shows the tables to read
        self.assertIn("1921: done", out.stdout)

    def test_a_named_year_is_the_only_one_made(self):
        out = self.run_wrapper("1921")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.cleaned(1921), ["smith", "obrien", None])
        self.assertFalse(self.has_column(1901))
        cur = self.conn.cursor()
        cur.execute("SELECT to_regclass('census.sname_1921') IS NOT NULL, to_regclass('census.sname_1901') IS NOT NULL")
        self.assertEqual(cur.fetchone(), (True, False))                                  # only 1921 got its helper table

    def test_running_it_again_finds_nothing_left_to_do(self):
        self.run_wrapper()
        again = self.run_wrapper()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertNotIn("making", again.stdout)
        self.assertIn("1921: has sname_clean_stand", again.stdout)

    def test_a_year_that_is_not_a_census_year_stops_it_before_anything_is_touched(self):
        out = self.run_wrapper("1921", "1871")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("1871 is not a census year", out.stdout)
        self.assertFalse(self.has_column(1921))

    def test_it_says_so_when_the_settings_are_missing_or_wrong(self):
        out = self.run_wrapper(PGHOST_ICEM=None)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("PGHOST_ICEM is not set", out.stderr)
        out = self.run_wrapper(PGUSER_ICEM="nobody-such-user")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("cannot connect", out.stdout)

    def test_the_password_is_never_printed(self):
        for args in (["--list"], []):
            out = self.run_wrapper(*args)
            self.assertNotIn(self.PASSWORD, out.stdout + out.stderr)

    def test_a_failure_at_the_start_leaves_the_year_as_it_was(self):
        cur = self.conn.cursor()
        cur.execute("ALTER TABLE census.gb1901 RENAME COLUMN sname TO surname")          # this year cannot be cleaned
        out = self.run_wrapper("1901")
        self.assertNotEqual(out.returncode, 0)
        self.assertFalse(self.has_column(1901))

    def test_a_failure_at_the_very_end_undoes_everything_before_it(self):
        cur = self.conn.cursor()
        cur.execute("""CREATE FUNCTION refuse() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'no'; END $$""")
        cur.execute("CREATE TRIGGER refuse BEFORE UPDATE ON census.gb1901 FOR EACH ROW EXECUTE FUNCTION refuse()")   # the last step fails
        out = self.run_wrapper("1901")
        self.assertNotEqual(out.returncode, 0)
        self.assertFalse(self.has_column(1901))                                          # the column added a moment before is gone
        cur.execute("SELECT to_regclass('census.sname_1901') IS NOT NULL")
        self.assertFalse(cur.fetchone()[0])                                              # and so is the helper table

    def test_each_table_is_vacuumed_afterwards(self):
        cur = self.conn.cursor()
        cur.execute("SELECT reltuples FROM pg_class WHERE oid = 'census.gb1921'::regclass")
        self.assertLess(cur.fetchone()[0], 0)                                            # never analysed yet
        self.run_wrapper("1921")
        cur.execute("SELECT reltuples FROM pg_class WHERE oid = 'census.gb1921'::regclass")
        self.assertEqual(cur.fetchone()[0], 3)                                           # now the planner knows the size


if __name__ == "__main__":
    unittest.main()
