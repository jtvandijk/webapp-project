"""A sanity check of the parish ids: what is in the two parish tables, what ids the census people carry, and how the
two fit together. It changes nothing and writes nothing; run it once the parish tables are in the database, and again
after any reload of them.

    python3 -m pipeline.check_parishes                            # every census year in run.settings
    python3 -m pipeline.check_parishes --census-years 1921        # only some years
    python3 -m pipeline.check_parishes --lookup conpar_lookup.csv # also compare with the old lookup file

It reads each parish table (about 13,000 rows) and makes one pass over each year's attributes table, counting the
people per parish id; everything else is worked out in Python. Lines that start with LOOK are the ones to read.
A problem with a parish table is a LOOK only if census people are in the parishes it touches, and it says how many:
a stray shape that nobody carries is only noted.

The people are joined to a parish the way every stage joins them: the parish id in the attributes table (gid; for 1921
conparid1901) against conparid in the parish table (config.CENSUS_PARISH_COLUMN, CENSUS_PARISH_BOUNDARIES).
"""
import argparse
import csv
import math
from collections import Counter

from . import config, db, sql
from .names import has_letters, name_key, place_label

LOST_SHARE = 0.05          # people whose parish id is not in the parish table: more than this is worth a look
OTHER_SHARE = 0.05         # people whose id is found in the OTHER boundaries' table: the wrong table may be in use
CAPS_LOOK = 3              # how many examples of a thing to print
NAME_SHARE = 0.005         # parishes without a name or a county, or the neighbours of fractional ids: worth a LOOK above this share of a year's people


def _num(value):
    """A parish id as a number: a whole id as an int, a fractional one (like 200136.3) as a float, None if missing."""
    if value is None:
        return None
    number = float(value)
    return int(number) if number == int(number) else number


def _float(value):
    return None if value is None else float(value)


def _fmt(value):
    return "-" if value is None else f"{value:,}" if isinstance(value, int) else str(value)


def _pct(part, whole):
    return f"{part / whole:.1%}" if whole else "-"


def _examples(items, limit=CAPS_LOOK):
    items = list(items)
    return ", ".join(str(i) for i in items[:limit]) + (f" and {len(items) - limit:,} more" if len(items) > limit else "")


def _lost_examples(year_summary, limit=5):
    """The ids that are most often missing from the parish table, with their people."""
    return _examples([f"{i} ({year_summary['lost_by_id'][i]:,})" for i in year_summary["lost_ids"]], limit)


def _integer_type(name):
    return any(word in str(name or "").lower() for word in ("int", "serial"))


def _text_type(name):
    return any(word in str(name or "").lower() for word in ("char", "text"))


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------

def gather(conn, cfg, years):
    """Everything the report needs, read from the database: per parish table its rows and the type of its id column,
    per census year the number of people carrying each parish id and the type of that column."""
    tables, per_year = {}, {}
    for year in years:
        _, att, parish, columns = sql.census_tables(cfg, year)
        boundaries = config.CENSUS_PARISH_BOUNDARIES[year]
        if boundaries not in tables:
            types = dict(db.fetch(conn, sql.column_types(cfg, parish)))
            tables[boundaries] = {
                "name": parish, "id_type": types.get(columns["parish_id"]),
                "rows": [(_num(i), _float(x), _float(y), name, county)
                         for i, x, y, name, county in db.fetch(conn, sql.parish_table_rows(cfg, year))]}
        counts = Counter()
        for parish_id, people in db.fetch(conn, sql.census_parish_id_counts(cfg, year)):
            counts[_num(parish_id)] += int(people)
        types = dict(db.fetch(conn, sql.column_types(cfg, att)))
        per_year[year] = {"boundaries": boundaries, "att": att, "column": columns["parish"],
                          "id_type": types.get(columns["parish"]), "counts": counts}
    return {"tables": tables, "years": per_year}


