#!/usr/bin/env python3
"""Build site/lookups/places.json: a flat {area code: human-readable name} map for the district
and MSOA/Intermediate Zone codes in facts.csv's places.register rows (tools/split_facts.py), so the
website can show real place names instead of raw GSS codes (confirmed with the user 2026-10-05).

All public, non-safeguarded reference geography - unlike raw-indicators/fpc, gb2c etc, nothing here
needs to stay out of the repo; the *raw downloads* just live in raw-indicators/places/ (git-ignored,
like every other raw download in this project) so the committed output is the compact lookup only.

    python3 tools/build_places_lookup.py                     # writes site/lookups/places.json

Sources (download once, save into raw-indicators/places/ with these names, re-run):
  lad_uk.csv              Local Authority Districts (UK-wide, incl. Scotland's 32 council areas) -
                          ONS Open Geography Portal, "Local Authority Districts ... Names and Codes
                          in the UK": https://open-geography-portalx-ons.hub.arcgis.com/
                          (search that name, Explore -> Download -> CSV)
  msoa_friendly_ew.csv    MSOA codes (England & Wales) with genuinely descriptive names (the raw ONS
                          MSOA21NM is just "Borough 001" - not useful to show) - House of Commons
                          Library "MSOA Names": https://houseofcommonslibrary.github.io/msoanames/
  iz_scotland_2011.csv    Intermediate Zone 2011 codes and names (Scotland) - NHS Scotland Open Data,
                          "Geography Codes and Labels": https://www.opendata.nhs.scot/dataset/geography-codes-and-labels/
  dz2022_lookup_scotland.csv
                          Intermediate Zone 2022 codes and names (Scotland's 2022 IZ revision added
                          new codes the 2011 file doesn't have, picking up exactly where it leaves
                          off - both vintages are needed for full coverage) -
                          https://statistics.gov.scot/data/data-zone-lookup-2022 ("2022 Data Zone Lookup")

Confirmed against the real facts.csv (2026-10-05): every district code and every MSOA/Intermediate
Zone code referenced in a 2,500-name sample resolves via this combined lookup - 348/348 districts,
5,299/5,299 MSOA/IZ codes.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw-indicators" / "places"
OUT = ROOT / "site" / "lookups" / "places.json"


def read_csv(path, encoding="utf-8-sig"):
    with open(path, encoding=encoding, newline="") as f:
        yield from csv.DictReader(f)


def build():
    missing = [p for p in ("lad_uk.csv", "msoa_friendly_ew.csv", "iz_scotland_2011.csv", "dz2022_lookup_scotland.csv")
              if not (RAW / p).exists()]
    if missing:
        raise SystemExit(f"Missing from {RAW}: {missing}. See this script's docstring for where to download each one from.")

    places = {}
    for row in read_csv(RAW / "lad_uk.csv"):
        places[row["LAD25CD"]] = row["LAD25NM"]
    for row in read_csv(RAW / "msoa_friendly_ew.csv"):
        places[row["msoa21cd"]] = row["msoa21hclnm"] or row["msoa21nm"]
    for row in read_csv(RAW / "iz_scotland_2011.csv"):
        places[row["IntZone"]] = row["IntZoneName"]
    for row in read_csv(RAW / "dz2022_lookup_scotland.csv", encoding="latin-1"):
        places.setdefault(row["IZ22_Code"], row["IZ22_Name"])   # 2011 file (just above) takes priority
    return places


def main():
    places = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(places, separators=(",", ":"), ensure_ascii=False))
    print(f"wrote {OUT}: {len(places):,} area codes")


if __name__ == "__main__":
    main()
