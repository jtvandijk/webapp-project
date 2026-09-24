"""Draw a page of maps to LOOK at, straight from the database, without the website.

    python3 -m pipeline.preview                       # a few example names on the fake data
    python3 -m pipeline.preview --names smith jones --periods 1851 1901 2000 2026
    python3 -m pipeline.preview --names smith jones --sources register   # all the register map years, no census database needed
    python3 -m pipeline.preview --variants 0/mass 0.5/mass 1/mass 0.5/peak     # compare settings
    python3 -m pipeline.preview --variants 0.5/mass:0.9,0.75,0.5 0.5/mass:0.75,0.5,0.25

By default (confirmed on real data 2026-09-23) every name gets its own LEVEL_MASS from
kde.size_level_mass(), not one fixed setting - pass --variants to compare specific settings by hand
instead (this turns --auto-level-mass off). A variant is  <weighting power>/<level mode>  or
<weighting power>/<level mode>:<levels>  (see WEIGHT_POWER, LEVEL_MODE, LEVEL_MASS and LEVEL_PEAK in
config.py), for example  0.5/mass:0.75,0.5,0.25. With several variants every name gets one group of
maps per variant, side by side.

Writes work/preview_maps/preview<N>.html, one more than the highest N already there, so an earlier
preview is never overwritten and you can compare runs (the page says at the top which command made it;
--out writes to a file of your choice instead). It is one plain file with the maps drawn inside it, so it
also opens on a machine with no internet (the TRE). Below the maps is a table with the bandwidth, the time each map
took and the size of the output file.

Use it to judge the settings in config.py. Maps that are left out say why (too few bearers for that
source's threshold). A heavily Scottish name does not lose its 1911/1921 map - it reuses the 1901
map instead, since Scotland is missing from both censuses; the caption says so.

Only connects to the database(s) that `--periods` actually needs - a register-only `--periods`
(e.g. `1997 2000 2005 2010 2015 2020 2025 2026`) works with no working census connection at all.

What is fetched from the database is cached in work/cache/ (per period: the names asked for so
far, and the population surface), since comparing KDE settings (bandwidth, weighting, levels, blob
share) re-draws the same data without re-fetching it. Adding a name to `--names` fetches only that
name - names already cached from an earlier run are not fetched again. Add `--refresh-cache` once
the underlying data has actually changed (a new register or census load), since nothing here
notices that on its own.
"""
import argparse
import csv
import hashlib
import html
import json
import pickle
import sys
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union

from . import config, db, fake_data, files, kde, rules, sql
from .names import surname_key

COLOURS = {1: "#6baed6", 2: "#4292c6", 3: "#2171b5"}
PANEL = 105                                 # width of one map in pixels
TOP = 1235                                   # km, for flipping y so that north is up


CACHE_DIR = config.WORK / "cache"


def _cache_stem(period):
    return f"{config.PROFILE}-{period['source']}-{period['year']}"


def _load(path):
    if path.exists():
        with path.open("rb") as f:
            return pickle.load(f)
    return None


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(value, f)