def read_lookup(path):
    """[(id, county, parish)] from the old lookup file (columns CONPARID, RC1851, Parish(s))."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = {name.strip().lower(): name for name in reader.fieldnames or []}
        find = lambda *starts: next((fields[k] for k in fields if k.startswith(starts)), None)
        id_col, parish_col, county_col = find("conparid"), find("parish"), find("rc", "county", "regcnty")
        if not (id_col and parish_col):
            raise SystemExit(f"{path}: expected the columns CONPARID and Parish(s); found {', '.join(reader.fieldnames or [])}")
        return [(_num(row[id_col]), row.get(county_col, ""), row[parish_col]) for row in reader if row[id_col].strip()]


# ---------------------------------------------------------------------------
# what a parish table holds, and how a year's people sit in it
# ---------------------------------------------------------------------------

def summarise_table(rows):
    """Facts about one parish table. rows: (id, x, y, parish name, county)."""
    grid = config.GRID
    on_grid = lambda x, y: (grid["x0"] <= x < grid["x0"] + grid["nx"] * grid["cell"]
                            and grid["y0"] <= y < grid["y0"] + grid["ny"] * grid["cell"])
    places = [r for r in rows if r[0] != 0]                  # parish id 0 is "not in a parish", not a place
    seen = Counter(r[0] for r in places if r[0] is not None)
    located = [(x, y) for _, x, y, _, _ in places if x is not None and y is not None]
    no_centroid_ids = [r[0] for r in places if r[1] is None or r[2] is None]
    zero_ids = [r[0] for r in places if r[1] == 0 and r[2] == 0]
    off_grid_ids = [r[0] for r in places if r[1] is not None and r[2] is not None and not on_grid(r[1], r[2])]
    label = lambda r: place_label(r[4], r[3], config.UNNAMED_PARISH_LABELS)
    names = [str(r[3]) for r in places if r[3] is not None]
    longest = max((len(n) for n in names), default=0)
    counties = {}
    for r in places:
        if has_letters(r[4]):
            counties.setdefault(name_key(r[4]), " ".join(str(r[4]).split()))       # grouping key -> the spelling to show
    return {
        "rows": len(rows), "ids": set(seen), "distinct": len(seen), "lo": min(seen, default=None), "hi": max(seen, default=None),
        "zero_rows": len(rows) - len(places), "no_id_rows": sum(r[0] is None for r in rows),
        "repeated": sorted(i for i, n in seen.items() if n > 1),
        "fractional": sorted(i for i in seen if isinstance(i, float)),
        "no_name": [r[0] for r in places if label(r) is None],                       # no name and no label to show instead
        "labelled": [r[0] for r in places if not has_letters(r[3]) and label(r) is not None],
        "no_county": sum(not has_letters(r[4]) for r in places),
        "no_county_ids": [r[0] for r in places if not has_letters(r[4])],
        "caps_counties": sorted({str(r[4]).strip() for r in places if has_letters(r[4]) and str(r[4]) == str(r[4]).upper()}),
        "caps_parishes": sum(has_letters(n) and n == n.upper() for n in names),
        "several_names": sum("," in n for n in names),
        "longest": longest, "at_longest": sum(len(n) == longest for n in names),
        "counties": counties,
        "no_centroid": len(places) - len(located), "centroid_zero": sum(x == 0 and y == 0 for x, y in located),
        "off_grid": sum(not on_grid(x, y) for x, y in located),
        "no_centroid_ids": no_centroid_ids, "centroid_zero_ids": zero_ids, "off_grid_ids": off_grid_ids,
        "unlocated_ids": set(no_centroid_ids) | set(zero_ids) | set(off_grid_ids),
        "x_range": (min((x for x, _ in located), default=None), max((x for x, _ in located), default=None)),
        "y_range": (min((y for _, y in located), default=None), max((y for _, y in located), default=None)),
    }


def summarise_year(counts, table_ids, other_ids=None):
    """How one census year's people (counts: {parish id: people}) sit in the parish table it should use, and in the other one."""
    people = sum(counts.values())
    real = {i: n for i, n in counts.items() if i not in (None, 0)}
    lost = {i: n for i, n in real.items() if i not in table_ids}
    return {
        "people": people, "no_id": counts.get(None, 0), "zero": counts.get(0, 0),
        "found": sum(n for i, n in real.items() if i in table_ids), "lost": sum(lost.values()),
        "lost_ids": sorted(lost, key=lambda i: -lost[i]), "lost_by_id": lost,
        "in_other": None if other_ids is None else sum(n for i, n in real.items() if i in other_ids),
        "lo": min(real, default=None), "hi": max(real, default=None), "distinct": len(real),
        "unused": len(table_ids - set(real)), "fractional_people": sum(n for i, n in real.items() if isinstance(i, float)),
    }


def compare_lookup(rows, lookup):
    """The parish ids and names of a parish table against the lookup file."""
    names = {}
    for parish_id, county, parish in lookup:
        names.setdefault(parish_id, []).append((name_key(county), name_key(parish)))
    missing, differing_parish, differing_county = [], [], []
    for parish_id, _, _, parish, county in rows:
        if parish_id in (None, 0):
            continue
        options = names.get(parish_id)
        if not options:
            missing.append(parish_id)
        else:
            if name_key(parish) not in {p for _, p in options}:
                differing_parish.append((parish_id, parish, options[0][1]))
            if name_key(county) not in {c for c, _ in options}:
                differing_county.append((parish_id, county, options[0][0]))
    return {"missing": sorted(missing), "parish": differing_parish, "county": differing_county,
            "repeated": sorted(i for i, n in Counter(i for i, _, _ in lookup).items() if n > 1)}


