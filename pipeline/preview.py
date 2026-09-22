"""Draw a page of maps to LOOK at, straight from the database, without the website.

    python3 -m pipeline.preview                       # a few example names on the fake data
    python3 -m pipeline.preview --names smith jones --periods 1851 1901 2000 2026
    python3 -m pipeline.preview --variants 0/mass 0.5/mass 1/mass 0.5/peak     # compare settings
    python3 -m pipeline.preview --variants 0.5/mass:0.9,0.75,0.5 0.5/mass:0.75,0.5,0.25

A variant is  <weighting power>/<level mode>  or  <weighting power>/<level mode>:<levels>  (see
WEIGHT_POWER, LEVEL_MODE, LEVEL_MASS and LEVEL_PEAK in config.py), for example  0.5/mass:0.75,0.5,0.25.
With several variants every name gets one group of maps per variant, side by side.

Writes work/preview.html. It is one plain file with the maps drawn inside it, so it also opens on a
machine with no internet (the TRE). Below the maps is a table with the bandwidth, the time each map
took and the size of the output file.

Use it to judge the settings in config.py. Maps that are left out say why (too few bearers for that
source's threshold). A heavily Scottish name does not lose its 1911/1921 map - it reuses the 1901
map instead, since Scotland is missing from both censuses; the caption says so.

Only connects to the database(s) that `--periods` actually needs - a register-only `--periods`
(e.g. `1997 2000 2005 2010 2015 2020 2025 2026`) works with no working census connection at all.
"""
import argparse
import csv
import html
import json

import numpy as np
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union

from . import config, db, fake_data, kde, rules, sql
from .names import surname_key

COLOURS = {1: "#6baed6", 2: "#4292c6", 3: "#2171b5"}
PANEL = 105                                 # width of one map in pixels
TOP = 1235                                   # km, for flipping y so that north is up


def fetch_period(conn, cfg, period, surnames=None):
    """{name: (cell x, cell y, n)} and the smoothed surface of everybody for one map period.
    surnames: the standardised keys being previewed - always pass this on a real database, or the
    query scans and groups by every surname in the country just to keep the few you asked for."""
    make = sql.register_cells if period["source"] == "register" else sql.census_cells
    by_name = kde.group_by_name(db.fetch(conn, make(cfg, period["year"], surnames=surnames)))
    ix, iy, n = (np.array(c) for c in zip(*db.fetch(conn, make(cfg, period["year"], by_surname=False))))
    return by_name, kde.population_surface(ix.astype(int), iy.astype(int), n.astype(float))


def path(geometry):
    """A geometry (metres) as an SVG path in kilometres."""
    out = []
    for polygon in _parts(geometry):
        for ring in [polygon.exterior, *polygon.interiors]:
            out.append("M" + "L".join(f"{x / 1000:.1f},{TOP - y / 1000:.1f}" for x, y in ring.coords) + "Z")
    return "".join(out)


def _parts(geometry):
    return [geometry] if geometry.geom_type == "Polygon" else list(getattr(geometry, "geoms", []))


def panel(bands, land_path, caption):
    layers = "".join(f'<path d="{path(b)}" fill="{COLOURS[i]}" fill-rule="evenodd"/>'
                     for i, b in enumerate(bands or [], start=1) if not b.is_empty)
    return (f'<figure><svg viewBox="-5 0 675 1245" width="{PANEL}"><path d="{land_path}" fill="#eef1f4" '
            f'stroke="#b8c2cc" stroke-width="1.5" fill-rule="evenodd"/>{layers}</svg>'
            f"<figcaption>{caption}</figcaption></figure>")


def old_bands(file):
    """A map from the existing site (longitude/latitude GeoJSON) as three bands in metres."""
    to_bng = Transformer.from_crs(4326, 27700, always_xy=True).transform
    collection = json.loads(file.read_text())
    return [unary_union([transform(to_bng, shape(f["geometry"])) for f in collection["features"]
                         if f["properties"]["level"] == level] or [shape({"type": "Polygon", "coordinates": []})])
            for level in (1, 2, 3)]


