"""Stage 4 (the heavy step): the map for every name and period in one chunk.

    python3 -m pipeline.s4_maps --chunk 0 --chunks 200
    python3 -m pipeline.s4_maps --chunk $SGE_TASK_ID --chunks 200 --sources register    # from an array job

Makes NO database queries and NO network access at all - everything it needs (a chunk's point
extracts, the population surfaces) was already written to disk by stage 2 and stage 3, so this can
run as a large SGE array job (see pipeline/hpc/stage4.sh) without hitting the database once per
task, only once per PERIOD, in stage 3. Each task loads the (small) population surfaces and the
coastline once, then works through its own names one at a time - never holding more than one
name's working grids in memory alongside the surfaces, so memory use does not grow with how many
names are in a chunk.

For each name (its own bandwidth, its own LEVEL_MASS from kde.size_level_mass(), the usual Scotland
substitution rule): writes one line per (name, period) to work/maps/chunk_<n>.jsonl (a "build"
period carries its GeoJSON; a "substitute" period only names which period to copy - resolving that
copy is stage 6's job, so identical geometry is never written out twice) and one row per
(name, period) to work/stats/chunk_<n>.csv (bearers, bandwidth, the resolved LEVEL_MASS, the
concentration/second_blob_share measures, and the map's own size/shape - kept out of the GeoJSON
itself, which only the website downloads and should stay lean).

Self-checking: writes work/maps/chunk_<n>.done only once a chunk finishes without error, and skips
straight past a chunk that already has one (pass --force to redo it anyway) - so re-submitting the
same array job after some tasks failed or were killed only repeats the ones that did not finish.
"""
import argparse
import csv
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import config, kde, rules


def load_surfaces(surfaces_dir, periods):
    """{period id: population surface}, read from stage 2's output."""
    surfaces = {}
    for period in periods:
        path = surfaces_dir / f"{period['id']}.npy"
        if not path.exists():
            raise SystemExit(f"No population surface at {path} - run s2_surfaces.py first.")
        surfaces[period["id"]] = np.load(path)
    return surfaces


def load_chunk(chunks_dir, periods, chunk):
    """{period id: {name: (cell x, cell y, n)}} for one chunk, read from stage 3's output - no
    database access at all."""
    by_period = {}
    for period in periods:
        path = chunks_dir / period["id"] / f"{chunk}.csv"
        if not path.exists():
            raise SystemExit(f"No chunk file at {path} - run s3_extracts.py first (with a matching --chunks).")
        grouped = defaultdict(lambda: ([], [], []))
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                g = grouped[row["surname"]]
                g[0].append(int(row["x"]))
                g[1].append(int(row["y"]))
                g[2].append(float(row["n"]))
        by_period[period["id"]] = {k: (np.array(v[0], int), np.array(v[1], int), np.array(v[2], float))
                                   for k, v in grouped.items()}
    return by_period


def process_name(name, cells_by_period, periods, pop_surfaces, land):
    """(jsonl rows, stats rows) for one name across every period it is asked for."""
    have = [c for c in cells_by_period.values() if c is not None]
    bandwidth = kde.choose_bandwidth(have)
    biggest_pid, biggest_cells = max(((pid, c) for pid, c in cells_by_period.items() if c is not None),
                                     key=lambda pc: pc[1][2].sum())
    biggest_grid = kde.to_grid(*biggest_cells)
    second = kde.second_blob_share(biggest_grid, bandwidth, pop_surfaces[biggest_pid], land, config.WEIGHT_POWER)
    concentration = kde.concentration(biggest_grid, bandwidth, pop_surfaces[biggest_pid], land, config.WEIGHT_POWER)
    levels = kde.size_level_mass(int(biggest_cells[2].sum()), second)

    timings = {}
    resolved = rules.build_maps(periods, cells_by_period, bandwidth, pop_surfaces, land, mode="mass",
                                levels=levels, timings=timings)

    jsonl_rows, stats_rows = [], []
    for period in periods:
        bands, r = resolved[period["id"]]
        cells = cells_by_period.get(period["id"])
        total = int(cells[2].sum()) if cells is not None else 0
        collection = kde.geojson(bands) if bands else None

        row = {"surname": name, "period": period["id"], "action": r.action, "bearers": total}
        if r.reason:
            row["reason"] = r.reason
        if r.action == "substitute":
            row["reference"] = r.reference
        elif collection:
            row["geojson"] = collection
        jsonl_rows.append(row)

        size_kb = len(json.dumps(collection, separators=(",", ":"))) / 1024 if collection else 0.0
        areas = sum(len(kde._polygons(b)) for b in bands or [])
        points = sum(len(rg.coords) for b in bands or [] for g in kde._polygons(b) for rg in [g.exterior, *g.interiors])
        ms = timings.get(r.reference if r.action == "substitute" else period["id"], 0.0) * 1000
        stats_rows.append([name, period["id"], r.action, total, round(bandwidth), config.WEIGHT_POWER,
                           *[round(x, 4) for x in levels], round(second, 4), round(concentration, 4),
                           areas, points, round(size_kb, 2), round(ms, 1)])
    return jsonl_rows, stats_rows


