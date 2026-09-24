"""Stage 1: count the bearers of every surname in every year, and make the name list.

    python3 -m pipeline.s1_counts                    # both sources
    python3 -m pipeline.s1_counts --sources register  # just the register database, e.g. while the
                                                       # census database is not ready yet

Writes (in the work folder, see config.py):
  counts.csv   source, year, surname, n         every name and year with at least COUNT_FLOOR bearers
  names.csv    surname, map_periods, max_n, periods
               the names that get a page: at least THRESHOLD[source] bearers in at least one map period

A run with --sources only covers those sources; counts.csv and names.csv only hold what was
actually counted this run, not a full release.

For the census it also reports how the people of each year divide up (counted, parish id 0 which is expected, and the
ones that should have been counted but were not), and stops if a person appears twice or the parish ids do not fit the
boundaries; for the register, the postcode match rate.

Surnames are turned into keys first (pipeline/names.py), so "SMITH", "Smith" and "smith" are one
name, and junk values such as "XXXX" or "nan" are dropped.
"""
import argparse
import csv
from collections import defaultdict

from . import config, db, sql
from .names import surname_key


def check_lookup(conn, cfg):
    """Stop if the postcode lookup has a postcode twice: everybody living there would count twice."""
    query = sql.duplicate_lookup_keys(cfg)
    if query and db.fetch(conn, query)[0][0]:
        raise SystemExit(f"The postcode lookup {cfg['register']['address_table']} has "
                         f"{db.fetch(conn, query)[0][0]:,} postcodes that appear more than once. "
                         "Make it one row per postcode (or fix the table name in config.py) and run again.")


def match_rate(conn, cfg):
    """{year: (rows with usable coordinates, all rows)} for the register. If the postcodes in the
    register and the lookup are written differently, or the lookup is too old, this shows it."""
    years = config.REGISTER_YEARS
    total = dict(db.fetch(conn, sql.register_totals(cfg, years, matched=False)))
    matched = dict(db.fetch(conn, sql.register_totals(cfg, years, matched=True)))
    return {int(y): (int(matched.get(y, 0)), int(total[y])) for y in total}


def report_match_rate(rates):
    """Print the match rate; stop if it is so low that something must be wrong."""
    worst = min(rates, key=lambda y: rates[y][0] / rates[y][1])
    overall = sum(m for m, t in rates.values()) / sum(t for m, t in rates.values())
    print(f"register rows with usable coordinates: {overall:.1%} overall, lowest {rates[worst][0] / rates[worst][1]:.1%} in {worst}")
    if overall < 0.80:
        raise SystemExit("Fewer than 80% of the register rows find their postcode in the lookup. The postcodes are "
                         "probably written differently in the two tables (spaces, capitals), or the lookup table or "
                         "its column names in config.py are wrong. Nothing has been written.")
    if rates[worst][0] / rates[worst][1] < 0.95:
        print(f"note: the match rate is below 95% in {worst}; if it falls in the newest years, the postcode lookup is probably out of date.")


def check_parish_tables(conn, cfg):
    """Stop if a parish table has a parish twice AND people carry that id: each of them would count twice. A repeated id
    that nobody carries (a stray piece of a shape, in the shapefiles: an id 0 aside, the 1851 and 1901 tables have three)
    does no harm, and is only said."""
    for year in sorted(set(config.CENSUS_YEARS)):
        repeated = db.fetch(conn, sql.duplicate_parish_ids(cfg, year))[0][0]
        if not repeated:
            continue
        people = int(db.fetch(conn, sql.people_in_repeated_parish_ids(cfg, year))[0][0] or 0)
        if people:
            raise SystemExit(f"The parish table used for {year} has {repeated:,} parish ids that appear more than once, and "
                             f"{people:,} people carry them, so they would be counted more than once. Make the table one row per "
                             "parish (python3 -m pipeline.check_parishes names the ids) or fix the table name in config.py, and run again.")
        print(f"note: the parish table used for {year} has {repeated:,} parish ids on more than one row, but nobody in {year} "
              "carries them, so nothing is counted twice.")


def census_match(conn, cfg):
    """{year: (people, with an attributes row, with parish id 0, counted)} for every census year."""
    found = {}
    for year in config.CENSUS_YEARS:
        people = int(db.fetch(conn, sql.census_rows(cfg, year))[0][0])
        joined, nowhere, counted = db.fetch(conn, sql.census_match(cfg, year))[0]
        found[year] = (people, int(joined or 0), int(nowhere or 0), int(counted or 0))
    return found


