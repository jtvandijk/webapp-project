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

Facts are shown as small cards (a heading and a table each). The OAC, LOAC and FPC groups carry their names, from
pipeline/reference/group_names.json (--lookups points at another file of the same shape, such as a lookups.json); a
group that is not in it is shown as its code.

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


LAND_ID = "gbland"


def panel(geojson, caption, land=False):
    """One period's map as a small inline SVG figure. With land=True it is drawn over the coastline, which the page
    defines once (land_defs) and every panel refers to - not repeated in each of them."""
    layers = [f'<use href="#{LAND_ID}" fill="#dfe5ea" stroke="#c4ccd3" stroke-width="0.5"/>'] if land else []
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


def land_defs(land):
    """The coastline, defined once at the top of the page for every panel's <use> to point at ("" if there is none)."""
    return f'<svg width="0" height="0" style="position:absolute"><defs><path id="{LAND_ID}" d="{land}"/></defs></svg>' if land else ""


def maps_block(bundle, land=False):
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


YEARS_PER_ROW = 15                   # the register has about 30 years: wrapped, so the table stays inside the page


def counts_block(bundle):
    """Every year's bearers: one small table per source, the years across the top (wrapped after YEARS_PER_ROW)."""
    counts = bundle.get("counts", {})
    if not counts:
        return "<p><i>no counts</i></p>"
    tables = []
    for source, years in sorted(counts.items()):
        years = sorted(years.items())
        rows = []
        for i in range(0, len(years), YEARS_PER_ROW):
            part = years[i:i + YEARS_PER_ROW]
            label = html.escape(source.capitalize()) if i == 0 else ""
            head = "".join(f"<th>{html.escape(year)}</th>" for year, _ in part)
            cells = "".join(f'<td class="num">{n:,}</td>' for _, n in part)
            rows.append(f"<tr><th>{label}</th>{head}</tr><tr><td>bearers</td>{cells}</tr>")
        tables.append(f'<table class="counts">{"".join(rows)}</table>')
    return "".join(tables)


def _percent(share):
    if share is None:
        return ""
    if share == 0:
        return "0%"
    return f"{100 * share:.0f}%" if share >= 0.01 else "<1%"


def readable(key, value):
    """A fact's value as a short line of text a person can read - not JSON. Only used for a fact the cards below do
    not know about, and for a list of [code, share] pairs."""
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


# ---------------------------------------------------------------------------
# facts: one small card per fact - a heading and a table
# ---------------------------------------------------------------------------

FACT_TITLES = {
    "oac": "UK Output Area Classification (OAC)",
    "loac": "London Output Area Classification (LOAC)",
    "fpc": "Financial Precarity Classification (FPC)",
    "eth": "Ethnicity estimate",
    "imd": "Index of Multiple Deprivation (IMD)",
    "ahah": "Access to Healthy Assets and Hazards (AHAH)",
}
SHOW_GROUPS = 6                       # rows of a group distribution before the rest are lumped into one line
CARD_ORDER = ("oac", "loac", "fpc", "eth", "imd", "ahah", "forenames", "places")


def load_names(path):
    """The group names, in the shape of lookups.json ({scheme: {"groups": {code: {"name": ...}}}}); {} if there is no file."""
    path = Path(path) if path else None
    return json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else {}


def group_name(names, scheme, code):
    """The name of a group code, or None if it is not known (the page then shows the code alone)."""
    if scheme == "eth":
        if code == config.ETH_UNKNOWN:
            return "Unknown (too few bearers with a usable code)"
        entry = names.get("eth", {}).get(code)
        if isinstance(entry, dict):
            entry = entry.get("name")
        return entry or config.ETH_GROUPS.get(code)
    entry = names.get(scheme, {}).get("groups", {}).get(code)
    return entry.get("name") if isinstance(entry, dict) else None


def group_label(names, scheme, code):
    name = group_name(names, scheme, code)
    if name is None:
        return html.escape(str(code))
    return f'{html.escape(name)} <span class="code">{html.escape(str(code))}</span>'


