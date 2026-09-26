"""A quick look at already-assembled release files (work/release/names/<xx>/<name>.json, stage 6) - not
the database, not a calculation, just "does this name's file look right": which map periods it has, a
picture of each over the coastline, its counts and its facts. For calibrating how a map is DRAWN, use
preview.py instead, which reads the database directly and can compare KDE settings; this tool never touches
the database and does no computation of its own, so it needs nothing beyond Python's own standard library -
it runs wherever stage 6 itself ran, HPC or otherwise.

    python3 -m pipeline.preview_web --names smith macdonald davies
    python3 -m pipeline.preview_web --sample 20                      # a random sample of assembled names

A name's file holds its counts and maps; its facts are in the one facts table, work/release/facts.csv (made by
merge_release.py), read here as a stream for just the names asked for. Facts inside the name file itself
(s6_assemble.py --facts-in-names) are shown too.

Writes work/preview_web/preview<N>.html, one file with everything inline (small hand-drawn SVGs, no map
library, no internet needed to open it) - the next number, so an earlier preview is never overwritten. The
coastline under the maps is pipeline/reference/gb_outline_lonlat.geojson (rough, a few KB; made by
pipeline/reference/make_preview_outline.py).
"""
import argparse
import csv
import html
import json
import math
import random
import sys
from pathlib import Path

from . import config, files

COLOURS = {1: "#6baed6", 2: "#4292c6", 3: "#2171b5"}      # the same shades preview.py uses for the same levels
PANEL_W, PANEL_H = 120, 210

# A fixed box around Great Britain, longitude/latitude - used for every panel, so panels are comparable
# to each other. This needs no shapely/pyproj, only the assembled GeoJSON, which is already longitude/latitude.
MAP_BOX = {"lon": (-8.6, 1.9), "lat": (49.8, 60.9)}


def _project(lon, lat):
    """A longitude/latitude point as (x, y) pixels inside a PANEL_W x PANEL_H box, north up. Longitude is
    scaled by cos(mean latitude) so the shape is not visibly squashed east-west - this needs no proper
    map projection, just enough correction that Great Britain looks like Great Britain."""
    lon0, lon1 = MAP_BOX["lon"]
    lat0, lat1 = MAP_BOX["lat"]
    cos_lat = math.cos(math.radians((lat0 + lat1) / 2))
    width, height = (lon1 - lon0) * cos_lat, (lat1 - lat0)
    scale = min(PANEL_W / width, PANEL_H / height)
    x = (lon - lon0) * cos_lat * scale
    y = (lat1 - lat) * scale                    # flipped: latitude grows north, SVG y grows down
    return x, y


def _rings(geometry):
    """Every ring (a list of [lon, lat] points) of a Polygon or MultiPolygon geometry, exterior and holes
    alike - fill-rule="evenodd" in the SVG below tells holes from exteriors apart, the same trick
    preview.py's own path() uses, so this does not need to know which ring is which."""
    if geometry["type"] == "Polygon":
        yield from geometry["coordinates"]
    else:
        for polygon in geometry["coordinates"]:
            yield from polygon


