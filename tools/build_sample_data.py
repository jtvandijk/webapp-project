#!/usr/bin/env python3
"""Build a SAMPLE data release for the static GBNames site (writes site/data/).

What is real and what is made up
--------------------------------
REAL     the map shapes (read from the KDE files in gbnames/static/kde/), the Scotland
         outline, and the OAC / LOAC 2021 names, colours and descriptions
         (tools/sample_inputs/).
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
KDE_DIR = ROOT / "gbnames" / "static" / "kde"
INPUTS = Path(__file__).resolve().parent / "sample_inputs"
OUT = ROOT / "site" / "data"

THRESHOLD = 100

# ---------------------------------------------------------------------------
# release description (manifest.json)
# ---------------------------------------------------------------------------

# One entry per map / slider position. To add a year (say 1921 or 2026) add a line here.
PERIODS = [
    {"id": "1851", "year": 1851, "source": "census"},
    {"id": "1861", "year": 1861, "source": "census"},
    {"id": "1881", "year": 1881, "source": "census"},
    {"id": "1891", "year": 1891, "source": "census"},
    {"id": "1901", "year": 1901, "source": "census"},
    {"id": "1911", "year": 1911, "source": "census", "mask": "scotland",
     "note": "The 1911 census data for Scotland are not available."},
    {"id": "1998", "year": 1998, "source": "register"},
    {"id": "2006", "year": 2006, "source": "register"},
    {"id": "2016", "year": 2016, "source": "register"},
]

CENSUS_YEARS = [1851, 1861, 1881, 1891, 1901, 1911]
REGISTER_YEARS = list(range(1997, 2017))

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
    "iuc": {"title": "Internet User Classification",
            "about": "Describes the nature and extent of Internet usage by the residents of neighbourhoods across Great Britain."},
    "eee": {"title": "Ethnicity Estimator", "subtitle": "Surname roots",
            "about": "Given and family names provide clues as to ethnicity. We show a rough estimate of the probable ethnicity of the surname that you entered."},
    "imd": {"title": "Index of Multiple Deprivation",
            "about": "Neighbourhoods can be ranked from best to worst and we show the decile in which your selected surname occurs most frequently."},
    "ahah": {"title": "Access to Healthy Assets and Hazards",
             "about": "Neighbourhoods can be ranked from best to worst and we show the decile in which your selected surname occurs most frequently."},
    "bbs": {"title": "Broadband speed",
            "about": "The modal fixed broadband download speed available to bearers of your selected surname."},
}

SCALES = {
    "imd": {"colours": ["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee08b",
                        "#d9ef8b", "#a6d96a", "#66bd63", "#1a9850", "#006837"],
            "text": "Your selected surname occurs most frequently in decile {mode} of the Index of Multiple Deprivation. The first decile is the worst performing decile whereas the tenth decile is the best performing decile."},
    "ahah": {"colours": ["#F46D43", "#F68A5B", "#F8A774", "#FAC48D", "#FCE1A6",
                         "#FFFFBF", "#D0DCBC", "#A2BAB9", "#7397B6", "#4575B4"],
             "text": "Your selected surname occurs most frequently in decile {mode} of the Access to Healthy Assets and Hazards index. The first decile is the worst performing decile whereas the tenth decile is the best performing decile."},
    "bbs": {"colours": ["#276419", "#4d9221", "#7fbc41", "#b8e186", "#e6f5d0",
                        "#fde0ef", "#f1b6da", "#de77ae", "#c51b7d", "#8e0152"],
            "labels": ["Speed band %d (placeholder label)" % i for i in range(1, 11)],
            "text": "Your selected surname falls in group {mode}, which suggests a modal fixed broadband download speed of {label}."},
}

IUC = {  # names from the CDRC Internet User Classification; descriptions left out on purpose
    1: ("e-Cultural Creators", "#ea4d78"), 2: ("e-Professionals", "#f36d5a"),
    3: ("e-Veterans", "#e4a5d0"), 4: ("Youthful Urban Fringe", "#ffd39b"),
    5: ("e-Rational Utilitarians", "#a5cfbc"), 6: ("e-Mainstream", "#d2d1ab"),
    7: ("Passive and Uncommitted Users", "#79cdcd"), 8: ("Digital Seniors", "#dd7cdc"),
    9: ("Settled Offline Communities", "#808fee"), 10: ("e-Withdrawn", "#8470ff"),
}

EEE = {
    1: ("White - British", "#fccde5"), 2: ("White - Irish", "#b3de69"),
    3: ("White - Other", "#fdb462"), 4: ("Black - African", "#ffffb3"),
    5: ("Asian - Indian", "#bebada"), 6: ("Asian - Chinese", "#fb8072"),
    7: ("Asian - Other", "#80b1d3"), 8: ("Other Ethnic Group", "#8dd3c7"),
    9: ("Unknown", "#d9d9d9"),
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
        "iuc": {str(k): {"name": n, "colour": c} for k, (n, c) in IUC.items()},
        "eee": {str(k): {"name": n, "colour": c} for k, (n, c) in EEE.items()},
        "scales": SCALES,
    }


def rng_for(name):
    return random.Random(int(hashlib.sha256(name.encode()).hexdigest(), 16))


def read_map(path):
    fc = json.loads(path.read_text(encoding="utf-8"))
    features = [
        {"type": "Feature", "properties": {"level": int(f["properties"]["level"])},
         "geometry": f["geometry"]}
        for f in fc["features"] if f.get("geometry")
    ]
    return {"type": "FeatureCollection", "features": features}


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


def synthetic_facts(rng, oac_groups, loac_groups):
    imd_mode, imd_mean, imd_sd, imd_dist = decile_distribution(rng)
    ahah_mode, _, _, ahah_dist = decile_distribution(rng)
    bbs_mode, _, _, bbs_dist = decile_distribution(rng)
    return {
        "forenames": {
            "census": {"f": rng.sample(FEMALE, 10), "m": rng.sample(MALE, 10)},
            "register": {"f": rng.sample(FEMALE, 10), "m": rng.sample(MALE, 10)},
        },
        "places": {
            "census": [{"area": a, "name": n} for a, n in rng.sample(OLD_PLACES, 10)],
            "register": [{"area": a, "name": n} for a, n in rng.sample(NEW_PLACES, 10)],
        },
        "oac": {"group": rng.choice(oac_groups)},
        "loac": {"group": rng.choice(loac_groups)},
        "iuc": {"group": rng.randint(1, 10)},
        "eee": {"group": rng.randint(1, 9)},
        "imd": {"mode": imd_mode, "mean": imd_mean, "sd": imd_sd, "distribution": imd_dist},
        "ahah": {"mode": ahah_mode, "distribution": ahah_dist},
        "bbs": {"mode": bbs_mode, "distribution": bbs_dist},
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
    period_source = {p["id"]: p["source"] for p in PERIODS}

    # Scotland outline, geometry only
    scotland = json.loads((KDE_DIR / "sc" / "scotland" / "scotland_0.json").read_text(encoding="utf-8"))
    mask = {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": f["geometry"]}
                         for f in scotland["features"]]}
    write_json(OUT / "masks" / "scotland.json", mask)

    # one bundle per surname that has KDE files locally
    shards = {}
    sizes = {}
    for name_dir in sorted(p for p in KDE_DIR.glob("*/*") if p.is_dir() and p.parent.name != "sc"):
        name = name_dir.name
        maps = {}
        for period in PERIODS:
            file = name_dir / f"{name}_{period['id']}.json"
            if file.exists():
                maps[period["id"]] = read_map(file)
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
            "facts": synthetic_facts(rng, oac_groups, loac_groups),
        }
        path = OUT / "names" / name[:2] / f"{name}.json"
        raw = write_json(path, bundle)
        gz = len(zlib.compress(path.read_bytes(), 6))
        sizes[name] = (raw, gz, len(maps))
        shards.setdefault(name[:2], []).append(name)

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
