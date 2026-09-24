"""Tests for pipeline/names.py's chunk_of() - stage 3 and stage 4 must always agree on where a
name's data lives, with no shared manifest file, so this is worth pinning down directly.

Run from the project root:   python3 -m unittest discover -s pipeline/tests -t .
"""
import subprocess
import sys
import unittest

from pipeline.names import chunk_of, has_letters, name_key, place_label, place_name


class PlaceName(unittest.TestCase):
    def test_all_capitals_become_ordinary_capitals(self):
        for raw, shown in [("ABERDEEN", "Aberdeen"), ("ROSS AND CROMARTY", "Ross and Cromarty"), ("LONDON 1", "London 1"),
                           ("KIRKPATRICK-FLEMING", "Kirkpatrick-Fleming"), ("SOUTH-ON-TEES", "South-on-Tees"),
                           ("ST. ANDREWS AND ST LEONARDS", "St. Andrews and St Leonards"),
                           ("KINCARDINE O'NEIL", "Kincardine O'Neil"), ("ST MARY'S", "St Mary's"),
                           ("THE ISLES OF THE SEA", "The Isles of the Sea")]:
            self.assertEqual(place_name(raw), shown, raw)

    def test_a_name_that_is_not_all_capitals_is_left_alone(self):
        # str.title() would break every one of these
        for raw in ["Middlesex (exclusive of London Districts)", "Yorkshire, West Riding", "St Mary's", "Ross and Cromarty",
                    "Bakewell", "Chelsfield, Orpington", "Wisborough Green (Billingshurst, Sussex)"]:
            self.assertEqual(place_name(raw), raw, raw)

    def test_spaces_are_tidied_and_nothing_gives_nothing(self):
        self.assertEqual(place_name("London  (West Districts)"), "London (West Districts)")
        self.assertEqual(place_name("  Kirkby   Malham "), "Kirkby Malham")
        self.assertEqual((place_name(None), place_name(""), place_name("-")), ("", "", "-"))

    def test_a_placeholder_has_no_letters(self):
        self.assertEqual([has_letters(x) for x in ("-", "", None, "  ", "1", "Bath", "London 1")],
                         [False, False, False, False, False, True, True])

    def test_the_grouping_key_ignores_capitals_and_spaces(self):
        self.assertEqual(name_key("ABERDEEN"), name_key(" Aberdeen "))
        self.assertEqual(name_key("Ross  and Cromarty"), name_key("ROSS AND CROMARTY"))
        self.assertNotEqual(name_key("Kirkby Malham"), name_key("Kirkby Malzeard"))


class PlaceLabel(unittest.TestCase):
    RULES = [(r"^(london [123]|city of london)$", "London", "London parishes")]

    def test_a_parish_with_a_name_is_shown_under_it(self):
        self.assertEqual(place_label("Kent", "Chelsfield", self.RULES), ("Kent", "Chelsfield"))
        self.assertEqual(place_label("ROSS AND CROMARTY", "COLL", self.RULES), ("Ross and Cromarty", "Coll"))
        self.assertEqual(place_label("", "Bath"), ("", "Bath"))                       # even with no county

    def test_a_nameless_parish_takes_the_label_of_its_county(self):
        for county in ("London 1", "London  2", "LONDON 3", " City of London "):
            self.assertEqual(place_label(county, "-", self.RULES), ("London", "London parishes"), county)
            self.assertEqual(place_label(county, "", self.RULES), ("London", "London parishes"), county)

    def test_a_nameless_parish_with_no_label_is_left_out(self):
        for county in ("Kent", "Yorkshire, North Riding", "London 4", "Greater London", "London (Central Districts)", "", None):
            self.assertIsNone(place_label(county, "-", self.RULES), county)
        self.assertIsNone(place_label("London 1", "-"))                               # no rules given: nothing is invented

    def test_a_named_parish_is_never_relabelled(self):
        self.assertEqual(place_label("London 1", "Paddington", self.RULES), ("London 1", "Paddington"))


class ChunkOf(unittest.TestCase):
    def test_always_in_range(self):
        for key in ("smith", "obrien", "", "a", "vandijk"):
            self.assertIn(chunk_of(key, 200), range(200))

    def test_stable_for_the_same_key(self):
        self.assertEqual(chunk_of("smith", 200), chunk_of("smith", 200))

    def test_stable_across_separate_processes(self):
        # the whole point: Python's own str hash() is randomised per process (PYTHONHASHSEED),
        # which chunk_of() must not depend on - checked here in a genuinely separate interpreter,
        # not just twice in this one
        code = "from pipeline.names import chunk_of; print(chunk_of('smith', 200))"
        first = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
        second = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
        self.assertEqual(first, second)

    def test_spreads_many_names_reasonably_evenly(self):
        chunks = 50
        counts = [0] * chunks
        for i in range(20000):
            counts[chunk_of(f"name{i}", chunks)] += 1
        # 20000 names over 50 chunks: 400 each on average - not asking for perfect balance, just
        # nothing wildly lopsided (a real hash function, not e.g. everything landing in one bucket)
        self.assertTrue(all(200 < c < 700 for c in counts), counts)

    def test_adding_a_name_does_not_move_an_existing_ones_chunk(self):
        chunks = 20
        before = {f"name{i}": chunk_of(f"name{i}", chunks) for i in range(500)}
        after = {f"name{i}": chunk_of(f"name{i}", chunks) for i in range(600)}   # 100 more names
        for key, chunk in before.items():
            self.assertEqual(after[key], chunk)


if __name__ == "__main__":
    unittest.main()
