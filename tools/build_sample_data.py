#!/usr/bin/env python3
"""Build a SAMPLE data release for the static GBNames site (writes site/data/).

What is real and what is made up
--------------------------------
REAL     the map shapes for smith/macdonald/sion (two periods each, trimmed from the real
         release - tools/sample_inputs/kde/), the Scotland outline (tools/sample_inputs/
         scotland_mask.json, also from the real release), and the OAC / LOAC 2021 names,
         colours and descriptions (tools/sample_inputs/).
MADE UP  every count, forename, place and classification result for a surname. They are
         generated from the surname itself, so the sample is identical on every run.
         Every file is flagged "synthetic": true so it can never be mistaken for real data.

Run from the project root:      python3 tools/build_sample_data.py
Then check it:                  python3 tools/validate_data.py site/data

The file formats are described in docs/data-contract.md.
"""
import csv
import datetime
import hashlib
import json
import math
import random
import shutil
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUTS = Path(__file__).resolve().parent / "sample_inputs"
KDE_SAMPLE_DIR = INPUTS / "kde"
SCOTLAND_MASK = INPUTS / "scotland_mask.json"
GROUP_NAMES = ROOT / "pipeline" / "reference" / "group_names.json"
OUT = ROOT / "site" / "data"

# Invented, round-robin - FPC/GB2C's real colours come from git-ignored raw-indicators/ files
# (see tools/build_lookups.py), which this standalone sample script deliberately does not depend
# on. Group NAMES are public (published papers; see feedback-safeguarded-data-never-public), only
# real area-to-group lookups are safeguarded - irrelevant here anyway, since every value below is
# made up.
SAMPLE_PALETTE = ["#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", "#fdb462", "#b3de69",
                  "#fccde5", "#d9d9d9", "#bc80bd", "#ccebc5", "#ffed6f"]

THRESHOLD = 100

# ---------------------------------------------------------------------------
# release description (manifest.json)
# ---------------------------------------------------------------------------

# One entry per map / slider position - matches run.settings' GBNAMES_CENSUS_YEARS and
# pipeline/config.py's MAP_YEARS["register"].
PERIODS = [
    {"id": "1851", "year": 1851, "source": "census"},
    {"id": "1861", "year": 1861, "source": "census"},
    {"id": "1881", "year": 1881, "source": "census"},
    {"id": "1891", "year": 1891, "source": "census"},
    {"id": "1901", "year": 1901, "source": "census"},
    {"id": "1911", "year": 1911, "source": "census", "mask": "scotland",
     "note": "Census data for Scotland are not available for this year."},
    {"id": "1921", "year": 1921, "source": "census", "mask": "scotland",
     "note": "Census data for Scotland are not available for this year."},
    {"id": "1997", "year": 1997, "source": "register"},
    {"id": "2000", "year": 2000, "source": "register"},
    {"id": "2005", "year": 2005, "source": "register"},
    {"id": "2010", "year": 2010, "source": "register"},
    {"id": "2015", "year": 2015, "source": "register"},
    {"id": "2020", "year": 2020, "source": "register"},
    {"id": "2025", "year": 2025, "source": "register"},
    {"id": "2026", "year": 2026, "source": "register"},
]

CENSUS_YEARS = [1851, 1861, 1881, 1891, 1901, 1911, 1921]
REGISTER_YEARS = list(range(1997, 2027))

