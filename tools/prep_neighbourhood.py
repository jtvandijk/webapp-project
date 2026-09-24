#!/usr/bin/env python3
"""Turn the raw neighbourhood downloads (raw-indicators/) into the lookup tables for the TRE.

Usage:   python3 tools/prep_neighbourhood.py
         python3 tools/prep_neighbourhood.py --raw raw-indicators --out work/neighbourhood

Needs pandas and openpyxl (pip install pandas openpyxl). Run it on a laptop, not in the TRE. All of the
data is public except the financial precarity classification (see below). Upload the five CSVs in the output folder; manifest.json records what
went in (file checksums) and what came out (rows per country).

SAFEGUARDED DATA: the financial precarity classification (fpc) may not be published. Its download
(raw-indicators/fpc/) and its table (nbhd_fpc.csv) must stay out of the repository: they are covered by
.gitignore, twice, and nothing in the code, tests or docs may contain its area-level values.

One table per product, each keyed on `area_code`, so a new version of one product replaces one
table and nothing else. Great Britain only (Northern Ireland is dropped).

  nbhd_oac    UK OAC 2021/22   output area: 2021 (England, Wales), 2022 (Scotland)
  nbhd_loac   London OAC 2021  output area 2021, London only
  nbhd_ahah   AHAH v5.1        LSOA 2021 (England, Wales), data zone 2022 (Scotland)
  nbhd_imd    deprivation      LSOA 2021 (England IoD 2025, Wales WIMD 2025), data zone 2011 (Scotland SIMD 2020v2)
  nbhd_fpc    financial precarity classification (SAFEGUARDED): LSOA 2021, data zone 2022 (Scotland); 5 clusters, 13 groups

Deprivation: each country is ranked on its own (rank 1 = most deprived) and given deciles and
percentiles from that rank, then the three countries are treated as comparable. They are not
strictly comparable; this is the agreed simple comparison. AHAH is one Great Britain ranking, so
its deciles need no such step, and it runs the other way: 1 = healthiest, 10 = least healthy.

The checks at the end stop the script (exit code 1) if a file is not what it should be, e.g. ranks
with gaps (an incomplete download), codes of the wrong shape, or a group that does not belong to
its supergroup.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

GB = {"E": "England", "W": "Wales", "S": "Scotland"}  # Northern Ireland is left out

INPUTS = {
    "oac": "oac21/uk_oac_final.csv",
    "loac": "loac21/loac_groups.csv",
    "ahah": "ahah/ahah_v5_1.csv",
    "imd_england": "imd/File_1_IoD2025_Index_of_Multiple_Deprivation.xlsx",
    "imd_wales": "imd/welsh-index-of-multiple-deprivation-wimd-2025-index-and-domain-ranks-and-groups-for-lower-layer-super-output-areas-lsoa-v7-en-gb.csv",
    "imd_scotland": "imd/SIMD+2020v2+-+ranks.xlsx",
    "fpc": "fpc/fpc_finalv2.csv",
    "fpc_labels": "fpc/fpc_label_colors.csv",
}

# Written into manifest.json so the geography and the direction of each scale travel with the tables.
NOTES = {
    "nbhd_oac": "UK OAC 2021/22. area_code is an output area: 2021 for England and Wales, 2022 for Scotland (ONSPD oa21cd).",
    "nbhd_loac": "London OAC 2021, London output areas only (ONSPD oa21cd).",
    "nbhd_ahah": "AHAH v5.1. area_code is a 2021 LSOA (England, Wales) or 2022 data zone (Scotland) (ONSPD lsoa21cd). "
                 "DIRECTION: rank 1 and decile 1 = healthiest, decile 10 = least healthy.",
    "nbhd_imd": "England IoD 2025 and Wales WIMD 2025 on 2021 LSOAs (ONSPD lsoa21cd); Scotland SIMD 2020v2 on 2011 data zones "
                "(ONSPD lsoa11cd). Ranked within each country, then treated as comparable. "
                "DIRECTION: rank 1, decile 1 and percentile 1 = most deprived.",
    "nbhd_fpc": "SAFEGUARDED - never publish. Financial precarity classification v2. area_code is a 2021 LSOA (England, Wales) "
                "or 2022 data zone (Scotland) (ONSPD lsoa21cd), as for AHAH. fpc_cluster is one of 5 clusters (A to E) and "
                "fpc_group one of 13 groups (A01 to E13) inside them. Categories: no order is claimed.",
}

OA_RE = re.compile(r"^[EWS]00\d{6}$")
ZONE_RE = re.compile(r"^[EWS]01\d{6}$")  # LSOAs and data zones


def ceil_share(rank, n, parts):
    """1..parts: which equal slice of the ranking a rank falls in (rank 1 of n is always slice 1)."""
    return -(-rank * parts // n)


def find_column(df, start):
    hits = [c for c in df.columns if c.startswith(start)]
    if len(hits) != 1:
        sys.exit(f"expected exactly one column starting {start!r}, found {hits}")
    return hits[0]


def by_country(codes):
    return codes.str[0].map(GB).value_counts().reindex(GB.values()).fillna(0).astype(int).to_dict()


# ---------------------------------------------------------------------------
# The four products
# ---------------------------------------------------------------------------

def prep_oac(raw, problems):
    df = pd.read_csv(raw / INPUTS["oac"], dtype=str)
    df = df[df["GeographyCode"].str[0].isin(GB)]  # drops Northern Ireland
    out = pd.DataFrame({"area_code": df["GeographyCode"], "oac_supergroup": df["Supergroup"],
                        "oac_group": df["Group"], "oac_subgroup": df["Subgroup"]})
    if not out.area_code.str.match(OA_RE).all():
        problems.append("oac: some area codes are not output area codes")
    if out.area_code.duplicated().any():
        problems.append("oac: duplicate area codes")
    if out.isna().any().any():
        problems.append("oac: empty cells")
    if not (out.oac_group.str[0] == out.oac_supergroup).all():
        problems.append("oac: a group does not start with its supergroup number")
    if not (out.oac_subgroup.str[:2] == out.oac_group).all():
        problems.append("oac: a subgroup does not start with its group")
    return out.sort_values("area_code")


def prep_loac(raw, oac, problems):
    df = pd.read_csv(raw / INPUTS["loac"], dtype=str)
    out = pd.DataFrame({"area_code": df["OA"], "loac_supergroup": df["SG"], "loac_group": df["G"]})
    if not out.area_code.str.match(OA_RE).all():
        problems.append("loac: some area codes are not output area codes")
    if out.area_code.duplicated().any():
        problems.append("loac: duplicate area codes")
    if not (out.loac_group.str[0] == out.loac_supergroup).all():
        problems.append("loac: a group does not start with its supergroup letter")
    # London only: every area should also be in UK OAC, and in a London borough (E09...)
    lad = pd.read_csv(raw / INPUTS["oac"], dtype=str).set_index("GeographyCode")["LAD25Code"]
    missing = ~out.area_code.isin(lad.index)
    if missing.any():
        problems.append(f"loac: {missing.sum()} areas are not in the UK OAC file")
    outside = ~lad.reindex(out.area_code).fillna("").str.startswith("E09").to_numpy()
    if outside.any():
        problems.append(f"loac: {outside.sum()} areas are outside London boroughs")
    return out.sort_values("area_code")


def prep_ahah(raw, problems):
    df = pd.read_csv(raw / INPUTS["ahah"])
    n = len(df)
    out = pd.DataFrame({"area_code": df["lsoa21cd"], "ahah_score": df["ahah"].round(3),
                        "ahah_rank": df["ahah_rnk"], "ahah_pctile": df["ahah_pct"],
                        "ahah_decile": ceil_share(df["ahah_rnk"], n, 10)})
    if not out.area_code.str.match(ZONE_RE).all():
        problems.append("ahah: some area codes are not LSOA / data zone codes")
    if out.area_code.duplicated().any():
        problems.append("ahah: duplicate area codes")
    if sorted(out.ahah_rank) != list(range(1, n + 1)):
        problems.append("ahah: ranks are not exactly 1..N (incomplete or changed file?)")
    if out.isna().any().any():
        problems.append("ahah: empty cells")
    # published percentile and our decile must tell the same story (percentile 1-10 = decile 1)
    if ((out.ahah_pctile + 9) // 10 - out.ahah_decile).abs().max() > 1:
        problems.append("ahah: published percentile and computed decile disagree by more than one step")
    return out.sort_values("area_code")


def prep_fpc(raw, ahah, problems, notes):
    df = pd.read_csv(raw / INPUTS["fpc"], dtype=str, encoding="utf-8-sig")
    labels = pd.read_csv(raw / INPUTS["fpc_labels"], dtype=str, encoding="utf-8-sig")
    out = pd.DataFrame({"area_code": df["lsoa21cd"], "fpc_cluster": df["cluster"], "fpc_group": df["label"]})
    if not out.area_code.str.match(ZONE_RE).all():
        problems.append("fpc: some area codes are not LSOA / data zone codes")
    if out.area_code.duplicated().any():
        problems.append("fpc: duplicate area codes")
    if out.isna().any().any() or (out.apply(lambda c: c.str.strip() == "")).any().any():
        problems.append("fpc: empty cells")
    if not out.fpc_cluster.isin(list("ABCDE")).all():
        problems.append("fpc: a cluster is not one of A to E")
    if not (out.fpc_group.str[0] == out.fpc_cluster).all():
        problems.append("fpc: a group does not start with its cluster letter")
    known = set(labels.iloc[:, 0])
    if set(out.fpc_group) != known:
        problems.append(f"fpc: the groups in the data and in the label file differ (only in data: {sorted(set(out.fpc_group) - known)}, "
                        f"only in labels: {sorted(known - set(out.fpc_group))})")
    notes.append(f"fpc: {out.fpc_group.nunique()} groups in {out.fpc_cluster.nunique()} clusters; "
                 f"same areas as AHAH: {set(out.area_code) == set(ahah.area_code)}")
    return out.sort_values("area_code")


def read_england(raw):
    df = pd.read_excel(raw / INPUTS["imd_england"], sheet_name="IMD25")
    code = find_column(df, "LSOA code")
    rank = find_column(df, "Index of Multiple Deprivation (IMD) Rank")
    decile = find_column(df, "Index of Multiple Deprivation (IMD) Decile")
    return df[code], df[rank], df[decile]


def read_wales(raw):
    # Long format, numbers stored as text with thousands commas and padding, and local authority
    # rows (W06...) mixed in with the LSOAs (W01...).
    df = pd.read_csv(raw / INPUTS["imd_wales"], dtype=str)
    df = df[df["Area code"].str.match(r"^W01\d{6}$", na=False) & (df["Domain"] == "WIMD")]

    def values(kind):
        part = df[df["Data description"] == kind].set_index("Area code")["Data values"]
        return pd.to_numeric(part.str.replace(",", "").str.strip(), errors="coerce")

    rank = values("Rank")
    return rank.index.to_series(), rank, values("Decile").reindex(rank.index)


def read_scotland(raw):
    df = pd.read_excel(raw / INPUTS["imd_scotland"], sheet_name="SIMD 2020v2 ranks")
    return df["Data_Zone"], df["SIMD2020v2_Rank"], None  # SIMD's ranks file has no deciles


def prep_imd(raw, problems, notes):
    frames = []
    for country, source, reader in (("England", "IoD2025", read_england), ("Wales", "WIMD2025", read_wales),
                                    ("Scotland", "SIMD2020v2", read_scotland)):
        code, rank, published = reader(raw)
        n = len(rank)
        if rank.isna().any() or sorted(rank.astype(int)) != list(range(1, n + 1)):
            problems.append(f"imd {country}: ranks are not exactly 1..N (incomplete or changed file?)")
            continue
        df = pd.DataFrame({"area_code": code.to_numpy(), "imd_country": country, "imd_source": source,
                           "imd_rank": rank.astype(int).to_numpy(), "imd_areas": n})
        df["imd_pctile"] = ceil_share(df.imd_rank, n, 100)
        df["imd_decile"] = ceil_share(df.imd_rank, n, 10)
        if not df.area_code.str.match(ZONE_RE).all() or not (df.area_code.str[0] == country[0]).all():
            problems.append(f"imd {country}: area codes are not {country} LSOA / data zone codes")
        if df.area_code.duplicated().any():
            problems.append(f"imd {country}: duplicate area codes")
        if published is not None:
            differ = int((published.to_numpy() != df.imd_decile.to_numpy()).sum())
            notes.append(f"imd {country}: {differ:,} of {n:,} computed deciles differ from the published ones")
        frames.append(df)
    return pd.concat(frames).sort_values("area_code")


# ---------------------------------------------------------------------------

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", type=Path, default=ROOT / "raw-indicators", help="folder with the downloads")
    parser.add_argument("--out", type=Path, default=ROOT / "work" / "neighbourhood", help="where the lookup tables go")
    args = parser.parse_args()

    for name, rel in INPUTS.items():
        if not (args.raw / rel).exists():
            sys.exit(f"missing input {name}: {args.raw / rel}")

    problems, notes = [], []
    oac = prep_oac(args.raw, problems)
    ahah = prep_ahah(args.raw, problems)
    tables = {
        "nbhd_oac": oac,
        "nbhd_loac": prep_loac(args.raw, oac, problems),
        "nbhd_ahah": ahah,
        "nbhd_imd": prep_imd(args.raw, problems, notes),
        "nbhd_fpc": prep_fpc(args.raw, ahah, problems, notes),
    }
    for note in notes:
        print("note:", note)
    if problems:  # write nothing, so a bad run cannot leave plausible-looking tables behind
        print("\n".join(f"PROBLEM {p}" for p in problems))
        return 1

    inputs_used = {
        "nbhd_oac": ["oac"], "nbhd_loac": ["loac", "oac"], "nbhd_ahah": ["ahah"],
        "nbhd_imd": ["imd_england", "imd_wales", "imd_scotland"], "nbhd_fpc": ["fpc", "fpc_labels"],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, df in tables.items():
        path = args.out / f"{name}.csv"
        df.to_csv(path, index=False, lineterminator="\n")
        manifest[name] = {"file": path.name, "notes": NOTES[name], "rows": len(df), "columns": list(df.columns),
                          "by_country": by_country(df.area_code), "sha256": sha256(path),
                          "inputs": {INPUTS[i]: sha256(args.raw / INPUTS[i]) for i in inputs_used[name]}}
        print(f"{name:10} {len(df):>8,} rows   {manifest[name]['by_country']}")
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"ok, written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
