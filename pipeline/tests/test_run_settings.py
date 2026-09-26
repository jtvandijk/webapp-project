"""Tests for the run settings (run.settings): the parser, the shipped file, the qsub scripts that read it, and the
stages that take their defaults from it. Run from the project root:   python3 -m unittest discover -s pipeline/tests -t ."""
import csv
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import config, db, fake_data, preview, s1_counts, s3_extracts, s5_facts

HPC = config.ROOT / "pipeline" / "hpc"
HAVE_BASH = shutil.which("bash") is not None


class ReadRunSettings(unittest.TestCase):
    def test_nothing_set_means_everything(self):
        got = config.read_run_settings({})
        self.assertEqual((got["sources"], got["chunks"], got["limit"], got["facts"]), (["register", "census"], 200, None, None))
        self.assertEqual(got["census_years"], config.ALL_CENSUS_YEARS)
        self.assertFalse(got["sources_were_set"])

    def test_values_are_read_and_an_empty_limit_or_facts_means_all(self):
        got = config.read_run_settings({"GBNAMES_SOURCES": "register", "GBNAMES_CHUNKS": "40", "GBNAMES_LIMIT": "5000",
                                        "GBNAMES_FACTS": "oac  imd", "GBNAMES_CENSUS_YEARS": "1911 1851 1851"})
        self.assertEqual((got["sources"], got["chunks"], got["limit"], got["facts"]), (["register"], 40, 5000, ["oac", "imd"]))
        self.assertEqual(got["census_years"], [1851, 1911])
        self.assertTrue(got["sources_were_set"])
        empty = config.read_run_settings({"GBNAMES_LIMIT": "", "GBNAMES_FACTS": "  ", "GBNAMES_CENSUS_YEARS": ""})
        self.assertEqual((empty["limit"], empty["facts"], empty["census_years"]), (None, None, config.ALL_CENSUS_YEARS))

    def test_a_typo_stops_the_run_and_names_the_setting(self):
        for env, name in [({"GBNAMES_SOURCES": "registers"}, "SOURCES"), ({"GBNAMES_SOURCES": " "}, "SOURCES"),
                          ({"GBNAMES_CHUNKS": "many"}, "CHUNKS"), ({"GBNAMES_CHUNKS": "0"}, "CHUNKS"),
                          ({"GBNAMES_LIMIT": "lots"}, "LIMIT"), ({"GBNAMES_LIMIT": "-5"}, "LIMIT"),
                          ({"GBNAMES_CENSUS_YEARS": "1871"}, "CENSUS_YEARS"), ({"GBNAMES_CENSUS_YEARS": "18x1"}, "CENSUS_YEARS")]:
            with self.assertRaises(SystemExit) as stopped:
                config.read_run_settings(env)
            self.assertIn(f"GBNAMES_{name}", str(stopped.exception), env)