def card(title, body, note=""):
    note = f'<p class="note">{note}</p>' if note else ""
    return f'<section class="card"><h4>{html.escape(title)}</h4>{note}{body}</section>'


def share_table(rows):
    """rows: [(label as html, share or None, is the most common one)] as a small table, a bar for each share."""
    lines = []
    for label, share, top in rows:
        row_class = ' class="top"' if top else ""
        bar = f'<span class="bar" style="width:{max(1, round(100 * share))}px"></span>' if share else ""
        lines.append(f'<tr{row_class}><td>{label}</td><td class="num">{html.escape(_percent(share))}</td><td>{bar}</td></tr>')
    return f'<table>{"".join(lines)}</table>'


def distribution_rows(distribution, top_code, label):
    """The biggest few groups of a {code: share} distribution, the most common one first, the rest as one line."""
    if not distribution:
        return [(label(top_code), None, True)]
    ordered = sorted(distribution.items(), key=lambda kv: (kv[0] != top_code, -kv[1], str(kv[0])))
    rows = [(label(code), share, code == top_code) for code, share in ordered[:SHOW_GROUPS]]
    rest = ordered[SHOW_GROUPS:]
    if rest:
        rows.append((f'<span class="code">{len(rest)} more groups</span>', sum(share for _, share in rest), False))
    return rows


def decile_rows(distribution, mode):
    rows = []
    for i, share in enumerate(distribution, start=1):
        end = " (worst)" if i == 1 else " (best)" if i == 10 else ""
        rows.append((f"Decile {i}{end}", share, i == mode))
    return rows