MANIFEST = {
    "schema": 1,
    "release": {
        "version": "4.0.0-dev",
        "date": datetime.date.today().isoformat(),
        "synthetic": True,
        "note": "Sample data: the map shapes are real, everything else is made up for development.",
    },
    "threshold": THRESHOLD,
    "sources": {
        "census": {"label": "Historical censuses", "short": "Census",
                   "counts": "All residents", "coverage": [1851, 1911]},
        "register": {"label": "Consumer registers", "short": "Registers",
                     "counts": "Adults (estimated)", "coverage": [1997, 2016]},
    },
    "periods": PERIODS,
    "levels": [
        {"level": 1, "label": "Concentrated", "colour": "#6baed6"},
        {"level": 2, "label": "More concentrated", "colour": "#4292c6"},
        {"level": 3, "label": "Most concentrated", "colour": "#2171b5"},
    ],
    "masks": {
        "scotland": {"url": "masks/scotland.json", "colour": "#dcdcdc", "opacity": 0.7,
                     "label": "No data for Scotland"},
    },
    "basemap": {
        "center": [54.505, -4], "zoom": 6, "minZoom": 6, "maxZoom": 12,
        "maxBounds": [[50, -28], [62, 20]],
        "tiles": [
            {"url": "https://maps.cdrc.ac.uk/tiles/shine_urbanmask_light/{z}/{x}/{y}.png",
             "attribution": "Contains Ordnance Survey data © Crown copyright",
             "bounds": [[50, -28], [62, 20]]},
            {"url": "https://maps.cdrc.ac.uk/tiles/shine_labels_gbnames/{z}/{x}/{y}.png",
             "labels": True, "bounds": [[50, -12], [62, 4]]},
        ],
    },
    "examples": [],  # filled in below with the names that exist
}

# ---------------------------------------------------------------------------
# shared text, names and colours (lookups.json)
# ---------------------------------------------------------------------------

CARDS = {
    "counts": {"title": "Number of bearers"},
    "forenames_census": {"title": "Historical forenames",
                         "about": "Most common female and male forenames for your search over the period {census_from}–{census_to}."},
    "forenames_register": {"title": "Recent forenames",
                           "about": "Most common female and male forenames for adults over the period {register_from}–{register_to}."},
    "places_census": {"title": "Top historical parishes", "subtitle": "Registration districts and parishes",
                      "columns": ["District name", "Parish name"]},
    "places_register": {"title": "Top areas today", "subtitle": "Middle layer Super Output Areas",
                        "columns": ["District name", "Area name"]},
    "oac": {"title": "UK Output Area Classification",
            "about": "A classification of UK neighbourhoods, arranged into Supergroups and Groups based upon 2021/22 Census of Population data. We show the Supergroup and Group in which your selected surname occurs most frequently."},
    "loac": {"title": "London Output Area Classification",
             "about": "A classification of London's neighbourhoods, arranged into Supergroups and Groups based upon 2021 Census of Population data. We show the Supergroup and Group in which your selected surname occurs most frequently."},
    "fpc": {"title": "Financial Precarity Classification",
            "about": "A classification of neighbourhoods by financial precarity, arranged into Supergroups and Groups. We show the Supergroup and Group in which your selected surname occurs most frequently."},
    "gb2c": {"title": "Gambling Behaviours in Britain",
             "about": "A classification of neighbourhoods by the gambling behaviours most common among their estimated active gamblers. We show the Type most closely associated with your selected surname."},
    "eth": {"title": "Ethnicity Estimator", "subtitle": "Surname roots",
            "about": "Given and family names provide clues as to ethnicity. We show a rough estimate of the probable ethnicity of the surname that you entered."},
    "imd": {"title": "Index of Multiple Deprivation",
            "about": "Neighbourhoods can be ranked from best to worst and we show the decile in which your selected surname occurs most frequently."},
    "ahah": {"title": "Access to Healthy Assets and Hazards",
             "about": "Neighbourhoods can be ranked from best to worst and we show the decile in which your selected surname occurs most frequently."},
}

SCALES = {
    # {decile} is replaced client-side with a colour pill (site/js/app.js's decilePill()) - must
    # match that exact placeholder name, not the fact value's own "mode" field name.
    "imd": {"colours": ["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee08b",
                        "#d9ef8b", "#a6d96a", "#66bd63", "#1a9850", "#006837"],
            "text": "Your selected surname occurs most frequently in {decile} of the Index of Multiple Deprivation (IMD). The first decile is the most deprived and the tenth decile the least deprived."},
    "ahah": {"colours": ["#F46D43", "#F68A5B", "#F8A774", "#FAC48D", "#FCE1A6",
                         "#FFFFBF", "#D0DCBC", "#A2BAB9", "#7397B6", "#4575B4"],
             "text": "Your selected surname occurs most frequently in {decile} of the Access to Healthy Assets and Hazards index. The first decile is the healthiest and the tenth decile the least healthy."},
}

