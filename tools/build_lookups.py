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
  GB2C           names from pipeline/reference/group_names.json; the raw download has no colour column, so GB2C_COLOURS
                 below is our own palette (confirmed with the user 2026-10-01): a muted jewel-tone family, deliberately
                 unlike OAC/LOAC/eth, with each hue chosen for that group's own name/character, not assigned arbitrarily
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
GB2C_RAW = ROOT / "raw-indicators" / "gb2c" / "classification_codes_and_names.csv"
GROUP_NAMES = ROOT / "pipeline" / "reference" / "group_names.json"
FPC_DESCRIPTIONS = ROOT / "pipeline" / "reference" / "fpc_descriptions.json"
GB2C_DESCRIPTIONS = ROOT / "pipeline" / "reference" / "gb2c_descriptions.json"

# FPC turns out to have a genuine two-level structure (confirmed by the user 2026-10-01, from the
# classification's own pen-portrait document) - 5 supergroups, each containing a handful of the 13
# groups above. GB2C's BG/B/G prefixes looked like the same thing at first, but the user decided
# (2026-10-02) they aren't a meaningful supergroup the way FPC's are - just a naming prefix - so GB2C
# stays flat (read_gb2c() below), one level only, despite having the same kind of source document.
# FPC's source doesn't publish a supergroup colour, so this is our own choice, same reasoning as
# GB2C_COLOURS below: a muted family, distinct per supergroup's own character, not an ordered scale.
FPC_SUPERGROUP_COLOURS = {
    "A": "#2A9D8F",   # Emerging Financial Climbers: young, upwardly mobile - teal
    "B": "#6A9F58",   # Suburban Financial Balancers: settled, stable - sage green
    "C": "#3D5A80",   # Mature and Financially Secure: steady, secure - slate blue
    "D": "#E09F3E",   # Financially Precarious Families: caution - amber
    "E": "#9E2A2B",   # Highly Vulnerable Families: the most severe - deep red
}

# Corrections to the published FPC labels, confirmed by the user (E12 on 2026-09-24, E13 on 2026-09-27).
FPC_TYPOS = {"Underprivilege dependent": "Underprivileged dependent", "Aging Blue-collar households": "Ageing Blue-collar households"}

# GB2C has no published colours (unlike FPC), so this is our own choice (confirmed with the user 2026-10-01): a
# muted jewel-tone family, visually distinct from OAC's primary mix, LOAC/eth's ColorBrewer pastels and the IMD/AHAH
# diverging ramps. Each hue is chosen for the group's own name/character (not an ordered/sequential scale - the data
# itself claims no order), and the 11 are spread across relative luminance (WCAG-style, computed, not eyeballed) so
# no two collapse together for colour-vision-deficient viewers - the tightest gap is BG5/B2 and G2/G3 alike.
GB2C_COLOURS = {
    "BG1": "#15767A",   # Engaged New-Age Gamblers: modern, tech-forward, actively engaged - teal
    "BG2": "#8FB3D9",   # Newcomers, sporadic/moderate play: tentative, just starting out - pale sky blue
    "BG3": "#E08A2E",   # Event-Driven Speculative Players: energetic, spikes around events - amber
    "BG4": "#5F9E78",   # Mindful Entertainment Seekers: calm, recreational - sage green
    "BG5": "#9C2B3C",   # High-Frequency High-Stake Losers: the clearest harm signal in the set - deep crimson
    "BG6": "#C94F8E",   # Young Occasional Binge Players: youthful, bursty - magenta-pink
    "B1":  "#8C6A42",   # Longstanding Habitual Veterans: steady, entrenched - umber/brown
    "B2":  "#41507A",   # Well-Resourced Hobbyists: affluent, relaxed - navy-indigo
    "G1":  "#C1562B",   # Episodic High Risk Takers: elevated risk, bursty - burnt orange
    "G2":  "#486675",   # Mindful Low-Rollers from Deprived Communities: calm, low stakes - slate blue-grey
    "G3":  "#7A4C8E",   # High-Stakes Gamers from Deprived Communities: high stakes, gaming not betting - plum/violet
}

# Ethnicity Estimator colours: the old site had nine (css btn-eee1 to btn-eee9, ColorBrewer Set3) and none of its own for Black - Caribbean,
# Asian - Pakistani or Asian - Bangladeshi, so those three take the three Set3 colours the old site did not use. Change them here.
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
            "about": "A classification of Great Britain's neighbourhoods by financial precarity, arranged into Supergroups and Groups. We show the Supergroup and Group in which your selected surname occurs most frequently."},
    "gb2c": {"title": "GB2C Gambling Classification",
             "about": "A classification of Great Britain's neighbourhoods by online gambling behaviour, arranged into groups. We show the group in which your selected surname occurs most frequently."},
    "eth": {"title": "Ethnicity Estimator", "subtitle": "Surname roots",
            "about": "Given and family names provide clues as to ethnicity. We show the census ethnic group that is most common among the people with your selected surname, estimated from their forenames and surnames."},
    "imd": {"title": "Index of Multiple Deprivation",
            "about": "Neighbourhoods can be ranked from most to least deprived and we show the decile in which your selected surname occurs most frequently. England, Wales and Scotland are each ranked on their own and the ranks are then compared directly.",
            "score": "The GBNames deprivation score is the average neighbourhood percentile of the people with your selected surname, from 1 (most deprived) to 100 (least deprived), with its spread."},
    "ahah": {"title": "Access to Healthy Assets and Hazards",
             "about": "Neighbourhoods can be ranked from the healthiest to the least healthy and we show the decile in which your selected surname occurs most frequently."},
}