def report_census_match(found):
    """Print how the people of each census year divide up, and stop if something must be wrong. People with parish id 0
    are expected (soldiers, sailors, people abroad) and are not a problem. Two things are:
      * more attributes rows than people: a person appears twice, so every count would be inflated;
      * many people who HAVE a parish id that is not in the parish boundaries used for that year: the wrong boundaries
        (say the 1851 ones for 1911), or a parish table that is not the one the ids come from."""
    worst, problems = 0.0, []
    print("census: how the people divide up (a person with parish id 0 is expected: soldiers, sailors, people abroad)")
    for year, (people, joined, nowhere, counted) in found.items():
        if not people:
            raise SystemExit(f"The census table for {year} has no rows. Check the table names in config.py.")
        missing_row, extra_rows = max(people - joined, 0), max(joined - people, 0)
        unexplained = max(joined - nowhere - counted, 0) + missing_row            # should be in a parish but are not counted
        share = unexplained / max(people - nowhere, 1)
        worst = max(worst, share)
        print(f"  {year}: {people:,} people; {counted / people:.1%} counted; {nowhere / people:.1%} parish id 0; "
              f"{unexplained / people:.2%} not counted although they should be (id not in the parish boundaries, no surname, or no attributes row)"
              + (f"; {extra_rows / people:.2%} MORE attributes rows than people" if extra_rows else ""))
        if extra_rows / people > 0.01:
            problems.append(f"{year}: {extra_rows:,} more attributes rows than people ({extra_rows / people:.1%}): people appear twice")
    if problems:
        raise SystemExit("A person appears more than once, so counts would be inflated:\n  " + "\n  ".join(problems) +
                         "\nNothing has been written.")
    if worst > 0.20:
        raise SystemExit(f"In at least one census year more than 20% of the people who should be in a parish are not counted "
                         f"(worst {worst:.0%}). The parish ids probably do not belong to the boundaries used for that year, or the "
                         "parish table or its column names in config.py are wrong. Nothing has been written.")
    if worst > 0.05:
        print(f"note: in at least one census year {worst:.0%} of the people who should be in a parish are not counted; "
              "look at the years above.")


def count_all(register_conn, census_conn, cfg, sources=("register", "census")):
    """{(source, year, key): n} for every requested source and year. Register and census live in
    different databases in the TRE, so each gets its own connection - only pass (and open) the one(s)
    named in `sources`; the other can be None."""
    counts = defaultdict(int)
    if "register" in sources:
        check_lookup(register_conn, cfg)
        for year, raw, n in db.fetch(register_conn, sql.register_counts(cfg, config.REGISTER_YEARS)):
            key = surname_key(raw)
            if key:
                counts[("register", int(year), key)] += n
    if "census" in sources:
        for year in config.CENSUS_YEARS:
            for raw, n in db.fetch(census_conn, sql.census_counts(cfg, year)):
                key = surname_key(raw)
                if key:
                    counts[("census", year, key)] += n
    # names that only existed in tiny variants may fall below the floor once merged
    return {k: n for k, n in counts.items() if n >= config.COUNT_FLOOR}


def name_list(counts):
    """{key: [period ids with at least THRESHOLD[source] bearers]} for the names that get a page."""
    periods = {(p["source"], p["year"]): p["id"] for p in config.PERIODS}
    listed = defaultdict(list)
    for (source, year, key), n in sorted(counts.items(), key=lambda item: item[0][1]):
        if n >= config.THRESHOLD[source] and (source, year) in periods:
            listed[key].append(periods[(source, year)])
    return listed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sources", nargs="*", choices=["register", "census"], default=config.RUN_SOURCES,
                        help="which sources to count (default GBNAMES_SOURCES in run.settings)")
    args = parser.parse_args()
    sources = set(args.sources)
    print(config.describe_run(), flush=True)

    cfg = config.settings()
    register_conn = db.connect("register") if "register" in sources else None
    census_conn = db.connect("census") if "census" in sources else None
    if register_conn:
        report_match_rate(match_rate(register_conn, cfg))
    if census_conn:
        check_parish_tables(census_conn, cfg)
        report_census_match(census_match(census_conn, cfg))
    counts = count_all(register_conn, census_conn, cfg, sources)
    if register_conn:
        register_conn.close()
    if census_conn:
        census_conn.close()
    listed = name_list(counts)

    config.WORK.mkdir(parents=True, exist_ok=True)
    with open(config.WORK / "counts.csv", "w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["source", "year", "surname", "n"])
        for (source, year, key), n in sorted(counts.items(), key=lambda item: (item[0][2], item[0][0], item[0][1])):
            out.writerow([source, year, key, n])
    with open(config.WORK / "names.csv", "w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["surname", "map_periods", "max_n", "periods"])
        biggest = defaultdict(int)                       # the highest count of each name in any year
        for (source, year, key), n in counts.items():
            biggest[key] = max(biggest[key], n)
        for key in sorted(listed):
            out.writerow([key, len(listed[key]), biggest[key], ";".join(listed[key])])

    per_period = defaultdict(int)
    for periods in listed.values():
        for pid in periods:
            per_period[pid] += 1
    thresholds = ", ".join(f"{source} {n}" for source, n in config.THRESHOLD.items())
    print(f"sources counted this run: {', '.join(sorted(sources))}")
    print(f"{len(counts):,} name-year counts written to {config.WORK / 'counts.csv'}")
    print(f"{len(listed):,} names reach the threshold ({thresholds}) in at least one map period "
          f"({sum(per_period.values()):,} maps in total)")
    print("names with a map, by period: " +
          "  ".join(f"{p['id']}:{per_period[p['id']]}" for p in config.PERIODS if p["source"] in sources))


if __name__ == "__main__":
    main()
