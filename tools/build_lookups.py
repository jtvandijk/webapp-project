#!/usr/bin/env python3
"""Build lookups.json for the real release: the shared words and colours (docs/data-contract.md, "lookups.json").

    python3 tools/build_lookups.py                     # writes work/lookups.json
    python3 tools/build_lookups.py --out somewhere/lookups.json

Put the result next to manifest.json in the release folder (work/release/ in the TRE), then run
    python3 tools/validate_data.py work/release        # without --skip-lookups

Sources (all names and colours; nothing about areas or people):
  OAC and LOAC   tools/sample_inputs/oac21_descriptions.csv, loac21_descriptions.csv (+ LOAC colours from tools/build_sample_data.py)
  FPC            names from pipeline/reference/group_names.json, colours from raw-indicators/fpc/fpc_label_colors.csv
                 (git-ignored; only the classification's lookup from area to group is safeguarded, not its names or colours)
  Ethnicity      pipeline/config.py ETH_GROUPS (+ "unknown")
The page text below is the wording to edit. Standard library only, so it runs anywhere.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_sample_data as sample          # LOAC_COLOURS, INPUTS, read_rows
import validate_data                        # the release checker, so the file is checked the way the release will be
from pipeline import config

FPC_RAW = ROOT / "raw-indicators" / "fpc" / "fpc_label_colors.csv"
GROUP_NAMES = ROOT / "pipeline" / "reference" / "group_names.json"

# The published FPC file has one typo (confirmed by the user 2026-09-24); the other spelling differences stay as published.
FPC_TYPOS = {"Underprivilege dependent": "Underprivileged dependent"}

# Ethnicity Estimator colours: the old site's Set3 colours for the groups it had; the three new groups (Black - Caribbean,
# Asian - Pakistani, Asian - Bangladeshi) take the three Set3 colours the old site did not use.
ETH_COLOURS = {"WBR": "#fccde5", "WIR": "#b3de69", "WAO": "#fdb462", "BAF": "#ffffb3", "BCA": "#bc80bd",
               "AIN": "#bebada", "APK": "#ccebc5", "ABD": "#ffed6f", "ACN": "#fb8072", "AAO": "#80b1d3",
               "OXX": "#8dd3c7", config.ETH_UNKNOWN: "#d9d9d9"}

IMD_COLOURS = ["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee08b", "#d9ef8b", "#a6d96a", "#66bd63", "#1a9850", "#006837"]
# The old site ran this ramp orange (decile 1) to blue (decile 10) and said decile 1 was the worst. Our AHAH decile 1 is the
# HEALTHIEST (the source's own direction), so the ramp is reversed to keep orange meaning the least healthy.
AHAH_COLOURS = ["#4575B4", "#7397B6", "#A2BAB9", "#D0DCBC", "#FFFFBF", "#FCE1A6", "#FAC48D", "#F8A774", "#F68A5B", "#F46D43"]

CARDS = {
    "counts": {"title": "Number of bearers"},
    "forenames_census": {"title": "Historical forenames",
                         "about": "Most common female and male forenames for your search over the period {census_from}–{census_to}."},
    "forenames_register": {"title": "Recent forenames",
                           "about": "Most common female and male forenames for adults over the period {register_from}–{register_to}."},
    "places_census": {"title": "Top historical parishes", "subtitle": "Registration counties and parishes",
                      "columns": ["County name", "Parish name"]},
    "places_register": {"title": "Top areas today", "subtitle": "Middle layer Super Output Areas",
                        "columns": ["District name", "Area name"]},
    "oac": {"title": "UK Output Area Classification",
            "about": "A classification of UK neighbourhoods, arranged into Supergroups and Groups based upon 2021/22 Census of Population data. We show the Supergroup and Group in which your selected surname occurs most frequently."},
    "loac": {"title": "London Output Area Classification",
             "about": "A classification of London's neighbourhoods, arranged into Supergroups and Groups based upon 2021 Census of Population data. We show the Supergroup and Group in which your selected surname occurs most frequently."},
    "fpc": {"title": "Financial Precarity Classification",
            "about": "A classification of Great Britain's neighbourhoods by financial precarity, arranged into groups. We show the group in which your selected surname occurs most frequently."},
    "eth": {"title": "Ethnicity Estimator", "subtitle": "Surname roots",
            "about": "Given and family names provide clues as to ethnicity. We show the census ethnic group that is most common among the people with your selected surname, estimated from their forenames and surnames."},
    "imd": {"title": "Index of Multiple Deprivation",
            "about": "Neighbourhoods can be ranked from most to least deprived and we show the decile in which your selected surname occurs most frequently. England, Wales and Scotland are each ranked on their own and the ranks are then compared directly.",
            "score": "The GBNames deprivation score is the average neighbourhood percentile of the people with your selected surname, from 1 (most deprived) to 100 (least deprived), with its spread."},
    "ahah": {"title": "Access to Healthy Assets and Hazards",
             "about": "Neighbourhoods can be ranked from the healthiest to the least healthy and we show the decile in which your selected surname occurs most frequently."},
}

SCALES = {
    "imd": {"colours": IMD_COLOURS,
            "text": "Your selected surname occurs most frequently in decile {mode} of the Index of Multiple Deprivation. The first decile is the most deprived and the tenth decile the least deprived."},
    "ahah": {"colours": AHAH_COLOURS,
             "text": "Your selected surname occurs most frequently in decile {mode} of the Access to Healthy Assets and Hazards index. The first decile is the healthiest and the tenth decile the least healthy."},
}


def read_classification(filename, colours=None):
    """OAC or LOAC: {"supergroups": {code: {...}}, "groups": {code: {..., "supergroup": code}}}."""
    out = {"supergroups": {}, "groups": {}}
    for row in sample.read_rows(filename):
        if colours is None:                                   # OAC: kind, code, colour, name, description
            kind, code, colour, name, desc = row
        else:                                                 # LOAC: kind, code, name, description
            kind, code, name, desc = row
            colour = colours[code]
        entry = {"name": name.strip(), "colour": colour, "desc": desc.strip()}
        if kind == "Supergroup":
            out["supergroups"][code] = entry
        else:
            entry["supergroup"] = code[0]
            out["groups"][code] = entry
    return out


def read_fpc():
    """FPC group names (corrected) and colours; stops if the two sources disagree about a name."""
    if not FPC_RAW.exists():
        raise SystemExit(f"{FPC_RAW} is missing: the FPC group colours come from it (it is git-ignored; it lives in raw-indicators/fpc/).")
    names = json.loads(GROUP_NAMES.read_text(encoding="utf-8"))["fpc"]["groups"]
    groups = {}
    with open(FPC_RAW, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = row["labels"].strip()
            label = row["Financial Precarity Classification"]
            match = re.match(r"^" + re.escape(code) + r":\s+(.*\S)\s*$", label)
            if not match:
                raise SystemExit(f"FPC label {label!r} does not start with {code!r}: ")
            name = FPC_TYPOS.get(match.group(1), match.group(1))
            if names.get(code, {}).get("name") != name:
                raise SystemExit(f"FPC group {code}: {name!r} in {FPC_RAW.name} but {names.get(code, {}).get('name')!r} in group_names.json")
            groups[code] = {"name": name, "colour": row["color"].strip()}
    if set(groups) != set(names):
        raise SystemExit(f"FPC groups differ between {FPC_RAW.name} ({sorted(groups)}) and group_names.json ({sorted(names)})")
    return {"groups": groups}


def build():
    oac = read_classification("oac21_descriptions.csv")
    loac = read_classification("loac21_descriptions.csv", colours=sample.LOAC_COLOURS)
    fpc = read_fpc()
    names = json.loads(GROUP_NAMES.read_text(encoding="utf-8"))
    for scheme, block in (("oac", oac), ("loac", loac)):        # the preview's names and this file must say the same
        theirs = {code: g["name"] for code, g in names[scheme]["groups"].items()}
        ours = {code: g["name"] for code, g in block["groups"].items()}
        if theirs != ours:
            raise SystemExit(f"{scheme}: group names differ between group_names.json and tools/sample_inputs/")

    eth = {code: {"name": name, "colour": ETH_COLOURS[code]} for code, name in config.ETH_GROUPS.items()}
    eth[config.ETH_UNKNOWN] = {"name": "Unknown", "colour": ETH_COLOURS[config.ETH_UNKNOWN]}
    return {"schema": 1, "cards": CARDS, "oac": oac, "loac": loac, "fpc": fpc, "eth": eth, "scales": SCALES}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "work" / "lookups.json")
    args = parser.parse_args()
    lookups = build()

    report = validate_data.Report()
    validate_data.check_lookups(lookups, report)
    if report.errors:
        print("\n".join(report.errors))
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(lookups, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: oac {len(lookups['oac']['supergroups'])} supergroups / {len(lookups['oac']['groups'])} groups, "
          f"loac {len(lookups['loac']['supergroups'])} / {len(lookups['loac']['groups'])}, fpc {len(lookups['fpc']['groups'])} groups, "
          f"eth {len(lookups['eth'])} entries, cards {len(lookups['cards'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