ETH = {
    "WBR": ("White - British", "#fccde5"), "WIR": ("White - Irish", "#b3de69"),
    "WAO": ("White - Other", "#fdb462"), "BAF": ("Black - African", "#ffffb3"),
    "BCA": ("Black - Caribbean", "#bebada"), "AIN": ("Asian - Indian", "#fb8072"),
    "APK": ("Asian - Pakistani", "#80b1d3"), "ABD": ("Asian - Bangladeshi", "#fdc086"),
    "ACN": ("Asian - Chinese", "#8dd3c7"), "AAO": ("Asian - Other", "#ccebc5"),
    "OXX": ("Other ethnic group", "#bc80bd"), "unknown": ("Unknown", "#d9d9d9"),
}

LOAC_COLOURS = {
    "A": "#66C2A5", "B": "#FC8D62", "C": "#8DA0CB", "D": "#E78AC3", "E": "#A6D854",
    "F": "#FFD92F", "G": "#D9DDDF",
    "A1": "#539B84", "A2": "#97C3B5", "A3": "#C5FFEC", "B1": "#CA714E", "B2": "#FC9872",
    "C1": "#63708E", "C2": "#C6D0E5", "D1": "#B96E9C", "D2": "#EEADD5", "D3": "#FFB9DA",
    "E1": "#74973B", "E2": "#CAE898", "F1": "#CCAE26", "F2": "#FFE882",
    "G1": "#7D7D7D", "G2": "#D1D1D1",
}

# invented material for the made-up facts
FEMALE = ["mary", "elizabeth", "sarah", "ann", "jane", "margaret", "emma", "alice", "catherine",
          "susan", "helen", "joan", "eleanor", "grace", "ruth", "hannah", "lucy", "olivia"]
MALE = ["john", "william", "george", "thomas", "james", "henry", "charles", "robert", "david",
        "peter", "edward", "arthur", "frederick", "joseph", "samuel", "daniel", "oliver", "jack"]
OLD_PLACES = [("Lancashire", "Liverpool"), ("Yorkshire", "Sheffield"), ("Devon", "Plymouth"),
              ("Kent", "Canterbury"), ("Durham", "Sunderland"), ("Cornwall", "Camborne"),
              ("Norfolk", "Norwich"), ("Glamorgan", "Cardiff"), ("Staffordshire", "Stoke"),
              ("Somerset", "Bath"), ("Cheshire", "Chester"), ("Cumberland", "Carlisle")]