def _list_table(head, rows):
    heads = "".join(f"<th>{html.escape(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><tr>{heads}</tr>{body}</table>"


def fact_cards(facts, names):
    """Every fact of a name as a card, in a fixed order; a fact this does not know is shown as text, not dropped."""
    cards = {}
    for scheme in ("oac", "loac", "fpc"):
        fact = facts.get(scheme)
        if isinstance(fact, dict):
            cards[scheme] = card(FACT_TITLES[scheme], share_table(distribution_rows(
                fact.get("distribution"), fact.get("group"), lambda code, scheme=scheme: group_label(names, scheme, code))))
    fact = facts.get("eth")
    if isinstance(fact, dict):
        origins = fact.get("countries")
        note = ("Most common origin codes: " + html.escape(readable("countries", origins))) if origins else ""
        cards["eth"] = card(FACT_TITLES["eth"], share_table(distribution_rows(
            fact.get("distribution"), fact.get("group"), lambda code: group_label(names, "eth", code))), note)
    for scale in ("imd", "ahah"):
        fact = facts.get(scale)
        if isinstance(fact, dict) and isinstance(fact.get("distribution"), list):
            extra = ""
            if fact.get("mean") is not None:
                extra = f'Average score {fact["mean"]:.1f}' + (f' (spread {fact["sd"]:.1f})' if fact.get("sd") is not None else "")
            cards[scale] = card(FACT_TITLES[scale], share_table(decile_rows(fact["distribution"], fact.get("mode"))),
                                "Decile 1 is the worst, 10 the best." + (" " + extra if extra else ""))
    fore = facts.get("forenames")
    if isinstance(fore, dict) and fore:
        sources = [(key, title) for key, title in (("register", "Recent (register)"), ("census", "Historical (census)")) if key in fore]
        rows = [(label, *[", ".join(fore[key].get(sex, [])) for key, _ in sources]) for sex, label in (("f", "Female"), ("m", "Male"))]
        cards["forenames"] = card("Most common forenames", _list_table(["", *[title for _, title in sources]], rows))
    places = facts.get("places")
    if isinstance(places, dict):
        parts = []
        if places.get("register"):
            parts.append(card("Top areas today (register)", _list_table(["Area", "Neighbourhood"], [(r["area"], r["name"]) for r in places["register"]]),
                              "Area codes; names are added later."))
        if places.get("census"):
            parts.append(card("Top historical parishes (census)", _list_table(["County", "Parish"], [(r["area"], r["name"]) for r in places["census"]])))
        cards["places"] = "".join(parts)
    for key in sorted(set(facts) - set(CARD_ORDER)):
        cards[key] = card(key, f"<p>{html.escape(readable(key, facts[key]))}</p>")
    return "".join(cards[key] for key in (*CARD_ORDER, *sorted(set(cards) - set(CARD_ORDER))) if key in cards)


def facts_block(bundle, names=None):
    facts = bundle.get("facts", {})
    if not facts:
        return "<p><i>no facts</i></p>"
    return f'<div class="cards">{fact_cards(facts, names or {})}</div>'


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
    parser.add_argument("--lookups", default=str(config.REFERENCE / "group_names.json"),
                        help="the names of the OAC, LOAC and FPC groups (default pipeline/reference/group_names.json; a lookups.json works too)")
    parser.add_argument("--out", help="write here instead of the next numbered file in work/preview_web/")
    args = parser.parse_args()

    names = args.names if args.names is not None else sample_names(args.names_dir, args.sample, args.seed)
    if not names:
        raise SystemExit("No names given (--names with nothing after it, or --sample 0).")

    table_facts = read_facts_table(args.facts_file, names)
    if not Path(args.facts_file).exists():
        print(f"note: no facts table at {args.facts_file} (merge_release.py makes it); showing only facts inside the name files")
    names_of_groups = load_names(args.lookups)
    if not names_of_groups:
        print(f"note: no group names at {args.lookups}; groups are shown as codes")
    land = land_path()
    blocks, missing = [], []
    for key in names:
        bundle, path = find_bundle(args.names_dir, key)
        if bundle is None:
            missing.append(key)
            continue
        bundle["facts"] = {**bundle.get("facts", {}), **table_facts.get(key, {})}
        blocks.append(f"""<h2>{html.escape(key)}</h2>
{maps_block(bundle, bool(land))}
<h3>Bearers per year</h3>{counts_block(bundle)}
<h3>Facts</h3>{facts_block(bundle, names_of_groups)}""")
    for key in missing:
        print(f"note: no assembled file for {key!r}, left out")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        folder = config.WORK / "preview_web"
        out = folder / f"preview{files.next_number(folder, 'preview', '.html')}.html"

    page = f"""<!doctype html><meta charset="utf-8"><title>Release preview</title>
<style>
body{{font:14px system-ui,sans-serif;margin:20px;max-width:1150px;color:#223}}
h2{{margin:34px 0 6px;padding-top:10px;border-top:2px solid #cfd8e0}}
h3{{margin:16px 0 5px;font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:#678}}
table{{border-collapse:collapse}}
td,th{{padding:2px 10px 2px 0;border-bottom:1px solid #e6ebf0;text-align:left;vertical-align:top}}
th{{font-weight:600;color:#456;font-size:12px}}
td.num{{text-align:right;white-space:nowrap}}
table.counts{{margin:0 0 6px}} table.counts td.num,table.counts th{{padding:2px 14px 2px 0}}
.cards{{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-start}}
.card{{border:1px solid #dbe2e9;border-radius:6px;padding:8px 12px 10px;flex:0 1 340px;box-sizing:border-box;background:#fff}}
.card h4{{margin:0 0 5px;font-size:13px;color:#234}}
.card table{{width:100%}}
.note{{margin:0 0 5px;font-size:12px;color:#667}}
.code{{color:#889;font-size:11px}}
tr.top td{{font-weight:600}}
.bar{{display:inline-block;height:8px;background:#4292c6;border-radius:2px}}
</style>
<h1>Release preview</h1>
<p><small>{html.escape(out.name)}: python3 -m pipeline.preview_web {html.escape(" ".join(sys.argv[1:]))}. Each map is over a rough
coastline; the number after the year is the bearers that year. Blue shades: level 1 (outer) to level 3 (most concentrated).
In a facts table the most common group is in bold.</small></p>
{land_defs(land)}{"".join(blocks)}"""
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}: {len(blocks)} names" + (f", {len(missing)} not found" if missing else ""))


if __name__ == "__main__":
    main()
