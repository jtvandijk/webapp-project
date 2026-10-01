"""tools/build_lookups.py: the real release's lookups.json is complete and passes the validator's own check of it."""
import sys
import unittest

from pipeline import config

sys.path.insert(0, str(config.ROOT / "tools"))
import build_lookups                       # noqa: E402
import validate_data                       # noqa: E402


@unittest.skipUnless(build_lookups.FPC_RAW.exists() and build_lookups.GB2C_RAW.exists(),
                     "the FPC/GB2C safeguarded downloads (raw-indicators/, git-ignored) are not both on this machine")
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
        self.assertEqual(len(self.lookups["gb2c"]["groups"]), 11)

    def test_ethnicity_has_every_configured_group_and_unknown(self):
        self.assertEqual(set(self.lookups["eth"]), set(config.ETH_GROUPS) | {config.ETH_UNKNOWN})

    def test_the_fpc_typos_are_handled(self):
        names = {g["name"] for g in self.lookups["fpc"]["groups"].values()}
        self.assertIn("Underprivileged dependent", names)
        self.assertIn("Ageing Blue-collar households", names)
        self.assertFalse([n for n in names if "  " in n or ":" in n], "a name still carries its code prefix or a double space")

    def test_gb2c_groups_have_a_name_and_our_own_colour_each(self):
        for code, group in self.lookups["gb2c"]["groups"].items():
            self.assertTrue(group["name"], code)
            self.assertRegex(group["colour"], r"^#[0-9a-fA-F]{6}$", code)
        self.assertEqual(len({g["colour"] for g in self.lookups["gb2c"]["groups"].values()}), 11)   # all distinct

    def test_gb2c_colours_are_spread_across_lightness_not_bunched_together(self):
        # a rough colour-blind-safety check: if two groups sit at nearly the same relative luminance, hue is all
        # that tells them apart, which is exactly what fails for red-green deficiency - so no two should be close.
        def luminance(hexcode):
            r, g, b = (int(hexcode[i:i + 2], 16) / 255 for i in (1, 3, 5))

            def lin(c):
                return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            r, g, b = lin(r), lin(g), lin(b)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        values = sorted(luminance(g["colour"]) for g in self.lookups["gb2c"]["groups"].values())
        gaps = [b - a for a, b in zip(values, values[1:])]
        self.assertGreater(min(gaps), 0.005, gaps)

    def test_the_ahah_text_matches_the_direction_of_the_data(self):
        self.assertIn("first decile is the healthiest", self.lookups["scales"]["ahah"]["text"])
        self.assertIn("first decile is the most deprived", self.lookups["scales"]["imd"]["text"])


if __name__ == "__main__":
    unittest.main()
