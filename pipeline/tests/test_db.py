"""Tests for pipeline/db.py: which settings each database group actually needs.

Run from the project root:   python3 -m unittest discover -s pipeline/tests -t .

Regression test: connecting to one database ("register" or "census") used to check that BOTH
databases were fully configured, so testing against the register database alone failed with a
confusing "FILL_IN: connections.census.dbname" even though census was never going to be used.
"""
import unittest

from pipeline import db

# a "tre"-shaped config with the census connection deliberately left unset, as it would be for
# someone testing --sources register before the census database is ready
CFG = {
    "connections": {
        "register": {"host": "h", "port": 5432, "dbname": "regdb", "user": "u"},
        "census": {"host": None, "port": 5432, "dbname": None, "user": None},
    },
    "register": {"table": "registers_linked.lcr_consol2026"},
    "census": {"table": "FILL_IN.gb{year}"},
}


class Missing(unittest.TestCase):
    def test_register_is_ready_even_though_census_is_not(self):
        self.assertEqual(db._missing(CFG, "register"), [])

    def test_census_reports_exactly_what_is_missing(self):
        missing = db._missing(CFG, "census")
        self.assertIn("connections.census.host", missing)
        self.assertIn("connections.census.dbname", missing)
        self.assertIn("connections.census.user", missing)
        self.assertIn("census.table", missing)
        self.assertNotIn("connections.register.host", missing, "should not look at the other group at all")


class _Cursor:
    """A stand-in for a driver's cursor: records what it was asked to run, optionally raising instead."""
    def __init__(self, log, fail=None):
        self.log, self.fail = log, fail

    def execute(self, sql):
        if self.fail:
            raise self.fail
        self.log.append(sql)

    def close(self):
        self.log.append("closed")


class Execute(unittest.TestCase):
    """db.execute(): for a statement that returns no rows (fetch() would fail on these - there is nothing
    to fetch). Used so far by preview.py's own connection (SET enable_nestloop = off)."""

    def test_runs_the_statement_and_closes_the_cursor(self):
        log = []
        conn = type("Conn", (), {"cursor": lambda self: _Cursor(log)})()
        db.execute(conn, "SET enable_nestloop = off")
        self.assertEqual(log, ["SET enable_nestloop = off", "closed"])

    def test_the_cursor_is_still_closed_if_the_statement_fails(self):
        log = []
        conn = type("Conn", (), {"cursor": lambda self: _Cursor(log, fail=RuntimeError("boom"))})()
        with self.assertRaises(RuntimeError):
            db.execute(conn, "bad sql")
        self.assertEqual(log, ["closed"])


if __name__ == "__main__":
    unittest.main()
