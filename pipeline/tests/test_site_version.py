"""Every local CSS/JS reference in the site carries one and the same ?v= version (tools/bump_site_version.py),
so a browser never mixes a new file with a stale cached one."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class SiteVersion(unittest.TestCase):
    def test_every_local_css_js_reference_has_the_same_version(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "bump_site_version.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