SCALES = {
    # {decile} is replaced with a bolded "Decile N" (not plain text) when rendered - the one place in
    # each sentence that names this name's own result, as opposed to the scale in general.
    "imd": {"colours": IMD_COLOURS,
            "text": "Your selected surname occurs most frequently in {decile} of the Index of Multiple Deprivation. The first decile is the most deprived and the tenth decile the least deprived."},
    "ahah": {"colours": AHAH_COLOURS,
             "text": "Your selected surname occurs most frequently in {decile} of the Access to Healthy Assets and Hazards index. The first decile is the healthiest and the tenth decile the least healthy."},
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
    """FPC supergroups and groups: names from group_names.json (corrected), group colours from the
    published source, supergroup colours our own, pen-portrait descriptions for both levels from
    fpc_descriptions.json; stops if the sources disagree about a name."""
    if not FPC_RAW.exists():
        raise SystemExit(f"{FPC_RAW} is missing: the FPC group colours come from it (it is git-ignored; it lives in raw-indicators/fpc/).")
    all_names = json.loads(GROUP_NAMES.read_text(encoding="utf-8"))["fpc"]
    names, supergroup_names = all_names["groups"], all_names["supergroups"]
    descriptions = json.loads(FPC_DESCRIPTIONS.read_text(encoding="utf-8"))
    groups = {}
    with open(FPC_RAW, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = row["labels"].strip()
            label = row["Financial Precarity Classification"]
            match = re.match(r"^" + re.escape(code) + r":\s+(.*\S)\s*$", label)
            if not match:
                raise SystemExit(f"FPC label {label!r} does not start with {code!r}: ")
            name = FPC_TYPOS.get(match.group(1), match.group(1))
            entry = names.get(code, {})
            if entry.get("name") != name:
                raise SystemExit(f"FPC group {code}: {name!r} in {FPC_RAW.name} but {entry.get('name')!r} in group_names.json")
            groups[code] = {"name": name, "colour": row["color"].strip(), "supergroup": entry.get("supergroup"),
                            "desc": descriptions.get(code, "")}
    if set(groups) != set(names):
        raise SystemExit(f"FPC groups differ between {FPC_RAW.name} ({sorted(groups)}) and group_names.json ({sorted(names)})")
    if set(supergroup_names) != set(FPC_SUPERGROUP_COLOURS):
        raise SystemExit(f"FPC_SUPERGROUP_COLOURS does not have exactly the supergroups in group_names.json ({sorted(supergroup_names)})")
    supergroups = {code: {"name": sg["name"], "colour": FPC_SUPERGROUP_COLOURS[code], "desc": descriptions.get(code, "")}
                  for code, sg in supergroup_names.items()}
    return {"supergroups": supergroups, "groups": groups}


def read_gb2c():
    """GB2C groups (flat - no supergroup level, per the user 2026-10-02): names from
    group_names.json, colours our own (no published colour exists), pen-portrait descriptions from
    gb2c_descriptions.json; stops if the raw download's own codes disagree with group_names.json (the
    raw file has no colour of its own to cross-check names against, unlike FPC, so this only checks
    the codes match)."""
    if not GB2C_RAW.exists():
        raise SystemExit(f"{GB2C_RAW} is missing: GB2C's own codes come from it (it is git-ignored; it lives in raw-indicators/gb2c/).")
    names = json.loads(GROUP_NAMES.read_text(encoding="utf-8"))["gb2c"]["groups"]
    descriptions = json.loads(GB2C_DESCRIPTIONS.read_text(encoding="utf-8"))
    with open(GB2C_RAW, encoding="utf-8-sig", newline="") as f:
        raw_codes = {row["Classification Code"] for row in csv.DictReader(f)
                    if row["Level"] == "Subgroup" and row["Classification Code"] != "-"}
    if raw_codes != set(names):
        raise SystemExit(f"GB2C groups differ between {GB2C_RAW.name} ({sorted(raw_codes)}) and group_names.json ({sorted(names)})")
    if set(names) != set(GB2C_COLOURS):
        raise SystemExit(f"GB2C_COLOURS does not have exactly the groups in group_names.json ({sorted(names)})")
    groups = {code: {"name": entry["name"], "colour": GB2C_COLOURS[code], "desc": descriptions.get(code, "")}
             for code, entry in names.items()}
    return {"groups": groups}


def build():
    oac = read_classification("oac21_descriptions.csv")
    loac = read_classification("loac21_descriptions.csv", colours=sample.LOAC_COLOURS)
    fpc = read_fpc()
    gb2c = read_gb2c()
    names = json.loads(GROUP_NAMES.read_text(encoding="utf-8"))
    for scheme, block in (("oac", oac), ("loac", loac)):        # the preview's names and this file must say the same
        theirs = {code: g["name"] for code, g in names[scheme]["groups"].items()}
        ours = {code: g["name"] for code, g in block["groups"].items()}
        if theirs != ours:
            raise SystemExit(f"{scheme}: group names differ between group_names.json and tools/sample_inputs/")

    eth = {code: {"name": name, "colour": ETH_COLOURS[code]} for code, name in config.ETH_GROUPS.items()}
    eth[config.ETH_UNKNOWN] = {"name": "Unknown", "colour": ETH_COLOURS[config.ETH_UNKNOWN]}
    return {"schema": 1, "cards": CARDS, "oac": oac, "loac": loac, "fpc": fpc, "gb2c": gb2c, "eth": eth, "scales": SCALES}


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
          f"gb2c {len(lookups['gb2c']['groups'])} groups, eth {len(lookups['eth'])} entries, cards {len(lookups['cards'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
