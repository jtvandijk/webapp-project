"""Tests for pipeline/sql.py's surname filter.

Run from the project root:   python3 -m unittest discover -s pipeline/tests -t .

Regression test: register_cells()/census_cells() used to have no way to narrow a query to specific
surnames, so asking for a handful of names on the real 150M-row register meant grouping by every
surname in the country to keep the few that were wanted - fine on the small fake data, unworkable
at real scale. The filter is Postgres-only and coarse (surname_key() still resolves it precisely
once the result reaches Python), so it must never change what SQLite (the small fake/test data)
sees, and must never be applied to the "everybody" population query, which needs every surname.
"""
import unittest

from pipeline import config, sql

TRE = config.settings("tre")
FAKE = config.settings("fake")


class SurnameFilter(unittest.TestCase):
    def test_no_filter_without_a_surname_list(self):
        self.assertNotIn("regexp_replace", sql.register_cells(TRE, 2020))
        self.assertNotIn("regexp_replace", sql.census_cells(TRE, 1901))

    def test_filter_present_on_postgres_when_surnames_given(self):
        q = sql.register_cells(TRE, 2020, surnames=["smith", "longley"])
        self.assertIn("regexp_replace(lower(r.surname), '[^a-z]', '', 'g') IN ('smith','longley')", q)
        self.assertIn("regexp_replace", sql.census_cells(TRE, 1901, surnames=["smith"]))

    def test_never_applied_to_the_population_surface_query(self):
        # by_surname=False must ignore a surnames list even if one is passed by mistake - the
        # "everybody" surface needs every surname, that is the whole point of it
        q = sql.register_cells(TRE, 2020, by_surname=False, surnames=["smith"])
        self.assertNotIn("regexp_replace", q)

    def test_never_applied_on_sqlite_even_with_surnames_given(self):
        # the fake/test database is small; filtering there would only risk diverging from the real
        # (unfiltered) behaviour that the other tests already check against an independent count
        q = sql.register_cells(FAKE, 2020, surnames=["smith"])
        self.assertNotIn("regexp_replace", q)

    def test_a_quote_in_a_surname_is_escaped_not_a_syntax_break(self):
        q = sql.register_cells(TRE, 2020, surnames=["o'brien"])
        self.assertIn("'o''brien'", q)

    def test_stage_1_has_no_way_to_be_passed_a_surname_filter(self):
        # register_counts()/census_counts() (stage 1) count every surname on purpose; they take no
        # surnames argument at all, so stage 1 cannot accidentally be narrowed
        with self.assertRaises(TypeError):
            sql.register_counts(TRE, [2020], surnames=["smith"])
        with self.assertRaises(TypeError):
            sql.census_counts(TRE, 1901, surnames=["smith"])


if __name__ == "__main__":
    unittest.main()
