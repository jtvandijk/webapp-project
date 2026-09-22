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


if __name__ == "__main__":
    unittest.main()
