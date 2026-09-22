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
    parser.add_argument("--sources", nargs="*", choices=["register", "census"], default=["register", "census"],
                        help="which sources to count (default: both)")
    args = parser.parse_args()
    sources = set(args.sources)

    cfg = config.settings()
    register_conn = db.connect("register") if "register" in sources else None
    census_conn = db.connect("census") if "census" in sources else None
    if register_conn:
        report_match_rate(match_rate(register_conn, cfg))
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