def fetch_period(connect, cfg, period, surnames=None, use_cache=True, refresh_cache=False, population_bandwidth=None):
    """{name: (cell x, cell y, n)} and the smoothed surface of everybody for one map period.
    surnames: the standardised keys being previewed - always pass this on a real database, or the
    query scans and groups by every surname in the country just to keep the few you asked for.

    connect: a zero-argument function that opens the database connection, called only on a cache
    miss - so that once every needed period is cached, comparing KDE settings needs no database
    connection at all.

    Cached under work/cache/, as two separate files per period so that adding a name to --names
    only fetches that name, not everything again: the "everybody" population surface (does not
    depend on which names are asked for, so it is fetched once ever, however many names later runs
    add - population_bandwidth is part of its cache filename, so trying a different one does not
    silently reuse a surface smoothed with the old one) and a per-name store that only grows (a name
    already in it from an earlier run is not re-fetched; a new one is fetched alone and added). Pass
    --refresh-cache once the underlying data has actually changed (a new register or census load),
    since nothing here notices that on its own - it starts both files over from empty."""
    stem = _cache_stem(period)
    pop_bw = config.POPULATION_BANDWIDTH_M if population_bandwidth is None else population_bandwidth
    names_path = CACHE_DIR / f"{stem}-names.pkl" if use_cache else None
    pop_path = CACHE_DIR / f"{stem}-population-{int(pop_bw)}.pkl" if use_cache else None
    make = sql.register_cells if period["source"] == "register" else sql.census_cells

    by_name = ({} if refresh_cache else _load(names_path)) if names_path else {}
    by_name = by_name if by_name is not None else {}
    missing = sorted(set(surnames or []) - by_name.keys())
    if missing or not names_path:
        by_name.update(kde.group_by_name(db.fetch(connect(), make(cfg, period["year"], surnames=missing or surnames))))
        if names_path:
            _save(names_path, by_name)

    population = None if refresh_cache else (_load(pop_path) if pop_path else None)
    if population is None:
        ix, iy, n = (np.array(c) for c in zip(*db.fetch(connect(), make(cfg, period["year"], by_surname=False))))
        population = kde.population_surface(ix.astype(int), iy.astype(int), n.astype(float), pop_bw)
        if pop_path:
            _save(pop_path, population)

    return by_name, population


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
    to_bng = Transformer.from_crs(4326, 27700, always_xy=True, allow_ballpark=True).transform
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
    parser.add_argument("--periods", nargs="*", help="map periods (default: 1851 1901 1911 1921 2000 2020 2026, or all the map "
                        "years of --sources)")
    parser.add_argument("--sources", nargs="*", choices=["register", "census"],
                        help="use every map year of these sources as the periods, e.g. --sources register for all eight register "
                             "years (only the databases the periods need are opened)")
    parser.add_argument("--variants", nargs="*", help="settings to compare, as <power>/<mode>, e.g. 0.5/mass 1/peak")
    parser.add_argument("--min-area", type=float, help="drop blobs and holes smaller than this many km2 (config MIN_AREA_KM2)")
    parser.add_argument("--smooth", type=float, help="metres to fill gaps/notches narrower than 2x this (config SMOOTH_M, now 10000)")
    parser.add_argument("--min-blob-share", type=float, help="drop a separate blob holding less than this share of the name's total (config MIN_BLOB_SHARE)")
    parser.add_argument("--min-blob-bearers", type=float, help="also drop a separate blob with fewer than this many actual bearers, whatever share "
                                                                "of the total that is (config MIN_BLOB_BEARERS) - for names too small for "
                                                                "--min-blob-share to do anything")
    parser.add_argument("--weight-ceiling", type=float, help="cap population used in weighting at this many people/km2 (config WEIGHT_CEILING) "
                                                              "- stops one very dense pixel (e.g. a city centre) creating a dip there")
    parser.add_argument("--population-bandwidth", type=float, help="smoothing of the population surface in metres (config POPULATION_BANDWIDTH_M, "
                                                                    "now 15000)")
    parser.add_argument("--auto-level-mass", action="store_true",
                        help="per-name LEVEL_MASS from kde.size_level_mass() - the default whenever --variants is not given (pass --variants to "
                             "compare specific settings manually instead)")
    parser.add_argument("--refresh-cache", action="store_true", help="ignore work/cache/ and re-query, e.g. after a new register or census load")
    parser.add_argument("--out", help="write here instead of the next numbered file in work/preview_maps/")
    args = parser.parse_args()
    if args.periods is None:
        args.periods = ([str(year) for source in args.sources for year in config.MAP_YEARS[source]] if args.sources
                        else ["1851", "1901", "1911", "1921", "2000", "2020", "2026"])
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        folder = config.WORK / "preview_maps"
        out = folder / f"preview{files.next_number(folder, 'preview', '.html')}.html"
    if args.variants is None and not args.auto_level_mass:
        args.auto_level_mass = True    # the confirmed way to run, now the default - pass --variants for manual comparisons instead
    if args.min_area is not None:
        config.MIN_AREA_KM2 = args.min_area
    if args.min_blob_share is not None:
        config.MIN_BLOB_SHARE = args.min_blob_share
    if args.min_blob_bearers is not None:
        config.MIN_BLOB_BEARERS = args.min_blob_bearers
    if args.smooth is not None:
        config.SMOOTH_M = args.smooth
    if args.weight_ceiling is not None:
        config.WEIGHT_CEILING = args.weight_ceiling

    variants = []
    for spec in args.variants or [f"{config.WEIGHT_POWER}/{config.LEVEL_MODE}"]:
        head, _, levels = spec.partition(":")
        power, mode = head.split("/")
        variants.append((float(power), mode, tuple(float(x) for x in levels.split(",")) if levels else None))
    # what each variant actually resolves to (falling back to config.py only where the variant did
    # not spell out its own levels) - shown in the page header instead of config.py's raw settings,
    # which are not what was drawn as soon as --variants overrides anything
    variant_labels = [f"power {p:g}, {m} " + ",".join(f"{x:g}" for x in (lv or (config.LEVEL_MASS if m == "mass" else config.LEVEL_PEAK)))
                      for p, m, lv in variants]
    names = [(surname_key(n), "") for n in args.names] if args.names else pick_examples()
    names = [(key, label) for key, label in names if key]  # drop anything that standardises to nothing
    periods = [p for p in config.PERIODS if p["id"] in args.periods]
    cfg, land = config.settings(), kde.Land()
    land_path = path(unary_union(land.parts).simplify(3000))

    # the reference census for the Scotland rule has to be loaded even if it is not drawn
    needed = list(periods)
    if any(p["year"] in config.SCOTLAND_MISSING_YEARS for p in periods):
        needed += [p for p in config.PERIODS if p["year"] == config.SCOTLAND_REFERENCE_YEAR and p not in periods]
    # only connect to the database(s) actually needed, and only on a cache miss - a register-only
    # --periods needs no working census connection at all, and once every period below is cached,
    # comparing KDE settings needs no database connection at all
    connections = {}

    def connect_once(source):
        if source not in connections:
            connections[source] = db.connect(source)
        return connections[source]

    surnames = [key for key, _ in names]
    data = {p["id"]: fetch_period(lambda p=p: connect_once(p["source"]), cfg, p, surnames=surnames,
                                   refresh_cache=args.refresh_cache, population_bandwidth=args.population_bandwidth)
            for p in needed}

    stats, blocks = [], []
    for key, label in names:
        by_period = {pid: data[pid][0].get(key) for pid in data}
        have = [c for c in by_period.values() if c is not None]
        if not have:
            print(f"note: {key} has no bearers in the chosen periods, left out")
            continue
        bandwidth = kde.choose_bandwidth(have)
        pop_surfaces = {pid: data[pid][1] for pid in data}
        if args.auto_level_mass:
            # --auto-level-mass replaces --variants entirely (one setting per name, not several to
            # compare) - the biggest year decides n and second_share, the same year choose_bandwidth()
            # itself uses
            biggest_pid, biggest_cells = max(((pid, c) for pid, c in by_period.items() if c is not None),
                                             key=lambda pc: pc[1][2].sum())
            second = kde.second_blob_share(kde.to_grid(*biggest_cells), bandwidth, pop_surfaces[biggest_pid],
                                           land, config.WEIGHT_POWER)
            biggest_n = int(biggest_cells[2].sum())
            auto_levels = kde.size_level_mass(biggest_n, second)
            name_variants = [(config.WEIGHT_POWER, "mass", auto_levels)]
            name_labels = [f"auto ({biggest_n:,} bearers, second blob {second:.2f}): power {config.WEIGHT_POWER:g}, mass "
                          + ",".join(f"{x:g}" for x in auto_levels)]
        else:
            name_variants, name_labels = variants, variant_labels
        rows = []
        for (power, mode, levels), variant_label in zip(name_variants, name_labels):
            timings = {}
            resolved = rules.build_maps(periods, by_period, bandwidth, pop_surfaces, land, power=power, mode=mode,
                                        levels=levels, timings=timings)
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
                ref_id = r.reference if r.action == "substitute" else p["id"]
                ref_cells = by_period.get(ref_id)
                ref_grid = kde.to_grid(*ref_cells) if ref_cells is not None else None
                conc = kde.concentration(ref_grid, bandwidth, pop_surfaces[ref_id], land, power) \
                       if ref_grid is not None else None
                second = kde.second_blob_share(ref_grid, bandwidth, pop_surfaces[ref_id], land, power) \
                         if ref_grid is not None else None
                variant_tag = f"{power:g}/{mode}" + (":" + ",".join(f"{x:g}" for x in levels) if levels else "")
                stats.append((key, variant_tag, p["id"], total, bandwidth / 1000, ms, r.action, areas, vertices,
                              size / 1024, conc, second))
                row.append(panel(bands, land_path, caption))
            tag = f"<div class='variant'>{variant_label}</div>" if len(name_variants) > 1 or args.auto_level_mass else ""
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
                    f"<td>{ar}</td><td>{pts:,}</td><td>{kb:.0f}</td><td>{'' if c is None else f'{c:.2f}'}</td>"
                    f"<td>{'' if s is None else f'{s:.2f}'}</td></tr>"
                    for k, v, p, n, h, ms, a, ar, pts, kb, c, s in stats)
    page = f"""<!doctype html><meta charset="utf-8"><title>Map preview</title>
<style>body{{font:14px system-ui,sans-serif;margin:20px}}h2{{margin:26px 0 2px}}small{{color:#667;font-weight:400}}
.row{{display:flex;flex-wrap:wrap;gap:4px}}.variant{{margin:8px 0 0;color:#345;font-weight:600;font-size:13px}}
figure{{margin:0}}figcaption{{font-size:11px;color:#445;text-align:center;max-width:105px}}.groups{{display:flex;flex-wrap:wrap;gap:22px}}
table{{border-collapse:collapse;margin-top:8px}}td,th{{padding:2px 10px;border-bottom:1px solid #dde;text-align:right}}
td:first-child,th:first-child{{text-align:left}}</style>
<h1>Map preview</h1>
<p><small>{html.escape(out.name)}: python3 -m pipeline.preview {html.escape(" ".join(sys.argv[1:]))}</small></p>
<p>{"<b>--auto-level-mass</b>: LEVEL_MASS from kde.size_level_mass() per name (exploratory, see its "
   "docstring) - each name's own resolved setting is labelled below its maps." if args.auto_level_mass else
   "Variant(s) run (weighting power, level mode, levels - see WEIGHT_POWER, LEVEL_MODE, LEVEL_MASS, "
   f"LEVEL_PEAK in config.py): <b>{'</b>; <b>'.join(variant_labels)}</b>."}
Bandwidth {config.BANDWIDTH_MIN_M // 1000} to {config.BANDWIDTH_MAX_M // 1000} km, growing with the number of
bearers. Database profile: <b>{config.PROFILE}</b>. Blue shades: level 1 (outer) to level 3 (highest).</p>
{''.join(blocks)}{reference}
<h2>Time and size</h2><p>Both exploratory, not used by make_map() - candidate measures of a name's own
shape, to see what predicts how tight LEVEL_MASS should be for it, instead of (or alongside) its
bearer count. <b>Concentration</b>: the "mass" cut-off value (0-1, share of the surface's own peak)
at which half this name's density is reached - low means spread thin across everywhere it has any
presence, high means piled into a few cells. <b>Second blob</b>: the size of a second separate
concentration relative to the biggest one (0 = only one, up to nearly 1 = two of about equal size) -
concentration alone cannot tell "one tall peak" from "two comparably tall peaks" apart, since both
score high; this can.</p>
<table><tr><th>name</th><th>variant</th><th>period</th><th>bearers</th><th>bandwidth km</th>
<th>action</th><th>ms</th><th>separate areas</th><th>points</th><th>KB as GeoJSON</th><th>concentration</th>
<th>second blob</th></tr>{table}</table>"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    if stats:
        built = [s[5] for s in stats if s[6] == "build"]
        timing = f"median {np.median(built):.0f} ms, " if built else ""
        print(f"wrote {out}: {len(stats)} maps ({len(built)} built, {len(stats) - len(built)} reused), "
              f"{timing}largest {max(s[9] for s in stats):.0f} KB")


if __name__ == "__main__":
    main()