def _path(geometry):
    return "".join("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in (_project(*p[:2]) for p in ring)) + "Z" for ring in _rings(geometry))


def land_path(path=None):
    """The coastline as one SVG path (the same for every panel), or "" if the file is not there."""
    path = Path(path) if path else config.REFERENCE / "gb_outline_lonlat.geojson"
    if not path.exists():
        return ""
    doc = json.loads(path.read_text())
    return "".join(_path(f["geometry"]) for f in doc["features"])


def panel(geojson, caption, land=""):
    """One period's map as a small inline SVG figure over the coastline."""
    layers = [f'<path d="{land}" fill="#dfe5ea" stroke="#c4ccd3" stroke-width="0.5"/>'] if land else []
    for feature in geojson.get("features", []):
        level = feature["properties"]["level"]
        layers.append(f'<path d="{_path(feature["geometry"])}" fill="{COLOURS[level]}" fill-rule="evenodd"/>')
    return (f'<figure style="margin:0"><svg viewBox="0 0 {PANEL_W} {PANEL_H}" width="{PANEL_W}">'
            f'<rect width="{PANEL_W}" height="{PANEL_H}" fill="#f3f5f7"/>{"".join(layers)}</svg>'
            f'<figcaption style="font-size:11px;color:#445;text-align:center;max-width:{PANEL_W}px">{html.escape(caption)}</figcaption></figure>')


def bearers_in(bundle, period_id):
    """The bearers of this period's year, from the counts (which hold every year), or None."""
    for years in bundle.get("counts", {}).values():
        if period_id in years:
            return years[period_id]
    return None


def maps_block(bundle, land=""):
    row = []
    for pid, geojson in sorted(bundle.get("maps", {}).items(), key=lambda kv: int(kv[0])):
        n = bearers_in(bundle, pid)
        source = geojson.get("copyOf")
        caption = f"{pid}: {n:,}" if n is not None else pid
        if source:
            caption += f" - shows {source}'s map"
        row.append(panel(geojson, caption, land))
    if not row:
        return "<p><i>no maps at all - should not happen for a published file</i></p>"
    return f'<div style="display:flex;flex-wrap:wrap;gap:8px">{"".join(row)}</div>'


def counts_block(bundle):
    """Every year's bearers, one line per source: 1851: 68 - 1861: 81 - ..."""
    counts = bundle.get("counts", {})
    if not counts:
        return "<p><i>no counts</i></p>"
    lines = [f"<p style=\"margin:2px 0\"><b>{html.escape(source)}</b> &nbsp; " +
             " &middot; ".join(f"{html.escape(year)}: {n:,}" for year, n in sorted(years.items())) + "</p>"
             for source, years in sorted(counts.items())]
    return "".join(lines)


def _percent(share):
    return f"{100 * share:.0f}%" if share >= 0.01 else "<1%"


def readable(key, value):
    """A fact's value as a short line of text a person can read - not JSON. Lists of names run on, a share
    is a percentage, a distribution is its biggest shares first."""
    if isinstance(value, dict):
        if key == "distribution":                                             # {group: share}: the biggest shares first
            return ", ".join(f"{k} {_percent(v)}" for k, v in sorted(value.items(), key=lambda kv: -kv[1]))
        return "; ".join(f"{k}: {readable(k, v)}" for k, v in value.items())
    if key == "distribution" and isinstance(value, list):                    # a decile distribution: ten shares in order
        return ", ".join(f"{i}: {_percent(v)}" for i, v in enumerate(value, start=1))
    if isinstance(value, list):
        if value and isinstance(value[0], list):                              # [[code, share], ...]
            return ", ".join(f"{code} {_percent(share)}" for code, share in value)
        if value and isinstance(value[0], dict):                              # places: [{"area": .., "name": ..}, ...]
            return "; ".join(" / ".join(str(v) for v in d.values()) for d in value)
        return ", ".join(str(v) for v in value)
    return str(value)


def facts_table(bundle):
    facts = bundle.get("facts", {})
    if not facts:
        return "<p><i>no facts</i></p>"
    rows = []
    for fact, value in sorted(facts.items()):
        # a fact with parts (forenames and places: register and census) is one row per part
        parts = list(value.items()) if fact in ("forenames", "places") else [("", value)]
        for part, inner in parts:
            rows.append(f"<tr><td>{html.escape(f'{fact} {part}'.strip())}</td><td>{html.escape(readable(fact if not part else '', inner))}</td></tr>")
    return f'<table><tr><th>fact</th><th>value</th></tr>{"".join(rows)}</table>'


def read_facts_table(path, wanted):
    """{name: {fact: object}} for the names in `wanted`, read from the facts table (name, fact, data) as a stream -
    the table has one row per name and fact for every published name, so it is never loaded whole."""
    found = {}
    if not Path(path).exists():
        return found
    wanted = set(wanted)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for name, fact, data in reader:
            if name in wanted:
                found.setdefault(name, {})[fact] = json.loads(data)
    return found


def find_bundle(names_dir, key):
    path = Path(names_dir) / key[:2] / f"{key}.json"
    if not path.exists():
        return None, path
    return json.loads(path.read_text()), path


def sample_names(names_dir, n, seed=None):
    """n names picked at random from whatever is already assembled - for spot-checking beyond a
    hand-picked list. Reads only the file names (from the folder listing), not their contents."""
    paths = sorted(Path(names_dir).glob("*/*.json"))
    if not paths:
        raise SystemExit(f"No assembled files in {names_dir} - run s6_assemble.py (and merge_release.py) first.")
    random.Random(seed).shuffle(paths)
    return [p.stem for p in paths[:n]]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--names", nargs="*", help="surname keys to look at (lower case, letters only)")
    which.add_argument("--sample", type=int, help="this many names, picked at random from what is already assembled")
    parser.add_argument("--seed", type=int, help="--sample is otherwise different every run; pass this to repeat the same sample")
    parser.add_argument("--names-dir", default=str(config.WORK / "release" / "names"))
    parser.add_argument("--facts-file", default=str(config.WORK / "release" / "facts.csv"), help="the facts table (default work/release/facts.csv)")
    parser.add_argument("--out", help="write here instead of the next numbered file in work/preview_web/")
    args = parser.parse_args()

    names = args.names if args.names is not None else sample_names(args.names_dir, args.sample, args.seed)
    if not names:
        raise SystemExit("No names given (--names with nothing after it, or --sample 0).")

    table_facts = read_facts_table(args.facts_file, names)
    if not Path(args.facts_file).exists():
        print(f"note: no facts table at {args.facts_file} (merge_release.py makes it); showing only facts inside the name files")
    land = land_path()
    blocks, missing = [], []
    for key in names:
        bundle, path = find_bundle(args.names_dir, key)
        if bundle is None:
            missing.append(key)
            continue
        bundle["facts"] = {**bundle.get("facts", {}), **table_facts.get(key, {})}
        blocks.append(f"""<h2>{html.escape(key)}</h2>
{maps_block(bundle, land)}
<h3>bearers per year</h3>{counts_block(bundle)}
<h3>facts</h3>{facts_table(bundle)}""")
    for key in missing:
        print(f"note: no assembled file for {key!r}, left out")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        folder = config.WORK / "preview_web"
        out = folder / f"preview{files.next_number(folder, 'preview', '.html')}.html"

    page = f"""<!doctype html><meta charset="utf-8"><title>Release preview</title>
<style>body{{font:14px system-ui,sans-serif;margin:20px;max-width:1100px}}h2{{margin:30px 0 6px}}h3{{margin:14px 0 2px;font-size:13px;color:#345}}
table{{border-collapse:collapse;margin-top:4px}}td,th{{padding:3px 12px 3px 0;border-bottom:1px solid #dde;text-align:left;vertical-align:top}}
td:first-child{{white-space:nowrap;color:#345}}</style>
<h1>Release preview</h1>
<p><small>{html.escape(out.name)}: python3 -m pipeline.preview_web {html.escape(" ".join(sys.argv[1:]))}. Each map is over a rough
coastline; the number after the year is the bearers that year. Blue shades: level 1 (outer) to level 3 (most concentrated).</small></p>
{"".join(blocks)}"""
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}: {len(blocks)} names" + (f", {len(missing)} not found" if missing else ""))


if __name__ == "__main__":
    main()