@unittest.skipUnless(HAVE_BASH, "bash is not available")
class TheShippedFilesAndScripts(unittest.TestCase):
    def test_run_settings_is_valid_when_sourced_and_is_in_git(self):
        out = subprocess.run(["bash", "-c", "set -a; source run.settings; env"], cwd=config.ROOT, capture_output=True, text=True, check=True).stdout
        env = dict(line.split("=", 1) for line in out.splitlines() if line.startswith("GBNAMES_") and "=" in line)
        for name in ("SOURCES", "CHUNKS", "LIMIT", "FACTS", "CENSUS_YEARS"):
            self.assertIn(f"GBNAMES_{name}", env, f"run.settings does not set GBNAMES_{name}")
        config.read_run_settings(env)                                   # does not raise: the shipped values are valid
        if (config.ROOT / ".git").exists():
            ignored = subprocess.run(["git", "check-ignore", "-q", "run.settings"], cwd=config.ROOT).returncode == 0
            self.assertFalse(ignored, "run.settings must be in git (it holds no secrets); only .env stays out")

    def test_every_stage_script_reads_run_settings_and_types_no_run_choices(self):
        scripts = sorted(HPC.glob("stage*.sh"))
        self.assertEqual([s.name for s in scripts], [f"stage{n}.sh" for n in range(1, 7)])
        for script in scripts:
            text = script.read_text()
            self.assertEqual(subprocess.run(["bash", "-n", str(script)]).returncode, 0, f"{script.name} has a syntax error")
            commands = [line.split("#")[0].strip() for line in text.splitlines()]     # what the script really runs, no comments
            self.assertIn("source run.settings", commands, f"{script.name} does not read run.settings")
            self.assertIn("export PYTHONUNBUFFERED=1", commands, script.name)
            for typed in ("SOURCES=", "LIMIT=", "CHUNKS=", "FACTS="):
                self.assertFalse([c for c in commands if c.startswith(typed)], f"{script.name} types {typed} itself")
            self.assertEqual("source .env" in commands, script.name not in ("stage4.sh", "stage6.sh"), script.name)   # neither needs a database

    def _guard(self, script, last, chunks):
        text = (HPC / script).read_text().split("\n")
        block = "\n".join(text[[i for i, l in enumerate(text) if l.startswith("# --- array guard")][0]:
                               [i for i, l in enumerate(text) if l.startswith("# --- end array guard")][0]])
        env = {"GBNAMES_CHUNKS": str(chunks), "PATH": "/usr/bin:/bin"}
        if last is not None:
            env["SGE_TASK_LAST"] = str(last)
        return subprocess.run(["bash", "-c", "set -euo pipefail\n" + block], env=env, capture_output=True, text=True)

    def test_stage_4_refuses_an_array_range_that_does_not_match_the_chunks(self):
        wrong = self._guard("stage4.sh", 100, 200)
        self.assertNotEqual(wrong.returncode, 0)
        self.assertIn("qsub -t 1-200", wrong.stderr)                  # tells you the command that would be right
        for last in (200, "undefined", None):                       # the right range, and jobs that are not arrays
            self.assertEqual(self._guard("stage4.sh", last, 200).returncode, 0, last)

    def test_stage_6_has_the_same_array_guard_as_stage_4(self):
        wrong = self._guard("stage6.sh", 100, 200)
        self.assertNotEqual(wrong.returncode, 0)
        self.assertIn("qsub -t 1-200 pipeline/hpc/stage6.sh", wrong.stderr)
        for last in (200, "undefined", None):
            self.assertEqual(self._guard("stage6.sh", last, 200).returncode, 0, last)


    def _chunk_chosen(self, script, task_id):
        text = (HPC / script).read_text().split("\n")
        block = "\n".join(text[[i for i, l in enumerate(text) if l.startswith("# --- task id")][0]:
                               [i for i, l in enumerate(text) if l.startswith("# --- end task id")][0]])
        env = {"PATH": "/usr/bin:/bin"}
        if task_id is not None:
            env["SGE_TASK_ID"] = str(task_id)
        done = subprocess.run(["bash", "-c", "set -euo pipefail\n" + block + '\necho "$CHUNK"'], env=env, capture_output=True, text=True)
        return done.returncode, done.stdout.strip()

    def test_an_array_task_does_its_own_chunk_and_a_plain_qsub_does_chunk_0(self):
        for script in ("stage4.sh", "stage6.sh"):
            self.assertEqual(self._chunk_chosen(script, 1), (0, "0"), script)
            self.assertEqual(self._chunk_chosen(script, 200), (0, "199"), script)
            self.assertEqual(self._chunk_chosen(script, "undefined"), (0, "0"), script)    # what SGE sets outside an array job
            self.assertEqual(self._chunk_chosen(script, None), (0, "0"), script)           # run by hand