def pick_examples():
    """Interesting names from the fake data: one of each kind."""
    truth = json.loads((config.WORK / "fake_truth.json").read_text())
    with open(config.WORK / "names.csv") as f:
        listed = {r["surname"]: r for r in csv.DictReader(f)}
    ranked = sorted((k for k in listed if k in truth), key=lambda k: -int(listed[k]["max_n"]))
    scottish = {t[0] for t in fake_data.TOWNS if t[5]}
    cornish = {"Truro", "Penzance", "Plymouth", "Exeter"}
    pick = lambda test: next((k for k in ranked if test(truth[k], listed[k])), None)
    chosen = [
        (pick(lambda t, r: t["kind"] == "widespread"), "widespread"),
        (pick(lambda t, r: t["kind"] == "regional"), "regional"),
        (pick(lambda t, r: t["kind"] == "local" and set(t["home"]) <= cornish), "Cornish"),
        (pick(lambda t, r: t["kind"] == "local" and set(t["home"]) <= scottish), "Scottish"),
        (pick(lambda t, r: t["kind"] == "local" and int(r["map_periods"]) >= 3 and int(r["max_n"]) < 250), "small"),
    ]
    return [(k, label) for k, label in chosen if k]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--names", nargs="*", help="surname keys (default: examples from the fake data)")
    parser.add_argument("--periods", nargs="*", default=["1851", "1901", "1911", "1921", "2000", "2020", "2026"])
    parser.add_argument("--variants", nargs="*", help="settings to compare, as <power>/<mode>, e.g. 0.5/mass 1/peak")
    parser.add_argument("--min-area", type=float, help="drop blobs and holes smaller than this many km2 (config MIN_AREA_KM2)")
    parser.add_argument("--out", default=str(config.WORK / "preview.html"))
    args = parser.parse_args()
    if args.min_area is not None:
        config.MIN_AREA_KM2 = args.min_area

    variants = []
    for spec in args.variants or [f"{config.WEIGHT_POWER}/{config.LEVEL_MODE}"]:
        head, _, levels = spec.partition(":")
        power, mode = head.split("/")
        variants.append((float(power), mode, tuple(float(x) for x in levels.split(",")) if levels else None))
    names = [(surname_key(n), "") for n in args.names] if args.names else pick_examples()
    names = [(key, label) for key, label in names if key]  # drop anything that standardises to nothing
    periods = [p for p in config.PERIODS if p["id"] in args.periods]
    cfg, land = config.settings(), kde.Land()
    land_path = path(unary_union(land.parts).simplify(3000))

    # the reference census for the Scotland rule has to be loaded even if it is not drawn
    needed = list(periods)
    if any(p["year"] in config.SCOTLAND_MISSING_YEARS for p in periods):
        needed += [p for p in config.PERIODS if p["year"] == config.SCOTLAND_REFERENCE_YEAR and p not in periods]
    # only connect to the database(s) actually needed - a register-only --periods needs no working
    # census connection at all
    connections = {source: db.connect(source) for source in {p["source"] for p in needed}}
    surnames = [key for key, _ in names]
    data = {p["id"]: fetch_period(connections[p["source"]], cfg, p, surnames=surnames) for p in needed}

    stats, blocks = [], []
    for key, label in names:
        by_period = {pid: data[pid][0].get(key) for pid in data}
        have = [c for c in by_period.values() if c is not None]
        if not have:
            print(f"note: {key} has no bearers in the chosen periods, left out")
            continue
        bandwidth = kde.choose_bandwidth(have)
        pop_surfaces = {pid: data[pid][1] for pid in data}
        rows = []
        for power, mode, levels in variants:
            timings = {}
            resolved = rules.build_maps(periods, by_period, bandwidth, pop_surfaces, land, power, mode, levels, timings)
            row = []
            for p in periods:
                bands, r = resolved[p["id"]]
                cells = by_period.get(p["id"])
                total = int(cells[2].sum()) if cells is not None else 0
                if r.action == "omit":
                    row.append(panel(None, land_path, f"{p['id']}: none ({r.reason})"))
                    continue
                caption = (f"{p['id']}: {total:,} bearers (using {r.reference}'s map, {r.reason})"
                          if r.action == "substitute" else f"{p['id']}: {total:,} bearers")
                ms = timings.get(r.reference if r.action == "substitute" else p["id"], 0.0) * 1000
                collection = kde.geojson(bands) if bands else None
                size = len(json.dumps(collection, separators=(",", ":"))) if collection else 0
                areas = sum(len(_parts(b)) for b in bands or [])
                vertices = sum(len(rg.coords) for b in bands or [] for g in _parts(b) for rg in [g.exterior, *g.interiors])
                variant_tag = f"{power:g}/{mode}" + (":" + ",".join(f"{x:g}" for x in levels) if levels else "")
                stats.append((key, variant_tag, p["id"], total, bandwidth / 1000, ms, r.action, areas, vertices, size / 1024))
                row.append(panel(bands, land_path, caption))
            shown = ",".join(f"{x:g}" for x in levels or (config.LEVEL_MASS if mode == "mass" else config.LEVEL_PEAK))
            tag = f"<div class='variant'>power {power:g}, {mode} {shown}</div>" if len(variants) > 1 else ""
            rows.append(f"<div>{tag}<div class='row'>{''.join(row)}</div></div>")
        blocks.append(f"<h2>{html.escape(key)} <small>{label}</small></h2><div class='groups'>{''.join(rows)}</div>")

    reference = ""
    old = [(config.ROOT / "gbnames/static/kde/sm/smith" / f"smith_{y}.json", f"Smith {y}") for y in (1901, 2016)] \
        + [(config.ROOT / "gbnames/static/kde/ju/juszczyk/juszczyk_2016.json", "Juszczyk 2016")]
    panels = [panel(old_bands(f), land_path, label) for f, label in old if f.exists()]
    if panels:
        reference = ("<h2>For comparison: maps on the existing website <small>real data, old method</small></h2>"
                     f"<div class='row'>{''.join(panels)}</div>")

    table = "".join(f"<tr><td>{k}</td><td>{v}</td><td>{p}</td><td>{n:,}</td><td>{h:.0f}</td><td>{a}</td><td>{ms:.0f}</td>"
                    f"<td>{ar}</td><td>{pts:,}</td><td>{kb:.0f}</td></tr>" for k, v, p, n, h, ms, a, ar, pts, kb in stats)
    page = f"""<!doctype html><meta charset="utf-8"><title>Map preview</title>
<style>body{{font:14px system-ui,sans-serif;margin:20px}}h2{{margin:26px 0 2px}}small{{color:#667;font-weight:400}}
.row{{display:flex;flex-wrap:wrap;gap:4px}}.variant{{margin:8px 0 0;color:#345;font-weight:600;font-size:13px}}
figure{{margin:0}}figcaption{{font-size:11px;color:#445;text-align:center;max-width:105px}}.groups{{display:flex;flex-wrap:wrap;gap:22px}}
table{{border-collapse:collapse;margin-top:8px}}td,th{{padding:2px 10px;border-bottom:1px solid #dde;text-align:right}}
td:first-child,th:first-child{{text-align:left}}</style>
<h1>Map preview</h1>
<p>Weighting power: <b>{config.WEIGHT_POWER}</b> (0 = plain density, 1 = fully relative). Levels by
<b>{config.LEVEL_MODE}</b>: {config.LEVEL_MASS if config.LEVEL_MODE == 'mass' else config.LEVEL_PEAK}.
Bandwidth {config.BANDWIDTH_MIN_M // 1000} to {config.BANDWIDTH_MAX_M // 1000} km, growing with the number of
bearers. Database profile: <b>{config.PROFILE}</b>. Blue shades: level 1 (outer) to level 3 (highest).
Variants shown: {', '.join(f'{p:g}/{m}' for p, m, _ in variants)}.</p>
{''.join(blocks)}{reference}
<h2>Time and size</h2><table><tr><th>name</th><th>variant</th><th>period</th><th>bearers</th><th>bandwidth km</th>
<th>action</th><th>ms</th><th>separate areas</th><th>points</th><th>KB as GeoJSON</th></tr>{table}</table>"""
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(page)
    if stats:
        built = [s[5] for s in stats if s[6] == "build"]
        timing = f"median {np.median(built):.0f} ms, " if built else ""
        print(f"wrote {args.out}: {len(stats)} maps ({len(built)} built, {len(stats) - len(built)} reused), "
              f"{timing}largest {max(s[9] for s in stats):.0f} KB")


if __name__ == "__main__":
    main()
