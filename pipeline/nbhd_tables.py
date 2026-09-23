"""The neighbourhood lookup tables in the TRE: the SQL to create and load them, and a check on them.

    python3 -m pipeline.nbhd_tables ddl                                  # print the SQL that creates the tables
    python3 -m pipeline.nbhd_tables ddl --csv-dir work/neighbourhood     # ... and the lines that load the CSVs
    python3 -m pipeline.nbhd_tables ddl --replace                        # ... dropping any old ones first
    python3 -m pipeline.nbhd_tables check                                # in the TRE, once they are loaded
    python3 -m pipeline.nbhd_tables check --year 2024
    python3 -m pipeline.nbhd_tables lookup "SW1A 1AA" "G1 1AA"           # what stage 5 uses for a postcode

The tables come from tools/prep_neighbourhood.py (work/neighbourhood/nbhd_*.csv). Their names and
columns are in config.py (NBHD_TABLE_COLUMNS, and "facts" > "tables" in the profile), so the SQL here,
the fake data and the queries in stage 5 cannot disagree. Change the schema name in the "tre" profile
if you cannot create tables in registers_lookup.

`ddl` uses the "tre" profile unless GBNAMES_PROFILE says otherwise. The lines that load the CSVs are
psql's \copy, which reads the file on the machine psql runs on, so give --csv-dir the folder as seen from there.

`lookup` shows, for some postcodes, the neighbourhood codes in the postcode directory and the value each
table gives for them, joined exactly as stage 5 joins them. To check the tables end to end, compare it
with the download itself: copy an area code from here into  python3 tools/audit_neighbourhood.py --show CODE
on your own computer, which prints what the raw download says for that area.

`check` joins the register rows of one year to the postcode directory and to every table, and prints
how many find a row, per country. Expect about 99.9% everywhere (the rest are postcodes with no
neighbourhood code in the directory itself). A country that is far lower means a table was made for
the wrong geography, or was only partly loaded: England, Wales and Scotland each use different
columns for some of them (see config.FACT_QUERIES). LOAC is London only, so it is shown as a share of
the rows in London.
"""
import argparse
import os
import re
from pathlib import Path

from . import config, db, sql

COUNTRIES = {"E92000001": "England", "W92000004": "Wales", "S92000003": "Scotland"}
LOOKUP_FIELDS = ["postcode", "counts", "country", "oa", "lsoa", "lsoa_2011", "msoa", "district",
                 "oac_supergroup", "oac_group", "oac_subgroup", "loac_group", "ahah_rank", "ahah_decile",
                 "imd_source", "imd_rank", "imd_areas", "imd_decile", "imd_pctile"]
LOW = 0.98                # a share below this in any country is reported as a problem


def ddl(cfg, csv_dir=None, replace=False):
    """The SQL text for the four tables, optionally with the lines that load their CSVs."""
    lines = ["-- The neighbourhood tables. Made by pipeline/nbhd_tables.py from config.py."]
    for key, columns in config.NBHD_TABLE_COLUMNS.items():
        name = cfg["facts"]["tables"][key]
        if replace:
            lines.append(f"DROP TABLE IF EXISTS {name};")
        body = ",\n  ".join(f"{c} {t}" + (" PRIMARY KEY" if c == "area_code" else "") for c, t in columns)
        lines.append(f"CREATE TABLE {name} (\n  {body}\n);")
        if csv_dir:
            lines.append(f"\\copy {name} ({', '.join(c for c, _ in columns)}) FROM '{Path(csv_dir) / f'nbhd_{key}.csv'}' "
                         "WITH (FORMAT csv, HEADER true)")
        lines.append("")
    return "\n".join(lines)


def check(conn, cfg, year):
    """Print the coverage of every table, per country. Returns a list of problems (empty if all is well)."""
    problems = []
    for key in config.NBHD_TABLE_COLUMNS:
        repeated = db.fetch(conn, sql.duplicate_nbhd_keys(cfg, key))[0][0]
        if repeated:
            problems.append(f"{cfg['facts']['tables'][key]} has {repeated:,} area codes that appear more than once")
    rows = db.fetch(conn, sql.nbhd_coverage(cfg, year))
    print(f"register rows in {year}, and the share that find a row, per country:")
    print(f"{'':10} {'rows':>12} {'OAC':>8} {'AHAH':>8} {'IMD':>8} {'LOAC (of London)':>17} {'neighbourhood':>14}")
    for country, n, oac, ahah, imd, london, loac, msoa in sorted(rows, key=lambda r: str(r[0])):
        n, london = int(n), int(london or 0)
        share = lambda k, of=n: (int(k or 0) / of) if of else float("nan")
        loac_share = share(loac, london) if london else float("nan")
        print(f"{COUNTRIES.get(country, str(country)):10} {n:>12,} {share(oac):>8.2%} {share(ahah):>8.2%} "
              f"{share(imd):>8.2%} {loac_share:>17.2%} {share(msoa):>14.2%}")
        for label, value in (("OAC", share(oac)), ("AHAH", share(ahah)), ("IMD", share(imd)), ("neighbourhood code", share(msoa))):
            if value < LOW:
                problems.append(f"{COUNTRIES.get(country, country)}: only {value:.1%} of rows find {label}")
        if london and loac_share < LOW:
            problems.append(f"{COUNTRIES.get(country, country)}: only {loac_share:.1%} of London rows find LOAC")
    if not rows:
        problems.append(f"no register rows found for {year}")
    return problems