class BeforeStageOneHasRun(unittest.TestCase):
    def test_a_missing_names_or_counts_file_says_to_run_stage_1(self):
        with tempfile.TemporaryDirectory() as empty, mock.patch.object(config, "WORK", Path(empty)):
            for action in (lambda: s3_extracts.load_names(), lambda: s5_facts.load_counts(),
                           lambda: (sys.argv.__setitem__(slice(None), ["s5_facts", "--names", "smith"]), s5_facts.main())):
                with self.assertRaises(SystemExit) as stopped:
                    action()
                self.assertIn("stage1.sh", str(stopped.exception))                  # not a raw "no such file" error
                self.assertIn("run  qsub", str(stopped.exception))


class StagesFollowTheSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        database = cls.root / "t.db"
        fake_data.generate(persons=20000, surnames=100, seed=6, path=database, quiet=True)
        cls.patches = [mock.patch.object(config, "WORK", cls.root), mock.patch.dict(config.PROFILES["fake"], {"database": str(database)}),
                       mock.patch.object(preview, "CACHE_DIR", cls.root / "cache")]
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

    def extract(self, *flags):
        out = self.root / "chunks_test"
        shutil.rmtree(out, ignore_errors=True)
        with mock.patch.object(sys, "argv", ["s3_extracts", "--out-dir", str(out), "--sources", "register", *flags]):
            s3_extracts.main()
        seen = set()
        for path in out.glob("*/*.csv"):
            with open(path, newline="") as f:
                seen |= {row["surname"] for row in csv.DictReader(f)}
        return (out / "CHUNKS").read_text(), seen

    def test_stage_3_takes_its_chunks_and_names_from_the_settings_and_a_flag_wins(self):
        with mock.patch.object(config, "RUN_CHUNKS", 3), mock.patch.object(config, "RUN_LIMIT", 4):
            chunks, seen = self.extract()
            self.assertEqual(chunks, "3")
            self.assertLessEqual(len(seen), 4)
            self.assertEqual(self.extract("--chunks", "5", "--limit", "8")[0], "5")          # the flag overrides

    def test_stage_5_reads_the_sources_and_a_sample_limit_does_not_hide_names_asked_for(self):
        opened, real = [], db.connect

        def spy(group, profile=None):
            opened.append(group)
            return real(group, profile)
        with_facts = sorted(s5_facts.reference_years(s5_facts.load_counts(), self.names))     # register facts need a register year with 100+ bearers
        wanted = [with_facts[0], with_facts[-1]]
        self.assertGreater(self.names.index(with_facts[-1]), 0)         # the last one is outside a limit of 1
        with mock.patch.object(config, "RUN_SOURCES", ["register"]), mock.patch.object(config, "RUN_LIMIT", 1), \
                mock.patch.object(db, "connect", spy), \
                mock.patch.object(sys, "argv", ["s5_facts", "--out-dir", str(self.root / "s5"), "--names", *wanted]):
            s5_facts.main()
        self.assertEqual(set(opened), {"register"})                    # the census was not opened: the setting was used
        with open(self.root / "s5" / "facts.csv", newline="") as f:
            self.assertEqual({row["surname"] for row in csv.DictReader(f)} & set(wanted), set(wanted))

    def test_the_preview_uses_the_sources_only_when_run_settings_sets_them(self):
        register = [str(y) for y in config.MAP_YEARS["register"]]
        name = max(self.names, key=lambda n: 0)                        # any name: the periods are what is tested
        for was_set, expect_census in ((True, False), (False, True)):
            settings = dict(config.RUN, sources_were_set=was_set, sources=["register"])
            out = self.root / f"preview_{was_set}.html"
            with mock.patch.object(config, "RUN", settings), mock.patch.object(config, "RUN_SOURCES", ["register"]), \
                    mock.patch.object(sys, "argv", ["preview", "--names", name, "--out", str(out)]):
                preview.main()
            page = out.read_text()
            self.assertEqual(any(f"<td>{y}</td>" in page for y in config.MAP_YEARS["census"]), expect_census, was_set)


if __name__ == "__main__":
    unittest.main()
