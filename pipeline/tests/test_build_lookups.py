"""tools/build_lookups.py: the real release's lookups.json is complete and passes the validator's own check of it."""
import sys
import unittest

from pipeline import config

sys.path.insert(0, str(config.ROOT / "tools"))
import build_lookups                       # noqa: E402
import validate_data                       # noqa: E402


@unittest.skipUnless(build_lookups.FPC_RAW.exists(), "the FPC colours file (raw-indicators/fpc/, git-ignored) is not on this machine")
class BuildLookups(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lookups = build_lookups.build()

    def test_it_passes_the_validators_check(self):
        report = validate_data.Report()
        validate_data.check_lookups(self.lookups, report)
        self.assertEqual(report.errors, [])

    def test_it_has_every_group_the_classifications_have(self):
        self.assertEqual((len(self.lookups["oac"]["supergroups"]), len(self.lookups["oac"]["groups"])), (8, 21))
        self.assertEqual((len(self.lookups["loac"]["supergroups"]), len(self.lookups["loac"]["groups"])), (7, 16))
        self.assertEqual(len(self.lookups["fpc"]["groups"]), 13)

    def test_ethnicity_has_every_configured_group_and_unknown(self):
        self.assertEqual(set(self.lookups["eth"]), set(config.ETH_GROUPS) | {config.ETH_UNKNOWN})

    def test_the_two_fpc_typos_are_handled(self):
        names = {g["name"] for g in self.lookups["fpc"]["groups"].values()}
        self.assertIn("Underprivileged dependent", names)
        self.assertFalse([n for n in names if "  " in n or ":" in n], "a name still carries its code prefix or a double space")

    def test_the_ahah_text_matches_the_direction_of_the_data(self):
        self.assertIn("first decile is the healthiest", self.lookups["scales"]["ahah"]["text"])
        self.assertIn("first decile is the most deprived", self.lookups["scales"]["imd"]["text"])


if __name__ == "__main__":
    unittest.main()