STATS_HEADER = ["surname", "period", "action", "bearers", "bandwidth_m", "weight_power",
               "level1", "level2", "level3", "second_blob_share", "concentration",
               "separate_areas", "points", "geojson_kb", "build_ms"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chunk", type=int, required=True, help="which chunk this task processes (0-based)")
    parser.add_argument("--chunks", type=int, default=200, help="total number of chunks (must match s3_extracts.py)")
    parser.add_argument("--sources", nargs="*", choices=["register", "census"], default=["register", "census"])
    parser.add_argument("--chunks-dir", default=str(config.WORK / "chunks"))
    parser.add_argument("--surfaces-dir", default=str(config.WORK / "surfaces"))
    parser.add_argument("--out-dir", default=str(config.WORK / "maps"))
    parser.add_argument("--stats-dir", default=str(config.WORK / "stats"))
    parser.add_argument("--force", action="store_true", help="redo this chunk even if it already finished")
    args = parser.parse_args()

    out_dir, stats_dir = Path(args.out_dir), Path(args.stats_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stats_dir.mkdir(parents=True, exist_ok=True)
    done_marker = out_dir / f"chunk_{args.chunk}.done"
    if done_marker.exists() and not args.force:
        print(f"chunk {args.chunk} already finished ({done_marker}) - skipping. Use --force to redo it.")
        return

    sources = set(args.sources)
    periods = [p for p in config.PERIODS if p["source"] in sources]
    needed = list(periods)
    if any(p["year"] in config.SCOTLAND_MISSING_YEARS for p in periods):
        needed += [p for p in config.PERIODS if p["year"] == config.SCOTLAND_REFERENCE_YEAR and p not in periods]

    started = time.perf_counter()
    land = kde.Land()
    pop_surfaces = load_surfaces(Path(args.surfaces_dir), needed)
    by_period = load_chunk(Path(args.chunks_dir), needed, args.chunk)
    names = sorted(set().union(*(d.keys() for d in by_period.values())))
    print(f"chunk {args.chunk}: {len(names):,} names, {len(periods)} periods, loaded in {time.perf_counter() - started:.1f}s")

    jsonl_path = out_dir / f"chunk_{args.chunk}.jsonl"
    stats_path = stats_dir / f"chunk_{args.chunk}.csv"
    with open(jsonl_path, "w") as jsonl_file, open(stats_path, "w", newline="") as stats_file:
        stats_out = csv.writer(stats_file)
        stats_out.writerow(STATS_HEADER)
        for i, name in enumerate(names, start=1):
            cells_by_period = {pid: by_period[pid].get(name) for pid in by_period}
            jsonl_rows, stats_rows = process_name(name, cells_by_period, periods, pop_surfaces, land)
            for row in jsonl_rows:
                jsonl_file.write(json.dumps(row, separators=(",", ":")) + "\n")
            stats_out.writerows(stats_rows)
            if i % 50 == 0 or i == len(names):
                print(f"chunk {args.chunk}: {i:,}/{len(names):,} names, {time.perf_counter() - started:.1f}s elapsed")

    done_marker.write_text(f"{len(names)} names, {time.perf_counter() - started:.1f}s\n")
    print(f"chunk {args.chunk} done: {jsonl_path}, {stats_path}")


if __name__ == "__main__":
    main()