# ---------------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------------

def make_report(data, lookup=None):
    """(lines, problems): the report as text, and the short list of things worth a look."""
    lines, problems = [], []

    def note(text=""):
        lines.append(text)

    def look(text):
        lines.append(f"  LOOK: {text}")
        problems.append(text)

    tables = {b: summarise_table(t["rows"]) for b, t in sorted(data["tables"].items())}
    years_of = {b: [year for year, y in sorted(data["years"].items()) if y["boundaries"] == b] for b in tables}
    total = {year: sum(y["counts"].values()) for year, y in data["years"].items()}

    def spread(b, ids):
        """{year: people carrying one of these ids} for the census years that use table b."""
        return {year: sum(data["years"][year]["counts"].get(i, 0) for i in ids) for year in years_of[b]}

    def where(spread_):
        return ", ".join(f"{year} {n:,} ({_pct(n, total[year])})" for year, n in spread_.items() if n)

    def share(spread_):
        return max((n / total[year] for year, n in spread_.items() if total[year]), default=0.0)

    note("PARISH TABLES")
    for b, s in tables.items():
        t = data["tables"][b]
        note(f"  {t['name']}: {s['rows']:,} rows, {s['distinct']:,} different ids from {_fmt(s['lo'])} to {_fmt(s['hi'])} "
             f"(id column: {t['id_type']}); id 0 on {s['zero_rows']:,} rows")
        if s["repeated"]:
            people = spread(b, s["repeated"])
            what = f"{t['name']}: {len(s['repeated']):,} parish ids appear on more than one row (e.g. {_examples(s['repeated'])})"
            if any(people.values()):
                look(f"{what}; people carry them and would be counted more than once: {where(people)}. Stage 1 stops until the table has one row per id")
            else:
                note(f"  {what}; no census person carries them, so nothing is counted twice, and stage 1 goes on")
        if s["no_id_rows"]:
            look(f"{t['name']}: {s['no_id_rows']:,} rows have no parish id")
        if s["fractional"]:
            note(f"  {len(s['fractional'])} ids are not whole numbers (e.g. {_examples(s['fractional'])}): the attributes columns must be able to hold them too")
        if s["no_name"]:
            people = spread(b, s["no_name"])
            what = f"{t['name']}: {len(s['no_name']):,} parishes have no real name (blank or \"-\"; ids e.g. {_examples(sorted(set(s['no_name'])))})"
            tail = f"; people in them: {where(people)}" if any(people.values()) else "; no census person is in them"
            if share(people) > NAME_SHARE:
                look(f"{what}{tail}. They are left out of the places lists, though their people are on the maps")
            else:
                note(f"  {what}{tail}: too few people to matter for the places lists")
        if s["labelled"]:
            people = spread(b, s["labelled"])
            note(f"  {t['name']}: {len(s['labelled']):,} parishes have no name but get one for the places lists from config.UNNAMED_PARISH_LABELS "
                 f"(ids e.g. {_examples(sorted(set(s['labelled'])))}); people in them: {where(people) or 'none'}")
        if s["no_county"]:
            people = spread(b, s["no_county_ids"])
            what = f"{t['name']}: {s['no_county']:,} parishes have no county"
            tail = f"; people in them: {where(people)}" if any(people.values()) else "; no census person is in them"
            if share(people) > NAME_SHARE:
                look(f"{what}{tail}")
            else:
                note(f"  {what}{tail}: too few people to matter")
        if s["caps_counties"]:
            note(f"  {len(s['caps_counties'])} counties are in ALL CAPITALS (e.g. {_examples(s['caps_counties'])}); stage 5 shows them as ordinary capitals")
        note(f"  names: {s['several_names']:,} hold several parishes in one (with a comma); the longest name has {s['longest']} characters "
             f"({s['at_longest']:,} names that long{'; a limit that cuts names short?' if s['at_longest'] > 5 and s['longest'] >= 50 else ''}); {s['caps_parishes']:,} parish names in ALL CAPITALS")
        note(f"  centroids: x from {_fmt(s['x_range'][0])} to {_fmt(s['x_range'][1])}, y from {_fmt(s['y_range'][0])} to {_fmt(s['y_range'][1])}")
        for count, ids, text in (
                (s["no_centroid"], s["no_centroid_ids"], "have no x/y; their people cannot be put on a map"),
                (s["centroid_zero"], s["centroid_zero_ids"], "have x = 0 and y = 0"),
                (s["off_grid"], s["off_grid_ids"], "have a centroid outside the map grid. x and y should be British National Grid "
                                                   "metres (x up to about 700,000, y up to about 1,250,000), not degrees")):
            if count:
                people = spread(b, ids)
                if any(people.values()):
                    look(f"{t['name']}: {count:,} parishes {text}; people in them: {where(people)}")
                else:
                    note(f"  {t['name']}: {count:,} parishes {text}; no census person is in them")

    if len(tables) == 2:
        (b1, s1), (b2, s2) = tables.items()
        shared = sorted(s1["ids"] & s2["ids"])
        if shared:
            look(f"the two parish tables share {len(shared):,} parish ids (e.g. {_examples(shared)}). The numbering schemes are meant to be apart, so that "
                 "a year joined to the wrong table finds no parish instead of the wrong one")
        else:
            note("  the two parish tables share no ids: a year joined to the wrong table would find no parish, not a wrong one")
        only1 = sorted(s1["counties"][k] for k in set(s1["counties"]) - set(s2["counties"]))
        only2 = sorted(s2["counties"][k] for k in set(s2["counties"]) - set(s1["counties"]))
        if only1 or only2:
            note(f"  counties named in only one table (a parish is pooled over the census years by county and name, so these do not pool across the two tables):")
            note(f"    only in {data['tables'][b1]['name']}: {_examples(only1, 8) or 'none'}")
            note(f"    only in {data['tables'][b2]['name']}: {_examples(only2, 8) or 'none'}")

    note()
    note("CENSUS YEARS (people counted per parish id of the attributes table)")
    note(f"  {'year':<6}{'id column':<16}{'people':>14}  {'ids used':<22}{'id 0':>7}{'no id':>7}{'not in table':>14}{'in other table':>16}")
    detail = []
    for year, y in sorted(data["years"].items()):
        table = tables[y["boundaries"]]
        other = next((s for b, s in tables.items() if b != y["boundaries"]), None)
        s = summarise_year(y["counts"], table["ids"], None if other is None else other["ids"])
        s["unlocated"] = sum(y["counts"].get(i, 0) for i in table["unlocated_ids"])
        used = f"{_fmt(s['lo'])} to {_fmt(s['hi'])}"
        note(f"  {year:<6}{y['column']:<16}{s['people']:>14,}  {used:<22}{_pct(s['zero'], s['people']):>7}{_pct(s['no_id'], s['people']):>7}"
             f"{_pct(s['lost'], s['people']):>14}{(_pct(s['in_other'], s['people']) if s['in_other'] is not None else 'n/a'):>16}")
        detail.append((year, y, s, table))

    for year, y, s, table in detail:
        real = s["people"] - s["zero"] - s["no_id"]
        note(f"  {year}: uses {data['tables'][y['boundaries']]['name']}; {s['distinct']:,} parish ids in use, {s['unused']:,} parishes in the table nobody is in"
             f"{' (expected for Scotland: it is not in this census)' if s['unused'] and year in config.SCOTLAND_MISSING_YEARS else ''}; id column {y['att']}.{y['column']} is {y['id_type']}")
        if not s["people"]:
            look(f"{year}: the attributes table has no rows")
            continue
        unplaced = s["zero"] + s["no_id"] + s["lost"] + s["unlocated"]
        note(f"  {year}: {unplaced:,} people ({_pct(unplaced, s['people'])}) cannot be put on a map: id 0 {s['zero']:,}, no id {s['no_id']:,}, "
             f"id not in the table {s['lost']:,}, parish without a usable location {s['unlocated']:,}")
        if real and s["lost"] / real > LOST_SHARE:
            look(f"{year}: {_pct(s['lost'], real)} of the people with a parish id have one that is not in {data['tables'][y['boundaries']]['name']}; "
                 f"the ids most often missing: {_lost_examples(s)}")
        elif s["lost"]:
            note(f"  {year}: {s['lost']:,} people have an id that is not in the table (ids most often missing: {_lost_examples(s)})")
        stale = sorted(i for i in config.CONPAR_ID_FIXES if i in s["lost_by_id"])
        if stale:
            look(f"{year}: {y['att']}.{y['column']} still holds ids that the fix list (pg_conpar_dic.txt) moves: "
                 f"{_examples([f'{i} (should be {config.CONPAR_ID_FIXES[i]})' for i in stale], 5)}")
        if y["boundaries"] == 1901:
            unshifted = sum(n for i, n in s["lost_by_id"].items() if 200000 < i < 200000 + config.SCOTLAND_1901_SHIFT)
            if unshifted:
                look(f"{year}: {unshifted:,} people carry Scottish ids in the 200,000s; in the 1901 numbering Scotland is 300,001 and up "
                     "(pg_conpar_dic.txt: add 100,000)")
        if s["in_other"] is not None and real and s["in_other"] / real > OTHER_SHARE:
            look(f"{year}: {_pct(s['in_other'], real)} of the people carry ids that are in the OTHER parish table; is {y['column']} the right column, "
                 f"and {data['tables'][y['boundaries']]['name']} the right table, for this year?")
        if s["no_id"] and year in config.CENSUS_NULL_PARISH_IS_NONE:
            note(f"  {year}: {s['no_id']:,} people ({_pct(s['no_id'], s['people'])}) have no parish id (NULL); that is how this year records people not in a parish "
                 "(soldiers, sailors, people abroad), and stage 1 counts them with the id-0 people of the other years")
        elif s["no_id"]:
            note(f"  {year}: {s['no_id']:,} people have no parish id at all (NULL); stage 1 counts them under \"not counted although they should be\", not under id 0")
        if _text_type(y["id_type"]) or _text_type(table_type(data, y)):
            look(f"{year}: a parish id column holds text ({y['id_type']} and {table_type(data, y)}); the join needs numbers on both sides")
        if s["fractional_people"] or table["fractional"]:
            if _integer_type(y["id_type"]):
                # a fractional parish's people can only carry a whole number here: the one below or above (truncated or rounded)
                around = {n for f in table["fractional"] for n in (math.floor(f), math.ceil(f))} - set(table["fractional"])
                near = sum(y["counts"].get(i, 0) for i in around)
                text = (f"{year}: the parish table has fractional ids (e.g. {_examples(table['fractional'])}) but {y['att']}.{y['column']} is {y['id_type']}, "
                        f"which cannot hold them. The whole-number ids next to them carry {near:,} people ({_pct(near, s['people'])}) between them; "
                        "that is the most who can be in the wrong parish")
                if near / s["people"] > NAME_SHARE:
                    look(text)
                else:
                    note("  " + text)
            else:
                note(f"  {year}: {s['fractional_people']:,} people carry a fractional parish id")

    if lookup is not None:
        note()
        note(f"LOOKUP FILE ({len(lookup):,} rows)")
        every = set().union(*(t["ids"] for t in tables.values())) if tables else set()
        for b, t in sorted(data["tables"].items()):
            c = compare_lookup(t["rows"], lookup)
            note(f"  {t['name']}: {len(c['missing']):,} ids are not in the lookup (e.g. {_examples(c['missing'])}); "
                 f"{len(c['parish']):,} parish names and {len(c['county']):,} counties differ (ignoring capitals and spaces)")
            for label, items in (("parish", c["parish"]), ("county", c["county"])):
                for parish_id, ours, theirs in items[:CAPS_LOOK]:
                    note(f"    id {parish_id}: {label} \"{ours}\" here, \"{theirs}\" in the lookup")
        note(f"  the lookup has {len({i for i, _, _ in lookup} - every):,} ids that are in neither parish table")
        repeated = compare_lookup([], lookup)["repeated"]
        if repeated:
            note(f"  {len(repeated):,} ids appear on more than one row of the lookup (e.g. {_examples(repeated)}); a parish table built by joining "
                 "to it on the id would repeat them")

    note()
    note(f"{len(problems)} thing(s) to look at" + (":" if problems else "; the ids look consistent."))
    for problem in problems:
        note(f"  - {problem}")
    return lines, problems


def table_type(data, year_data):
    return data["tables"][year_data["boundaries"]]["id_type"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--census-years", nargs="*", type=int, default=config.RUN["census_years"],
                        help="which census years to check (default GBNAMES_CENSUS_YEARS in run.settings)")
    parser.add_argument("--lookup", help="also compare the parish tables with this lookup file (CONPARID, RC1851, Parish(s))")
    args = parser.parse_args()
    print(config.describe_run(), flush=True)
    lookup = read_lookup(args.lookup) if args.lookup else None
    cfg = config.settings()
    conn = db.connect("census")
    data = gather(conn, cfg, sorted(set(args.census_years)))
    conn.close()
    lines, _ = make_report(data, lookup)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