def standard_postcode(text):
    """A postcode as the linked registers and the lookup write it: lower case, letters and digits only."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def lookup(conn, cfg, postcodes):
    """{standard postcode: {field: value}} for the postcodes that are in the postcode directory."""
    asked = sorted({standard_postcode(p) for p in postcodes} - {""})
    if not asked:
        return {}
    return {row[0]: dict(zip(LOOKUP_FIELDS, row)) for row in db.fetch(conn, sql.postcode_lookup(cfg, asked))}


def describe(cfg, text, row):
    """The lines that say, for one postcode, what stage 5 would use, and why anything is missing."""
    if row is None:
        return [f"{text}  ({standard_postcode(text)})", f"  not in the postcode directory ({cfg['register']['address_table']})"]
    areas = cfg["register"]["areas"]
    scotland = row["country"] == config.COUNTRY_SCOTLAND
    country = COUNTRIES.get(row["country"], str(row["country"]))
    lines = [f"{text}  ({row['postcode']})",
             "  counted by the pipeline: " + ("yes" if row["counts"] else "NO (no grid reference, or not in Great Britain: "
                                              "it is left out of every count)") + f"; country {country}",
             "  codes in the directory: " + "  ".join(f"{areas[k]} {row[k] or '(blank)'}" for k in ("oa", "lsoa", "lsoa_2011", "msoa", "district"))]

    def why(code_field):
        code = row[code_field]
        return "the postcode has no such code" if not code else f"code {code} is not in the table"

    label = lambda name: f"  {name:16}"
    joined = lambda field: f"   [joined on {areas[field]}]"
    if row["oac_group"]:
        lines.append(f"{label('UK OAC 2021/22')}supergroup {row['oac_supergroup']}, group {row['oac_group']}, subgroup {row['oac_subgroup']}{joined('oa')}")
    else:
        lines.append(f"{label('UK OAC 2021/22')}no row: {why('oa')}")
    if row["loac_group"]:
        lines.append(f"{label('London OAC')}group {row['loac_group']}{joined('oa')}")
    else:
        lines.append(f"{label('London OAC')}" + ("no row: " + why("oa") if (row["district"] or "").startswith("E09")
                                                  else "none (it covers London only)"))
    if row["ahah_decile"] is not None:
        lines.append(f"{label('AHAH v5.1')}decile {row['ahah_decile']}, rank {int(row['ahah_rank']):,}   (1 = healthiest, 10 = least healthy){joined('lsoa')}")
    else:
        lines.append(f"{label('AHAH v5.1')}no row: {why('lsoa')}")
    if row["imd_decile"] is not None:
        used = "lsoa_2011" if scotland else "lsoa"
        lines.append(f"{label('deprivation')}{row['imd_source']}: decile {row['imd_decile']}, percentile {row['imd_pctile']}, "
                     f"rank {int(row['imd_rank']):,} of {int(row['imd_areas']):,}   (1 = most deprived){joined(used)}"
                     + (" (Scotland is on the 2011 data zones)" if scotland else ""))
    else:
        lines.append(f"{label('deprivation')}no row: {why('lsoa_2011' if scotland else 'lsoa')}")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("ddl", help="print the SQL that creates (and loads) the tables")
    make.add_argument("--csv-dir", help="the folder with nbhd_*.csv, as psql will see it: adds the lines that load them")
    make.add_argument("--replace", action="store_true", help="drop each table first, to replace an old one")
    show = sub.add_parser("lookup", help="what stage 5 uses for some postcodes")
    show.add_argument("postcodes", nargs="+", help='postcodes, with or without spaces, e.g. "SW1A 1AA"')
    test = sub.add_parser("check", help="check the loaded tables against the real register")
    test.add_argument("--year", type=int, default=config.REGISTER_YEARS[-2], help="register year to check (default: last full year)")
    args = parser.parse_args()

    if args.command == "ddl":
        print(ddl(config.settings(os.environ.get("GBNAMES_PROFILE", "tre")), args.csv_dir, args.replace))
        return
    cfg = config.settings()
    conn = db.connect("register")
    if args.command == "lookup":
        found = lookup(conn, cfg, args.postcodes)
        conn.close()
        for text in args.postcodes:
            print("\n".join(describe(cfg, text, found.get(standard_postcode(text)))) + "\n")
        return
    problems = check(conn, cfg, args.year)
    conn.close()
    if problems:
        print("\nPROBLEMS:\n  " + "\n  ".join(problems))
        raise SystemExit(1)
    print("\nall tables look right")


if __name__ == "__main__":
    main()
