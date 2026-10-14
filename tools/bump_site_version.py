#!/usr/bin/env python3
"""Stamp a new version on every reference the site makes to its own CSS and JavaScript, so browsers fetch
the new files straight after an update instead of reusing a cached copy for up to the server's max-age.

    python3 tools/bump_site_version.py            # new version = today's date (a second run on one day adds .2, .3, ...)
    python3 tools/bump_site_version.py --check    # only check that every reference carries one and the same version

Run it once the site code is ready to go out. Then send every file it lists, PLUS every site file you changed
(a file whose content changed but that imports nothing, e.g. css/style.css, is not in its list). Simplest:
send index.html, about.html, css/ and js/ whole.

What it rewrites, in site/*.html and site/js/*.js: "css/x.css", "js/x.js" and "./x.js" (the imports between
the JS modules) -> "...?v=<version>". The imports matter as much as the HTML: a new app.js that imports
"./indicators.js" without the tag would still get the old cached indicators.js. vendor/ (Bootstrap,
Leaflet) is left alone - it never changes. The data release is versioned separately (site/js/data.js:
manifest.json and lookups.json are always re-checked, the per-name files carry the release version).
Standard library only.
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
# a quoted local CSS/JS reference, with or without an existing ?v=... tag
REFERENCE = re.compile(r"""(["'])((?:css/|js/|\./)[\w./-]+\.(?:css|js))(?:\?v=([^"']*))?\1""")


def site_files():
    return sorted(SITE.glob("*.html")) + sorted((SITE / "js").glob("*.js"))


def versions_in_use():
    """{version or None: [(file, reference), ...]} over every local CSS/JS reference."""
    found = {}
    for path in site_files():
        for match in REFERENCE.finditer(path.read_text(encoding="utf-8")):
            found.setdefault(match.group(3), []).append((path.relative_to(SITE), match.group(2)))
    return found


def next_version(current):
    today = datetime.date.today().isoformat()
    if current is None or not current.startswith(today):
        return today
    head, _, tail = current.partition(".")
    return f"{today}.{int(tail) + 1 if tail.isdigit() else 2}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="check only; exit 1 unless every reference has one version")
    parser.add_argument("--version", help="use this version instead of today's date")
    args = parser.parse_args()

    found = versions_in_use()
    if args.check:
        if None in found or len(found) != 1:
            for version, refs in sorted(found.items(), key=lambda kv: str(kv[0])):
                print(f"version {version!r}: " + ", ".join(f"{f}:{r}" for f, r in refs))
            print("NOT OK: every local CSS/JS reference should carry the same ?v= version")
            return 1
        print(f"OK: {sum(len(r) for r in found.values())} references, all ?v={next(iter(found))}")
        return 0

    current = max((v for v in found if v), default=None)
    version = args.version or next_version(current)
    changed = []
    for path in site_files():
        text = path.read_text(encoding="utf-8")
        new = REFERENCE.sub(lambda m: f"{m.group(1)}{m.group(2)}?v={version}{m.group(1)}", text)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(path.relative_to(SITE))
    print(f"version {current} -> {version}; tags updated in (site/...):")
    for path in changed:
        print(f"  {path}")
    print("Send these PLUS every other site file you changed (simplest: index.html, about.html, css/ and js/ whole).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
