"""Tests for the things you look at while working: the numbered preview files, and where a few-names run of
stage 5 writes. Run from the project root:   python3 -m unittest discover -s pipeline/tests -t ."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import config, fake_data, files, preview, s1_counts, s5_facts


class NextNumber(unittest.TestCase):
    def test_counts_on_from_the_highest_number_and_ignores_other_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "preview_maps"                          # does not exist yet: it is made
            self.assertEqual(files.next_number(folder, "preview", ".html"), 1)
            for name in ("preview1.html", "preview3.html", "preview_old.html", "preview2.txt", "notes.html", "xpreview9.html"):
                (folder / name).write_text("x")
            self.assertEqual(files.next_number(folder, "preview", ".html"), 4)     # after 3, not after 9 or the odd names
            self.assertEqual(files.next_number(folder, "facts", ".csv"), 1)        # a different stem counts on its own


class PreviewsAreNeverOverwritten(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        db = cls.root / "t.db"
        fake_data.generate(persons=20000, surnames=100, seed=6, path=db, quiet=True)
        cls.patches = [mock.patch.object(config, "WORK", cls.root),
                       mock.patch.dict(config.PROFILES["fake"], {"database": str(db)}),
                       mock.patch.object(preview, "CACHE_DIR", cls.root / "cache")]      # fixed when preview.py is imported
        for patch in cls.patches:
            patch.start()
        with mock.patch.object(sys, "argv", ["s1_counts"]):
            s1_counts.main()
        with open(cls.root / "names.csv", newline="") as f:
            cls.names = [row["surname"] for row in csv.DictReader(f)]

    @classmethod
    def tearDownClass(cls):
        for patch in cls.patches:
            patch.stop()
        cls.tmp.cleanup()

    def run_preview(self, *extra):
        with mock.patch.object(sys, "argv", ["preview", "--names", self.names[0], "--periods", "2000", "2020", *extra]):
            preview.main()

    def test_each_preview_gets_its_own_numbered_file_in_preview_maps(self):
        folder = self.root / "preview_maps"
        self.run_preview()
        self.run_preview()
        self.assertEqual(sorted(p.name for p in folder.glob("preview*.html")), ["preview1.html", "preview2.html"])
        first = (folder / "preview1.html").read_text()
        self.assertIn("preview1.html: python3 -m pipeline.preview --names", first)     # the page says how it was made
        self.assertIn(self.names[0], first)
        self.assertIn("preview2.html", (folder / "preview2.html").read_text())

    def test_out_still_chooses_the_file(self):
        target = self.root / "somewhere" / "mine.html"
        self.run_preview("--out", str(target))
        self.assertTrue(target.exists())

    def test_a_few_names_of_stage_5_default_to_preview_facts_and_each_run_is_kept(self):
        for chosen in (self.names[:1], self.names[:2]):
            with mock.patch.object(sys, "argv", ["s5_facts", "--names", *chosen]):
                s5_facts.main()
        folder = self.root / "preview_facts"
        self.assertEqual(sorted(p.name for p in folder.glob("facts[0-9]*.csv")), ["facts1.csv", "facts2.csv"])
        self.assertEqual(sorted(p.name for p in folder.glob("report[0-9]*.txt")), ["report1.txt", "report2.txt"])
        with open(folder / "facts1.csv", newline="") as f:
            self.assertEqual({r["surname"] for r in csv.DictReader(f)}, set(self.names[:1]))     # run 1 was not replaced by run 2
        with open(folder / "facts.csv", newline="") as f:
            self.assertEqual({r["surname"] for r in csv.DictReader(f)}, set(self.names[:2]))     # facts.csv is the latest

    def test_a_full_run_still_goes_to_facts(self):
        with mock.patch.object(sys, "argv", ["s5_facts", "--limit", "3"]):
            s5_facts.main()
        self.assertTrue((self.root / "facts" / "facts.csv").exists())
        self.assertEqual(list((self.root / "facts").glob("facts[0-9]*.csv")), [])              # numbered copies are for --names runs


if __name__ == "__main__":
    unittest.main()
