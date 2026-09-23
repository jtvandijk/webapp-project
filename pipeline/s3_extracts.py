"""Stage 3: for each map period, one query pulls (surname, cell x, cell y, n) for every name on
the list at once, and the rows are split into chunk files by name - so stage 4 makes no database
queries at all, and each of its tasks only ever loads its own slice of names.

    python3 -m pipeline.s3_extracts                          # every name in work/names.csv, 200 chunks
    python3 -m pipeline.s3_extracts --limit 500 --chunks 20  # a small sample run
    python3 -m pipeline.s3_extracts --sources register       # one database at a time

--limit takes the first N names from work/names.csv (already sorted by s1_counts.py), for timing a
sample run before committing to the full name list. Which chunk a name's rows land in is
kde.names.chunk_of(key, chunks) - a pure function of the key, not an assignment stage 4 has to be
told separately, so a later, bigger run does not reshuffle chunks a smaller sample already used.

Writes work/chunks/<period id>/<chunk>.csv (surname, x, y, n) - every chunk file is written for
every period, even if empty, so stage 4 never has to special-case a missing file.
"""
import argparse
import csv
import time
from collections import defaultdict
from pathlib import Path

from . import config, db, sql
from .names import chunk_of, surname_key


def load_names(limit=None):
    """The names that get a page (work/names.csv, stage 1), sorted - optionally only the first
    `limit`, for a small sample run. Sorting first makes --limit reproducible run to run."""
    with open(config.WORK / "names.csv", newline="") as f:
        names = sorted(row["surname"] for row in csv.DictReader(f))
    return names[:limit] if limit else names


def extract_period(conn, cfg, period, names, chunks, out_dir):
    """One query for this period; its rows, aggregated by (standardised key, cell) so that spelling
    variants (O'Brien/OBrien) are merged once here rather than separately by every stage 4 task that
    happens to see one, split into `chunks` files by name. Returns the number of (name, cell) rows
    written."""
    make = sql.register_cells if period["source"] == "register" else sql.census_cells
    names_set = set(names)
    totals = defaultdict(float)
    for raw, ix, iy, n in db.fetch(conn, make(cfg, period["year"], surnames=names)):
        key = surname_key(raw)
        if key in names_set:      # defends against _surname_filter()'s coarse accent-folding gap
            totals[(key, ix, iy)] += n

    by_chunk = defaultdict(list)
    for (key, ix, iy), n in totals.items():
        by_chunk[chunk_of(key, chunks)].append((key, ix, iy, n))

    period_dir = out_dir / period["id"]
    period_dir.mkdir(parents=True, exist_ok=True)
    for chunk in range(chunks):
        with open(period_dir / f"{chunk}.csv", "w", newline="") as f:
            out = csv.writer(f)
            out.writerow(["surname", "x", "y", "n"])
            out.writerows(sorted(by_chunk.get(chunk, [])))
    return len(totals)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sources", nargs="*", choices=["register", "census"], default=["register", "census"],
                        help="which sources to extract from (default: both)")
    parser.add_argument("--limit", type=int, help="only the first N names from work/names.csv (a sample run)")
    parser.add_argument("--chunks", type=int, default=200, help="how many chunk files per period (default 200)")
    parser.add_argument("--out-dir", default=str(config.WORK / "chunks"))
    args = parser.parse_args()
    sources = set(args.sources)
    out_dir = Path(args.out_dir)

    names = load_names(args.limit)
    if not names:
        raise SystemExit("No names in work/names.csv - run s1_counts.py first.")

    cfg = config.settings()
    periods = [p for p in config.PERIODS if p["source"] in sources]
    connections = {}

    def connect_once(source):
        if source not in connections:
            connections[source] = db.connect(source)
        return connections[source]

    for period in periods:
        started = time.perf_counter()
        rows = extract_period(connect_once(period["source"]), cfg, period, names, args.chunks, out_dir)
        print(f"{period['id']} ({period['source']}): {rows:,} name-cell rows, {time.perf_counter() - started:.1f}s")

    for conn in connections.values():
        conn.close()
    print(f"{len(names):,} names, {args.chunks} chunks, {len(periods)} periods written to {out_dir}")


if __name__ == "__main__":
    main()
