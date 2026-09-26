"""Merge stage 6's per-chunk output into the whole-release files - a real merge step, not something
stage 6 does itself, for the same reason merge_stats.py exists: many array tasks writing to the same
shared file at once is a corruption risk, so each chunk writes its own (work/release/index_parts/chunk_N.txt),
and this reads all of them together.

    python3 -m pipeline.merge_release                     # every work/release/index_parts/chunk_*.txt -> the release

Cheap and safe to re-run at any point during a long array job, to check progress - it does not touch or
require the .done markers, it just reads whatever chunk index files already exist (same pattern as
merge_stats.py). Writes, under --out-dir (default work/release):

    index/<xx>.json      the search index: every name that got a file, per first two letters, sorted
    masks/scotland.json  the Scotland mask, reprojected from pipeline/reference/scotland_outline.geojson
                         the same way stage 4 reprojects every map (kde._to_lonlat, kde._repair)
    manifest.json        built from config.py: periods, threshold, masks. The presentational bits config.py
                         has no equivalent of (source descriptions, basemap tiles, level colours) are the
                         same fixed text tools/build_sample_data.py already uses for this project - real
                         content, not made up, but a website/copy decision, so treat it as a starting point
                         to edit, not a final answer, the same way lookups.json is left for later entirely.
"""
import argparse
import datetime
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import mapping, shape

from . import config, kde

# The same fixed text tools/build_sample_data.py already uses (a real, working choice for this project,
# not made up) - see the module docstring above.
SOURCE_TEXT = {
    "census": {"label": "Historical censuses", "short": "Census", "counts": "All residents"},
    "register": {"label": "Consumer registers", "short": "Registers", "counts": "Adults (estimated)"},
}
LEVELS = [
    {"level": 1, "label": "Concentrated", "colour": "#6baed6"},
    {"level": 2, "label": "More concentrated", "colour": "#4292c6"},
    {"level": 3, "label": "Most concentrated", "colour": "#2171b5"},
]
MASKS = {
    "scotland": {"url": "masks/scotland.json", "colour": "#dcdcdc", "opacity": 0.7, "label": "No data for Scotland"},
}
BASEMAP = {
    "center": [54.505, -4], "zoom": 6, "minZoom": 6, "maxZoom": 12,
    "maxBounds": [[50, -28], [62, 20]],
    "tiles": [
        {"url": "https://maps.cdrc.ac.uk/tiles/shine_urbanmask_light/{z}/{x}/{y}.png",
         "attribution": "Contains Ordnance Survey data © Crown copyright", "bounds": [[50, -28], [62, 20]]},
        {"url": "https://maps.cdrc.ac.uk/tiles/shine_labels_gbnames/{z}/{x}/{y}.png",
         "labels": True, "bounds": [[50, -12], [62, 4]]},
    ],
}
EXAMPLES = ["smith", "macdonald", "davies", "patel", "pascoe"]      # names already used to test this pipeline; a real editorial pick can replace this


def build_index(index_parts_dir, out_dir):
    """{prefix: [names, ...]}, read from every chunk's own list of names it wrote (not the actual
    names/ files - much cheaper, and exactly what each chunk itself knows it wrote)."""
    by_prefix = defaultdict(set)
    for path in sorted(Path(index_parts_dir).glob("chunk_*.txt")):
        for name in path.read_text().splitlines():
            if name:
                by_prefix[name[:2]].add(name)
    for prefix, names in by_prefix.items():
        write_json(Path(out_dir) / "index" / f"{prefix}.json", sorted(names))
    return by_prefix


def build_scotland_mask(reference_path):
    """masks/scotland.json: the Scotland outline in longitude/latitude, the same reprojection every map
    already goes through (kde._to_lonlat, kde._repair) - the reference file itself is in British National
    Grid metres, like every other reference/working geometry in this pipeline."""
    doc = json.loads(Path(reference_path).read_text())
    features = []
    for feature in doc["features"]:
        geometry = kde._repair(shapely.transform(shape(feature["geometry"]),
                                                  lambda c: np.column_stack(kde._to_lonlat.transform(c[:, 0], c[:, 1]))))
        features.append({"type": "Feature", "properties": {}, "geometry": mapping(geometry)})
    return {"type": "FeatureCollection", "features": features}


def build_manifest(version, synthetic=False):
    periods = []
    for period in config.PERIODS:
        entry = dict(period)
        if period["source"] == "census" and period["year"] in config.SCOTLAND_MISSING_YEARS:
            entry["mask"] = "scotland"
            entry["note"] = "Census data for Scotland are not available for this year."
        periods.append(entry)
    thresholds = set(config.THRESHOLD.values())
    if len(thresholds) != 1:
        raise SystemExit(f"config.THRESHOLD has more than one value ({config.THRESHOLD}) - manifest.json needs one number; "
                         "decide which, or how to show two, before building it.")
    return {
        "schema": 1,
        "release": {"version": version, "date": datetime.date.today().isoformat(), "synthetic": synthetic},
        "threshold": thresholds.pop(),
        "sources": {
            "census": {**SOURCE_TEXT["census"], "coverage": [min(config.CENSUS_YEARS), max(config.CENSUS_YEARS)]},
            "register": {**SOURCE_TEXT["register"], "coverage": [min(config.REGISTER_YEARS), max(config.REGISTER_YEARS)]},
        },
        "periods": periods,
        "levels": LEVELS,
        "masks": MASKS,
        "basemap": BASEMAP,
        "examples": EXAMPLES,
    }


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--index-parts-dir", default=str(config.WORK / "release" / "index_parts"))
    parser.add_argument("--out-dir", default=str(config.WORK / "release"))
    parser.add_argument("--reference", default=str(config.ROOT / "pipeline" / "reference" / "scotland_outline.geojson"))
    parser.add_argument("--chunks", type=int, default=config.RUN_CHUNKS, help="how many chunks to expect (default GBNAMES_CHUNKS in run.settings)")
    parser.add_argument("--version", default="0.1.0-dev", help="release.version in manifest.json - a release-management choice, not derived from the data")
    parser.add_argument("--synthetic", action="store_true", help="flag this release as sample/made-up data (fake_data.py runs)")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)

    found = sorted(Path(args.index_parts_dir).glob("chunk_*.txt"))
    if not found:
        raise SystemExit(f"No chunk index files in {args.index_parts_dir} - run s6_assemble.py first.")
    missing = sorted(set(range(args.chunks)) - {int(p.stem.removeprefix("chunk_")) for p in found})
    if missing:
        print(f"WARNING: only {len(found)} of {args.chunks} expected chunks are present - missing: "
             f"{', '.join(map(str, missing))}. This merge will NOT include them.")

    by_prefix = build_index(args.index_parts_dir, out_dir)
    write_json(out_dir / "masks" / "scotland.json", build_scotland_mask(args.reference))
    write_json(out_dir / "manifest.json", build_manifest(args.version, args.synthetic))

    n_names = sum(len(v) for v in by_prefix.values())
    print(f"{n_names:,} names in {len(by_prefix)} index files, manifest.json and masks/scotland.json written to {out_dir}")


if __name__ == "__main__":
    main()
