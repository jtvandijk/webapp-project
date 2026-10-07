#!/usr/bin/env python3
"""Turn the raw neighbourhood downloads (raw-indicators/) into the lookup tables for the TRE.

Usage:   python3 tools/prep_neighbourhood.py
         python3 tools/prep_neighbourhood.py --raw raw-indicators --out work/neighbourhood

Needs pandas and openpyxl (pip install pandas openpyxl). Run it on a laptop, not in the TRE. All of the
data is public except the financial precarity classification and the GB2C gambling classification (see
below). Upload the eight CSVs in the output folder; manifest.json records what went in (file checksums)
and what came out (rows per country).

SAFEGUARDED DATA: the lookup from area to group of the financial precarity classification (fpc) and of
the GB2C gambling classification (gb2c) may not be published (both classifications' published names and
descriptions are not safeguarded). Their downloads (raw-indicators/fpc/, raw-indicators/gb2c/) and their
tables (nbhd_fpc.csv, nbhd_gb2c.csv) must stay out of the repository: they are covered by .gitignore,
twice, and nothing in the code, tests or docs may contain their area-level values.

One table per product, each keyed on `area_code`, so a new version of one product replaces one
table and nothing else. Great Britain only (Northern Ireland is dropped) - except nbhd_oac and
nbhd_count, which keep Northern Ireland: the 2021/2 UK OAC genuinely classifies it (real 2021 NISRA
census data, not a modelled stand-in), so dropping it would make the OAC population-share baseline a
Great Britain number wearing a UK label. Every other product (LOAC, AHAH, IMD, FPC, GB2C, and the
LSOA-level population count below) stays Great Britain/London only, as it always has (confirmed
2026-10-07).

  nbhd_oac    UK OAC 2021/22   output area: 2021 (England, Wales), 2022 (Scotland), 2021 (Northern
              Ireland, NISRA Small Area, code prefix N20 - same shape as an output area, different name)
  nbhd_loac   London OAC 2021  output area 2021, London only
  nbhd_ahah   AHAH v5.1        LSOA 2021 (England, Wales), data zone 2022 (Scotland)
  nbhd_imd    deprivation      LSOA 2021 (England IoD 2025, Wales WIMD 2025), data zone 2011 (Scotland SIMD 2020v2)
  nbhd_fpc    financial precarity classification (SAFEGUARDED): LSOA 2021, data zone 2022 (Scotland); 5 clusters, 13 groups
  nbhd_gb2c   GB2C gambling classification (SAFEGUARDED): LSOA 2021, data zone 2022 (Scotland); 11 groups (the area's
              modal Active Subgroup) - inside 3 groups (BG, B, G), not stored, derivable from the group code's own prefix
  nbhd_count  2021/22 Census population (GeoDS Unified UK Census Data), output area: 2021 (England, Wales), 2022
              (Scotland), 2021 (Northern Ireland). Not safeguarded. Population baseline for the OAC/LOAC bar
              charts - OAC's own share is UK-wide; LOAC only ever looks up its own (always London) codes.
  nbhd_count_lsoa  the same population, summed to LSOA 2021 / data zone 2022, Great Britain only (drops
              Northern Ireland again - GB2C/FPC/AHAH/IMD are Great Britain products). Not safeguarded.
              Population baseline for the GB2C/FPC/AHAH/IMD bar charts.

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
UK = {**GB, "N": "Northern Ireland"}  # nbhd_oac/nbhd_count only - see the module docstring

INPUTS = {
    "oac": "oac21/uk_oac_final.csv",
    "loac": "loac21/loac_groups.csv",
    "ahah": "ahah/ahah_v5_1.csv",
    "imd_england": "imd/File_1_IoD2025_Index_of_Multiple_Deprivation.xlsx",
    "imd_wales": "imd/welsh-index-of-multiple-deprivation-wimd-2025-index-and-domain-ranks-and-groups-for-lower-layer-super-output-areas-lsoa-v7-en-gb.csv",
    "imd_scotland": "imd/SIMD+2020v2+-+ranks.xlsx",
    "fpc": "fpc/fpc_finalv2.csv",
    "fpc_labels": "fpc/fpc_label_colors.csv",
    "gb2c": "gb2c/lsoa21dz22-gb2c-v1.2.csv",
    "gb2c_labels": "gb2c/classification_codes_and_names.csv",
    "census_population": "census/csv/uk001.csv",
    "oa_lsoa_ew": "geography/oa21_lsoa21_ew.csv",
    "oa_dz_scotland": "geography/oa22_dz22_scotland.csv",
}

# Written into manifest.json so the geography and the direction of each scale travel with the tables.
NOTES = {
    "nbhd_oac": "UK OAC 2021/22. area_code is an output area: 2021 for England and Wales, 2022 for Scotland (ONSPD oa21cd), "
                "2021 for Northern Ireland (NISRA Small Area, code prefix N20). The only table here that keeps Northern "
                "Ireland, so the OAC population-share baseline is a genuine UK share.",
    "nbhd_loac": "London OAC 2021, London output areas only (ONSPD oa21cd).",
    "nbhd_ahah": "AHAH v5.1. area_code is a 2021 LSOA (England, Wales) or 2022 data zone (Scotland) (ONSPD lsoa21cd). "
                 "DIRECTION: rank 1 and decile 1 = healthiest, decile 10 = least healthy.",
    "nbhd_imd": "England IoD 2025 and Wales WIMD 2025 on 2021 LSOAs (ONSPD lsoa21cd); Scotland SIMD 2020v2 on 2011 data zones "
                "(ONSPD lsoa11cd). Ranked within each country, then treated as comparable. "
                "DIRECTION: rank 1, decile 1 and percentile 1 = most deprived.",
    "nbhd_fpc": "SAFEGUARDED - never publish this lookup. Financial precarity classification. area_code is a 2021 LSOA (England, Wales) "
                "or 2022 data zone (Scotland) (ONSPD lsoa21cd), as for AHAH. fpc_cluster is one of 5 clusters (A to E) and "
                "fpc_group one of 13 groups (A01 to E13) inside them. Categories: no order is claimed.",
    "nbhd_gb2c": "SAFEGUARDED - never publish this lookup. GB2C gambling classification. area_code is a 2021 LSOA (England, Wales) "
                 "or 2022 data zone (Scotland) (ONSPD lsoa21cd), as for AHAH/FPC. gb2c_group is the area's modal (most common) "
                 "Active Subgroup, one of 11 codes (BG1-BG6, B1-B2, G1-G3) inside 3 groups (BG, B, G - the group is the code's "
                 "own prefix, not a separate column). Categories: no order is claimed.",
    "nbhd_count": "2021/22 Census usual resident population, per output area (2021 England/Wales, 2022 Scotland, 2021 Northern "
                  "Ireland, ONSPD oa21cd / NISRA Small Area) - GeoDS's own Unified UK Census Data (data.geods.ac.uk), table "
                  "uk001, variable uk001001. Not safeguarded - a public, openly-licensed count. Population baseline for "
                  "OAC/LOAC bars (OAC's own share is UK-wide; LOAC only ever looks up its own, always-London codes).",
    "nbhd_count_lsoa": "The same population, summed to its parent LSOA (England/Wales) or data zone (Scotland), via public ONS "
                       "(OA21->LSOA21) and NRS (OA22->DZ22) hierarchy lookups - Great Britain only (drops Northern Ireland "
                       "again, unlike nbhd_count). Not safeguarded, no group/classification data involved, geography only. "
                       "Population baseline for GB2C/FPC/AHAH/IMD bars.",
}

OA_RE = re.compile(r"^([EWS]00|N20)\d{6}$")  # N20... is Northern Ireland's Small Area code (nbhd_oac/nbhd_count)
ZONE_RE = re.compile(r"^[EWS]01\d{6}$")  # LSOAs and data zones


def ceil_share(rank, n, parts):
    """1..parts: which equal slice of the ranking a rank falls in (rank 1 of n is always slice 1)."""
    return -(-rank * parts // n)


def find_column(df, start):
    hits = [c for c in df.columns if c.startswith(start)]
    if len(hits) != 1:
        sys.exit(f"expected exactly one column starting {start!r}, found {hits}")
    return hits[0]


def by_country(codes, countries=GB):
    return codes.str[0].map(countries).value_counts().reindex(countries.values()).fillna(0).astype(int).to_dict()


# ---------------------------------------------------------------------------
# The four products
# ---------------------------------------------------------------------------

def prep_oac(raw, problems):
    df = pd.read_csv(raw / INPUTS["oac"], dtype=str)
    df = df[df["GeographyCode"].str[0].isin(UK)]  # keeps Northern Ireland - see the module docstring
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


def prep_count(raw, problems):
    """Output-area population, for the OAC/LOAC bar baselines. uk001001/002/003 = total / in households /
    in communal establishments (checked: 002 + 003 == 001 for every row); only the total is kept. Keeps
    Northern Ireland, unlike every other product here, so OAC's population-share baseline is a genuine
    UK share; prep_count_lsoa() below drops Northern Ireland again for the Great Britain-only products."""
    df = pd.read_csv(raw / INPUTS["census_population"], dtype=str)
    df = df[df["OA"].str[0].isin(UK)]  # keeps Northern Ireland - see the module docstring
    out = pd.DataFrame({"area_code": df["OA"], "population": df["uk001001"].astype(int)})
    if not out.area_code.str.match(OA_RE).all():
        problems.append("count: some area codes are not output area codes")
    if out.area_code.duplicated().any():
        problems.append("count: duplicate area codes")
    if out.isna().any().any():
        problems.append("count: empty cells")
    if (out.population < 0).any():
        problems.append("count: negative population")
    households = pd.to_numeric(df["uk001002"]) + pd.to_numeric(df["uk001003"])
    if not (households.to_numpy() == out.population.to_numpy()).all():
        problems.append("count: uk001002 + uk001003 does not equal uk001001 for every area (table structure changed?)")
    return out.sort_values("area_code")


def prep_count_lsoa(raw, count, problems):
    """prep_count()'s output-area population, summed up to its parent LSOA (England, Wales) or data
    zone (Scotland) - the geography GB2C/FPC/AHAH/IMD actually use. The census file itself has no
    parent-area column, so this uses separate public ONS (OA21->LSOA21, England/Wales) and NRS
    (OA22->DZ22, Scotland) lookups just for the hierarchy, not for any population figure. Great
    Britain only: drops Northern Ireland again, since prep_count() (unusually) kept it and GB2C/FPC/
    AHAH/IMD are Great Britain products, not UK ones."""
    count = count[count.area_code.str[0].isin(GB)]
    ew = pd.read_csv(raw / INPUTS["oa_lsoa_ew"], dtype=str)[["OA21CD", "LSOA21CD"]]
    ew = ew.rename(columns={"OA21CD": "area_code", "LSOA21CD": "parent"})
    sc = pd.read_csv(raw / INPUTS["oa_dz_scotland"], dtype=str)[["OA22", "DZ22"]]
    sc = sc.rename(columns={"OA22": "area_code", "DZ22": "parent"})
    crosswalk = pd.concat([ew, sc], ignore_index=True)

    if crosswalk.area_code.duplicated().any():
        problems.append("count_lsoa: duplicate output areas in the OA->LSOA/data zone crosswalk")
    missing = ~count.area_code.isin(crosswalk.area_code)
    if missing.any():
        problems.append(f"count_lsoa: {missing.sum()} output areas in nbhd_count have no parent LSOA/data zone")
    extra = ~crosswalk.area_code.isin(count.area_code)
    if extra.any():
        problems.append(f"count_lsoa: {extra.sum()} crosswalk rows are for output areas not in nbhd_count "
                        "(Northern Ireland leaking in?)")

    merged = count.merge(crosswalk, on="area_code", how="inner")
    out = merged.groupby("parent", as_index=False).population.sum().rename(columns={"parent": "area_code"})
    if not out.area_code.str.match(ZONE_RE).all():
        problems.append("count_lsoa: some parent codes are not LSOA / data zone codes")
    if out.population.sum() != count.population.sum():
        problems.append("count_lsoa: total population changed during aggregation (an area was dropped or "
                        "double-counted)")
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


def prep_gb2c(raw, ahah, problems, notes):
    df = pd.read_csv(raw / INPUTS["gb2c"], dtype=str, encoding="utf-8-sig")
    labels = pd.read_csv(raw / INPUTS["gb2c_labels"], dtype=str, encoding="utf-8-sig")
    out = pd.DataFrame({"area_code": df["lsoa21cd"], "gb2c_group": df["modal_name"]})
    if not out.area_code.str.match(ZONE_RE).all():
        problems.append("gb2c: some area codes are not LSOA / data zone codes")
    if out.area_code.duplicated().any():
        problems.append("gb2c: duplicate area codes")
    if out.isna().any().any() or (out.apply(lambda c: c.str.strip() == "")).any().any():
        problems.append("gb2c: empty cells")
    known = set(labels[(labels["Level"] == "Subgroup") & (labels["Classification Code"] != "-")]["Classification Code"])
    if set(out.gb2c_group) != known:
        problems.append(f"gb2c: the groups in the data and in the label file differ (only in data: {sorted(set(out.gb2c_group) - known)}, "
                        f"only in labels: {sorted(known - set(out.gb2c_group))})")
    notes.append(f"gb2c: {out.gb2c_group.nunique()} groups; same areas as AHAH: {set(out.area_code) == set(ahah.area_code)}")
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
    count = prep_count(args.raw, problems)
    tables = {
        "nbhd_oac": oac,
        "nbhd_loac": prep_loac(args.raw, oac, problems),
        "nbhd_ahah": ahah,
        "nbhd_imd": prep_imd(args.raw, problems, notes),
        "nbhd_fpc": prep_fpc(args.raw, ahah, problems, notes),
        "nbhd_gb2c": prep_gb2c(args.raw, ahah, problems, notes),
        "nbhd_count": count,
        "nbhd_count_lsoa": prep_count_lsoa(args.raw, count, problems),
    }
    for note in notes:
        print("note:", note)
    if problems:  # write nothing, so a bad run cannot leave plausible-looking tables behind
        print("\n".join(f"PROBLEM {p}" for p in problems))
        return 1

    inputs_used = {
        "nbhd_oac": ["oac"], "nbhd_loac": ["loac", "oac"], "nbhd_ahah": ["ahah"],
        "nbhd_imd": ["imd_england", "imd_wales", "imd_scotland"], "nbhd_fpc": ["fpc", "fpc_labels"],
        "nbhd_gb2c": ["gb2c", "gb2c_labels"], "nbhd_count": ["census_population"],
        "nbhd_count_lsoa": ["census_population", "oa_lsoa_ew", "oa_dz_scotland"],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, df in tables.items():
        path = args.out / f"{name}.csv"
        df.to_csv(path, index=False, lineterminator="\n")
        countries = UK if name in ("nbhd_oac", "nbhd_count") else GB  # only these two keep Northern Ireland
        manifest[name] = {"file": path.name, "notes": NOTES[name], "rows": len(df), "columns": list(df.columns),
                          "by_country": by_country(df.area_code, countries), "sha256": sha256(path),
                          "inputs": {INPUTS[i]: sha256(args.raw / INPUTS[i]) for i in inputs_used[name]}}
        print(f"{name:10} {len(df):>8,} rows   {manifest[name]['by_country']}")
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"ok, written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
