#!/usr/bin/env python3
"""Split a release's facts.csv (one row per name and fact) into one small JSON file per name,
sharded the same way as names/<xx>/<name>.json, so the website can fetch a name's facts without
downloading every other name's.

Usage:   python3 tools/split_facts.py data/facts.csv --out-dir data/facts

facts.csv is already sorted by name then fact (pipeline/merge_release.py's build_facts_table), so
this reads it as a single stream, grouping consecutive rows by name - never more than one name's
rows in memory at a time.
"""
import argparse
import csv
import itertools
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("facts_csv", help="the release's facts.csv")
    parser.add_argument("--out-dir", default="data/facts", help="where to write <xx>/<name>.json (default data/facts)")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)

    with open(args.facts_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        if header != ["name", "fact", "data"]:
            raise SystemExit(f"{args.facts_csv}: expected header name,fact,data, got {header}")

        names = 0
        rows = 0
        for name, group in itertools.groupby(reader, key=lambda row: row[0]):
            facts = {}
            for _, fact, data in group:
                facts[fact] = json.loads(data)
                rows += 1
            path = out_dir / name[:2] / f"{name}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(facts, separators=(",", ":"), ensure_ascii=False))
            names += 1

    print(f"{names:,} names, {rows:,} facts written to {out_dir}")


if __name__ == "__main__":
    main()
