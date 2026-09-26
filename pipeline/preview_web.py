"""A quick look at already-assembled release files (work/release/names/<xx>/<name>.json, stage 6) - not
the database, not a calculation, just "does this name's file look right": which map periods it has, a
small picture of each, and its facts as a plain table. For calibrating how a map is DRAWN, use preview.py
instead, which reads the database directly and can compare KDE settings; this tool never touches the
database and does no computation of its own, so it needs nothing beyond Python's own standard library -
it runs wherever stage 6 itself ran, HPC or otherwise.

    python3 -m pipeline.preview_web --names smith macdonald davies
    python3 -m pipeline.preview_web --sample 20                      # a random sample of assembled names

Writes work/preview_web/preview<N>.html, one file with everything inline (small hand-drawn SVGs, no map
library, no internet needed to open it) - the next number, so an earlier preview is never overwritten.
"""
import argparse
import html
import json
import math
import random
import sys
from pathlib import Path

from . import config, files

COLOURS = {1: "#6baed6", 2: "#4292c6", 3: "#2171b5"}      # the same shades preview.py uses for the same levels
PANEL_W, PANEL_H = 110, 130

# A fixed box around Great Britain, longitude/latitude - used for every panel, so panels are comparable
# to each other (the same box preview.py's own coastline drawing works from, just not reprojected here:
# this needs no shapely/pyproj, only the assembled GeoJSON, which is already longitude/latitude).
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


def panel(geojson, caption):
    """One period's map as a small inline SVG figure, or an empty box with just the caption if there is
    no geojson (a period with no map at all is never in a bundle's "maps", so this is only reached for
    a period genuinely present)."""
    layers = []
    for feature in geojson.get("features", []):
        level = feature["properties"]["level"]
        d = "".join("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in (_project(*p[:2]) for p in ring)) + "Z"
                   for ring in _rings(feature["geometry"]))
        layers.append(f'<path d="{d}" fill="{COLOURS[level]}" fill-rule="evenodd"/>')
    return (f'<figure style="margin:0"><svg viewBox="0 0 {PANEL_W} {PANEL_H}" width="{PANEL_W}">'
           f'<rect width="{PANEL_W}" height="{PANEL_H}" fill="#eef1f4"/>{"".join(layers)}</svg>'
           f'<figcaption style="font-size:11px;color:#445;text-align:center;max-width:{PANEL_W}px">{html.escape(caption)}</figcaption></figure>')


def maps_block(bundle):
    row = []
    for pid, geojson in sorted(bundle.get("maps", {}).items(), key=lambda kv: int(kv[0])):
        source = geojson.get("copyOf")
        caption = f"{pid}: shows {source}'s map" if source else pid
        row.append(panel(geojson, caption))
    if not row:
        return "<p><i>no maps at all - should not happen for a published file</i></p>"
    return f'<div style="display:flex;flex-wrap:wrap;gap:6px">{"".join(row)}</div>'


def counts_table(bundle):
    counts = bundle.get("counts", {})
    rows = [f"<tr><td>{html.escape(source)}</td><td>{html.escape(year)}</td><td style=\"text-align:right\">{n:,}</td></tr>"
           for source, years in sorted(counts.items()) for year, n in sorted(years.items())]
    if not rows:
        return "<p><i>no counts</i></p>"
    return f'<table><tr><th>source</th><th>year</th><th>bearers</th></tr>{"".join(rows)}</table>'


def facts_table(bundle):
    facts = bundle.get("facts", {})
    if not facts:
        return "<p><i>no facts</i></p>"
    rows = [f"<tr><td>{html.escape(key)}</td><td><pre style=\"margin:0;white-space:pre-wrap\">{html.escape(json.dumps(value, indent=2, ensure_ascii=False))}</pre></td></tr>"
           for key, value in sorted(facts.items())]
    return f'<table><tr><th>fact</th><th>value</th></tr>{"".join(rows)}</table>'


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
    parser.add_argument("--out", help="write here instead of the next numbered file in work/preview_web/")
    args = parser.parse_args()

    names = args.names if args.names is not None else sample_names(args.names_dir, args.sample, args.seed)
    if not names:
        raise SystemExit("No names given (--names with nothing after it, or --sample 0).")

    blocks, missing = [], []
    for key in names:
        bundle, path = find_bundle(args.names_dir, key)
        if bundle is None:
            missing.append(key)
            continue
        blocks.append(f"""<h2>{html.escape(key)}</h2>
{maps_block(bundle)}
<h3>counts</h3>{counts_table(bundle)}
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
<style>body{{font:14px system-ui,sans-serif;margin:20px}}h2{{margin:26px 0 6px}}h3{{margin:14px 0 2px;font-size:13px;color:#345}}
table{{border-collapse:collapse;margin-top:4px}}td,th{{padding:2px 10px;border-bottom:1px solid #dde;text-align:left;vertical-align:top}}</style>
<h1>Release preview</h1>
<p><small>{html.escape(out.name)}: python3 -m pipeline.preview_web {html.escape(" ".join(sys.argv[1:]))}</small></p>
{"".join(blocks)}"""
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}: {len(blocks)} names" + (f", {len(missing)} not found" if missing else ""))


if __name__ == "__main__":
    main()