NEW_PLACES = [("Leeds", "Headingley"), ("Birmingham", "Selly Oak"), ("Glasgow City", "Partick"),
              ("Cardiff", "Roath"), ("Manchester", "Didsbury"), ("Bristol", "Clifton"),
              ("Edinburgh", "Morningside"), ("Sheffield", "Crookes"), ("Newcastle", "Jesmond"),
              ("Cornwall", "Truro"), ("Norfolk", "Wymondham"), ("Kent", "Whitstable")]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def write_json(path, obj, pretty=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    else:
        text = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def read_rows(filename):
    with open(INPUTS / filename, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def build_fpc():
    """Two-level (supergroups + groups), names from the real group_names.json (public - see
    SAMPLE_PALETTE's note above), colours invented."""
    names = json.loads(GROUP_NAMES.read_text(encoding="utf-8"))["fpc"]
    supergroups = {code: {"name": entry["name"], "colour": colour}
                   for colour, (code, entry) in zip(SAMPLE_PALETTE, sorted(names["supergroups"].items()))}
    groups = {code: {"name": entry["name"], "supergroup": entry["supergroup"], "colour": colour}
              for colour, (code, entry) in zip(SAMPLE_PALETTE * 2, sorted(names["groups"].items()))}
    return {"supergroups": supergroups, "groups": groups}


def build_gb2c():
    """Flat (groups only), same real-names/invented-colours approach as build_fpc()."""
    names = json.loads(GROUP_NAMES.read_text(encoding="utf-8"))["gb2c"]
    groups = {code: {"name": entry["name"], "colour": colour}
              for colour, (code, entry) in zip(SAMPLE_PALETTE, sorted(names["groups"].items()))}
    return {"groups": groups}


def build_lookups():
    oac = {"supergroups": {}, "groups": {}}
    for kind, code, colour, name, desc in read_rows("oac21_descriptions.csv"):
        entry = {"name": name.strip(), "colour": colour, "desc": desc.strip()}
        if kind == "Supergroup":
            oac["supergroups"][code] = entry
        else:
            entry["supergroup"] = code[0]
            oac["groups"][code] = entry

    loac = {"supergroups": {}, "groups": {}}
    for kind, code, name, desc in read_rows("loac21_descriptions.csv"):
        entry = {"name": name.strip(), "colour": LOAC_COLOURS[code], "desc": desc.strip()}
        if kind == "Supergroup":
            loac["supergroups"][code] = entry
        else:
            entry["supergroup"] = code[0]
            loac["groups"][code] = entry

    return {
        "schema": 1,
        "cards": CARDS,
        "oac": oac,
        "loac": loac,
        "fpc": build_fpc(),
        "gb2c": build_gb2c(),
        "eth": {k: {"name": n, "colour": c} for k, (n, c) in ETH.items()},
        "scales": SCALES,
    }


def rng_for(name):
    return random.Random(int(hashlib.sha256(name.encode()).hexdigest(), 16))


def decile_distribution(rng):
    centre = rng.uniform(1.5, 9.5)
    weights = [math.exp(-((i - centre) ** 2) / (2 * 1.9 ** 2)) * (0.7 + 0.6 * rng.random())
               for i in range(1, 11)]
    total = sum(weights)
    dist = [round(w / total, 3) for w in weights]
    dist[-1] = round(dist[-1] + (1 - sum(dist)), 3)
    mode = dist.index(max(dist)) + 1
    mean = sum((i + 1) * p for i, p in enumerate(dist))
    sd = math.sqrt(sum(p * ((i + 1) - mean) ** 2 for i, p in enumerate(dist)))
    return mode, round(mean, 2), round(sd, 2), dist


def synthetic_counts(rng, mapped_years):
    """Made-up counts for every year. Mapped years always reach the threshold."""
    big_name = len(mapped_years) >= 5
    base = rng.randint(3000, 60000) if big_name else rng.randint(120, 900)
    counts = {"census": {}, "register": {}}
    for year in CENSUS_YEARS:
        value = int(base * (0.6 + 0.08 * (year - 1851) / 10) * rng.uniform(0.85, 1.15))
        counts["census"][str(year)] = value
    for year in REGISTER_YEARS:
        value = int(base * 1.5 * rng.uniform(0.9, 1.1))
        counts["register"][str(year)] = value
    if not big_name:
        for source, years in (("census", CENSUS_YEARS), ("register", REGISTER_YEARS)):
            for year in years:
                if year not in mapped_years:
                    counts[source][str(year)] = rng.randint(20, THRESHOLD - 5)
    for year, source in mapped_years.items():
        key = str(year)
        counts[source][key] = max(counts[source][key], THRESHOLD + rng.randint(5, 60))
    return counts


def group_distribution(rng, codes, mode_code):
    """Made-up share per group code (renderGroupCard/renderFlatGroupCard both need one, not just a
    mode): mode_code's own weight is always drawn above every other code's, so it is genuinely the
    largest share after normalising, consistent with it being reported as the mode."""
    weights = {code: rng.uniform(0.2, 1.0) for code in codes}
    weights[mode_code] = max(weights.values()) + rng.uniform(0.3, 0.8)
    total = sum(weights.values())
    return {code: round(w / total, 3) for code, w in weights.items()}


def group_fact(rng, codes):
    mode_code = rng.choice(codes)
    return {"group": mode_code, "distribution": group_distribution(rng, codes, mode_code)}


def synthetic_facts(rng, oac_groups, loac_groups, fpc_groups, gb2c_groups):
    imd_mode, imd_mean, imd_sd, imd_dist = decile_distribution(rng)
    ahah_mode, _, _, ahah_dist = decile_distribution(rng)
    return {
        "forenames": {
            "census": {"f": rng.sample(FEMALE, 10), "m": rng.sample(MALE, 10)},
            "register": {"f": rng.sample(FEMALE, 10), "m": rng.sample(MALE, 10)},
        },
        "places": {
            "census": [{"area": a, "name": n} for a, n in rng.sample(OLD_PLACES, 10)],
            "register": [{"area": a, "name": n} for a, n in rng.sample(NEW_PLACES, 10)],
        },
        "oac": group_fact(rng, oac_groups),
        "loac": group_fact(rng, loac_groups),
        "fpc": group_fact(rng, fpc_groups),
        "gb2c": group_fact(rng, gb2c_groups),
        "eth": {"group": rng.choice(list(ETH.keys()))},
        "imd": {"mode": imd_mode, "mean": imd_mean, "sd": imd_sd, "distribution": imd_dist},
        "ahah": {"mode": ahah_mode, "distribution": ahah_dist},
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    if OUT.exists():
        shutil.rmtree(OUT)  # site/data is generated, so it is safe to rebuild from scratch

    lookups = build_lookups()
    oac_groups = sorted(lookups["oac"]["groups"])
    loac_groups = sorted(lookups["loac"]["groups"])
    fpc_groups = sorted(lookups["fpc"]["groups"])
    gb2c_groups = sorted(lookups["gb2c"]["groups"])
    period_source = {p["id"]: p["source"] for p in PERIODS}

    # Scotland outline, already in the right shape (a trimmed copy of the real release's own
    # masks/scotland.json - see tools/sample_inputs/README.md)
    write_json(OUT / "masks" / "scotland.json", json.loads(SCOTLAND_MASK.read_text(encoding="utf-8")))

    # one bundle per surname with a real sample map file (tools/sample_inputs/kde/<name>.json -
    # a dict of period id -> FeatureCollection, already trimmed to the periods we ship)
    shards = {}
    sizes = {}
    for kde_file in sorted(KDE_SAMPLE_DIR.glob("*.json")):
        name = kde_file.stem
        by_period = json.loads(kde_file.read_text(encoding="utf-8"))
        maps = {pid: fc for pid, fc in by_period.items() if pid in period_source}
        if not maps:
            continue
        rng = rng_for(name)
        mapped_years = {int(pid): period_source[pid] for pid in maps}
        bundle = {
            "schema": 1,
            "name": name,
            "synthetic": True,
            "counts": synthetic_counts(rng, mapped_years),
            "maps": maps,
        }
        path = OUT / "names" / name[:2] / f"{name}.json"
        raw = write_json(path, bundle)
        gz = len(zlib.compress(path.read_bytes(), 6))
        sizes[name] = (raw, gz, len(maps))
        shards.setdefault(name[:2], []).append(name)

        # facts are published separately (tools/split_facts.py does the same split on a real
        # release) - site/js/data.js's fetchFacts() fetches this file independently, never looks
        # for a "facts" key inside the names/ bundle.
        write_json(OUT / "facts" / name[:2] / f"{name}.json",
                   synthetic_facts(rng, oac_groups, loac_groups, fpc_groups, gb2c_groups))

    for prefix, names in shards.items():
        write_json(OUT / "index" / f"{prefix}.json", sorted(names))

    MANIFEST["examples"] = sorted(sizes)
    write_json(OUT / "manifest.json", MANIFEST, pretty=True)
    write_json(OUT / "lookups.json", lookups, pretty=True)

    print(f"Wrote sample release to {OUT.relative_to(ROOT)}")
    for name, (raw, gz, n) in sorted(sizes.items()):
        print(f"  {name:10s} {n} map periods   {raw/1024:7.1f} KB raw   about {gz/1024:6.1f} KB compressed")


if __name__ == "__main__":
    main()
