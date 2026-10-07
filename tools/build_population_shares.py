#!/usr/bin/env python3
"""Build work/population_shares.json: each OAC/LOAC/GB2C/FPC group's (and supergroup's) share of the
real population, so the website can show a baseline marker on each bar alongside a name's own share -
is this name over- or under-represented in a Group, relative to how many people actually live there?

    python3 tools/build_population_shares.py

Reads work/neighbourhood/nbhd_oac.csv, nbhd_loac.csv, nbhd_gb2c.csv, nbhd_fpc.csv, nbhd_count.csv and
nbhd_count_lsoa.csv (all built by tools/prep_neighbourhood.py - run that first if they're stale) and
joins each classification's own area->group lookup to the matching population file (OAC/LOAC are
output areas; GB2C/FPC are LSOA/data zone, hence the separate nbhd_count_lsoa.csv).

Only ever writes group-level aggregates - a handful of numbers per classification - never the
area->group join itself, so nothing safeguarded (FPC/GB2C's area-level lookup) leaves work/, same
rule tools/prep_neighbourhood.py already follows.

LOAC's denominator is London's own population (the London output areas already in nbhd_loac.csv),
not Great Britain's - its groups partition London only, so "expected share" has to mean "share of
Londoners", not "share of Great Britain" (confirmed with the user, 2026-10-06).

OAC's denominator is the UK's population, Northern Ireland included - unlike every other classification
here, nbhd_oac.csv and nbhd_count.csv both carry Northern Ireland (see tools/prep_neighbourhood.py's
docstring), because the 2021/2 UK OAC genuinely classifies it. Without that, this baseline would be a
Great Britain number describing itself as a UK one (confirmed with the user, 2026-10-07).
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "neighbourhood"
OUT = ROOT / "work" / "population_shares.json"


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def read_population(filename):
    """{area_code: population} from an nbhd_count*.csv."""
    return {row["area_code"]: int(row["population"]) for row in read_csv(WORK / filename)}


def shares_by(rows, population, code_key):
    """{code: that code's share of the total population covered by `rows`}."""
    totals = {}
    grand_total = 0
    for row in rows:
        pop = population[row["area_code"]]
        code = row[code_key]
        totals[code] = totals.get(code, 0) + pop
        grand_total += pop
    return {code: pop / grand_total for code, pop in totals.items()}


def two_level_shares(filename, population, group_key, supergroup_key):
    rows = read_csv(WORK / filename)
    return {"groups": shares_by(rows, population, group_key),
            "supergroups": shares_by(rows, population, supergroup_key)}


def flat_shares(filename, population, group_key):
    rows = read_csv(WORK / filename)
    return {"groups": shares_by(rows, population, group_key)}


def main():
    oa_population = read_population("nbhd_count.csv")
    lsoa_population = read_population("nbhd_count_lsoa.csv")

    out = {
        "oac": two_level_shares("nbhd_oac.csv", oa_population, "oac_group", "oac_supergroup"),
        "loac": two_level_shares("nbhd_loac.csv", oa_population, "loac_group", "loac_supergroup"),
        "gb2c": flat_shares("nbhd_gb2c.csv", lsoa_population, "gb2c_group"),
        "fpc": two_level_shares("nbhd_fpc.csv", lsoa_population, "fpc_group", "fpc_cluster"),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    for name, d in out.items():
        sg = f", {len(d['supergroups'])} supergroups" if "supergroups" in d else ""
        print(f"{name}: {len(d['groups'])} groups{sg}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
