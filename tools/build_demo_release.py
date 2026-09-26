#!/usr/bin/env python3
"""Build a small demo release from FAKE data, to look at - no TRE, no database, no HPC.

Runs the real code of stages 1 to 6 on the fake database (pipeline/fake_data.py), in one go, into its own folder
work/demo_release/ (so nothing in your own work/ is touched), then draws pipeline/preview_web.py's page for a few
names: one whose 1911/1921 map is a copy of 1901's (the Scotland rule), the name with the most maps, and one of the
smallest. Use it to see what an assembled release looks like before running stage 6 on real output, or after
changing stage 6 / the maps.

    python3 tools/build_demo_release.py            # then open work/demo_release/preview_web/preview.html
    python3 tools/build_demo_release.py --seed 5   # another fake dataset

It starts by clearing its own folder (work/demo_release, or --folder), but only one it made itself - a folder with
anything else in it is refused, never emptied.

The names and the shapes are FAKE (made-up people in real towns); only the map code, the file formats and the
page are real. Always the fake database, whatever GBNAMES_PROFILE says in your shell: this cannot touch the real one.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# before the pipeline is imported: it reads these when it is imported, and this must never reach the real database
for key in [k for k in os.environ if k.startswith("GBNAMES_")]:
    del os.environ[key]
os.environ["GBNAMES_PROFILE"] = "fake"

from pipeline import config, fake_data, merge_release, preview_web, s1_counts, s2_surfaces, s3_extracts, s4_maps, s5_facts, s6_assemble  # noqa: E402


MARKER = ".demo_release"


def run(main, *argv):
    """Run one stage's main() in this process, as if typed with these arguments."""
    saved = sys.argv
    sys.argv = [main.__module__, *argv]
    try:
        main()
    finally:
        sys.argv = saved


def choose_names(names_dir, how_many=3):
    """A name with a copied map, the name with the most maps, and one of the smallest - from what was assembled."""
    bundles = {p.stem: json.loads(p.read_text()) for p in sorted(Path(names_dir).glob("*/*.json"))}
    copied = [n for n, b in bundles.items() if any("copyOf" in m for m in b["maps"].values())]
    by_maps = sorted(bundles, key=lambda n: (-len(bundles[n]["maps"]), n))
    chosen = []
    for name in (copied[:1] + by_maps[:1] + by_maps[-1:]):
        if name not in chosen:
            chosen.append(name)
    return chosen[:how_many] if how_many else chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=1, help="fake dataset (1 has a name with a copied 1911/1921 map)")
    parser.add_argument("--chunks", type=int, default=4)
    parser.add_argument("--persons", type=int, default=20000, help="people in the fake database (fewer is faster, and fewer names)")
    parser.add_argument("--folder", default=str(ROOT / "work" / "demo_release"), help="where to build it (default work/demo_release)")
    args = parser.parse_args()

    work = Path(args.folder)
    if work.exists():
        if not (work / MARKER).exists() and any(work.iterdir()):
            raise SystemExit(f"{work} exists and was not made by this tool, so it is not being cleared. Give --folder a new or empty folder.")
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / MARKER).write_text("made by tools/build_demo_release.py; this tool clears the folder each run\n")
    config.WORK = work
    database = work / "fake.db"
    config.PROFILES["fake"]["database"] = str(database)
    fake_data.generate(persons=args.persons, surnames=200, seed=args.seed, path=database, quiet=True)

    chunks = str(args.chunks)
    run(s1_counts.main)
    run(s2_surfaces.main)
    run(s3_extracts.main, "--chunks", chunks)
    for chunk in range(args.chunks):
        run(s4_maps.main, "--chunk", str(chunk), "--chunks", chunks)
    run(s5_facts.main)
    run(s6_assemble.main, "--prepare", "--chunks", chunks)
    for chunk in range(args.chunks):
        run(s6_assemble.main, "--chunk", str(chunk), "--chunks", chunks)
    run(merge_release.main, "--chunks", chunks)

    names = choose_names(work / "release" / "names")
    out = work / "preview_web" / "preview.html"
    run(preview_web.main, "--names", *names, "--out", str(out))
    print(f"\nDemo release (fake data): {work / 'release'}")
    print(f"Open in a browser:        {out}")


if __name__ == "__main__":
    main()
