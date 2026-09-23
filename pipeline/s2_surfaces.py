"""Stage 2: the smoothed surface of everybody, once per map period.

    python3 -m pipeline.s2_surfaces                    # every period, both sources
    python3 -m pipeline.s2_surfaces --sources register  # one database at a time, like s1_counts.py

Every name's map divides by this surface (kde.weigh()), so it is computed once per period here and
read back from disk by every stage 4 task, rather than being queried or recomputed once per name -
the same reasoning as stage 3 doing one query per period instead of one per name. It changes only
if the underlying data or POPULATION_BANDWIDTH_M changes, not per calibration run, so re-running
this stage is not part of the normal preview.py-style iteration loop.

Writes work/surfaces/<period id>.npy (a plain numpy array, kde.GRID shaped) and a
work/surfaces/manifest.csv (period id, bearers, seconds taken) to check against before trusting a
run's surfaces are current.
"""
import argparse
import csv
import time
from pathlib import Path

import numpy as np

from . import config, db, kde, sql


def build_surface(conn, cfg, period):
    """The smoothed surface of everybody for one period (kde.population_surface, current
    POPULATION_BANDWIDTH_M)."""
    make = sql.register_cells if period["source"] == "register" else sql.census_cells
    rows = db.fetch(conn, make(cfg, period["year"], by_surname=False))
    ix, iy, n = zip(*rows) if rows else ((), (), ())
    return kde.population_surface(np.array(ix, int), np.array(iy, int), np.array(n, float))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sources", nargs="*", choices=["register", "census"], default=["register", "census"],
                        help="which sources to build surfaces for (default: both)")
    parser.add_argument("--out-dir", default=str(config.WORK / "surfaces"))
    args = parser.parse_args()
    sources = set(args.sources)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = config.settings()
    periods = [p for p in config.PERIODS if p["source"] in sources]
    connections = {}

    def connect_once(source):
        if source not in connections:
            connections[source] = db.connect(source)
        return connections[source]

    manifest = []
    for period in periods:
        started = time.perf_counter()
        surface = build_surface(connect_once(period["source"]), cfg, period)
        elapsed = time.perf_counter() - started
        np.save(out_dir / f"{period['id']}.npy", surface)
        manifest.append((period["id"], period["source"], int(surface.sum()), round(elapsed, 1)))
        print(f"{period['id']} ({period['source']}): {int(surface.sum()):,} people on the grid, {elapsed:.1f}s")

    for conn in connections.values():
        conn.close()

    with open(out_dir / "manifest.csv", "w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["period", "source", "people", "seconds"])
        out.writerows(manifest)
    print(f"{len(manifest)} surfaces written to {out_dir}")


if __name__ == "__main__":
    main()
