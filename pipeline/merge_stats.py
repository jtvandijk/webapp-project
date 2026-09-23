"""Merge stage 4's per-chunk stats CSVs into one file - a real merge step, not something stage 4
does itself, since many array tasks writing to the same file at once is a corruption risk (that is
also why each chunk gets its own file in the first place, not one shared file appended to).

    python3 -m pipeline.merge_stats                     # every work/stats/chunk_*.csv -> work/stats.csv

Cheap and safe to re-run at any point during a long array job, to check progress on what has
finished so far - it does not touch or require the .done markers, it just reads whatever chunk CSVs
already exist.
"""
import argparse
import csv
from pathlib import Path

from . import config
from .s4_maps import STATS_HEADER


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stats-dir", default=str(config.WORK / "stats"))
    parser.add_argument("--out", default=str(config.WORK / "stats.csv"))
    args = parser.parse_args()

    chunks = sorted(Path(args.stats_dir).glob("chunk_*.csv"))
    if not chunks:
        raise SystemExit(f"No chunk stats CSVs in {args.stats_dir} - run s4_maps.py first.")

    rows = 0
    with open(args.out, "w", newline="") as out_file:
        out = csv.writer(out_file)
        out.writerow(STATS_HEADER)
        for chunk_path in chunks:
            with open(chunk_path, newline="") as f:
                reader = csv.reader(f)
                next(reader)          # each chunk file repeats the header; skip it here
                for row in reader:
                    out.writerow(row)
                    rows += 1
    print(f"{rows:,} rows from {len(chunks)} chunk files -> {args.out}")


if __name__ == "__main__":
    main()
