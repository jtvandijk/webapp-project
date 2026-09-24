"""
Settings for the GBNames pipeline. Edit this file, not the others.

  Fake data (default):  python3 -m pipeline.fake_data, then run any stage as normal.
  Real run in the TRE:  the register+ONSPD and the census+parish tables live in two different
                         databases, each with its own full set of connection variables (see
                         PG_ENV_SUFFIX and "tre" below): PGHOST_LCR/PGPORT_LCR/PGDATABASE_LCR/
                         PGUSER_LCR/PGPASSWORD_LCR for the register (LCR = linked consumer
                         register), and the same with _ICEM for the census (I-CeM). Set them (e.g.
                         source an env file; export the two passwords separately), then export
                         GBNAMES_PROFILE=tre.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"                                   # everything the pipeline writes (git-ignored)
REFERENCE = Path(__file__).resolve().parent / "reference"

PROFILE = os.environ.get("GBNAMES_PROFILE", "fake")

# The choices that change from run to run (which database(s), how many names, how many chunks) live in the file
# run.settings in the project folder, which is read by every qsub script and sourced by you, like .env (which holds the
# passwords and stays out of git). They arrive here as GBNAMES_* environment variables, and every stage uses them as
# the default for its matching flag, so a typed command and a qsub job cannot disagree; a flag still overrides them.
# Nothing set means: both sources, 200 chunks, every name, every fact, every census year.
ALL_CENSUS_YEARS = [1851, 1861, 1881, 1891, 1901, 1911, 1921]      # 1871 is not available


def read_run_settings(env):
    """The run settings from an environment (run.settings, once sourced), with their defaults, checked. A typo
    stops the run with a message that names the setting, instead of quietly doing something else."""
    def bad(name, why):
        raise SystemExit(f"run.settings: GBNAMES_{name} {why}")

    sources = env.get("GBNAMES_SOURCES", "register census").split()
    if not sources or any(s not in ("register", "census") for s in sources):
        bad("SOURCES", f'is "{env.get("GBNAMES_SOURCES")}"; use register, census or "register census"')
    try:
        chunks = int(env.get("GBNAMES_CHUNKS", "200") or 200)
        if chunks < 1:
            raise ValueError
    except ValueError:
        bad("CHUNKS", f'is "{env.get("GBNAMES_CHUNKS")}"; use a whole number, 1 or more')
    limit = (env.get("GBNAMES_LIMIT") or "").strip()
    try:
        limit = int(limit) if limit else None
        if limit is not None and limit < 1:
            raise ValueError
    except ValueError:
        bad("LIMIT", f'is "{env.get("GBNAMES_LIMIT")}"; use a whole number, or leave it empty for every name')
    try:
        years = [int(y) for y in env.get("GBNAMES_CENSUS_YEARS", "").split()] or list(ALL_CENSUS_YEARS)
    except ValueError:
        bad("CENSUS_YEARS", f'is "{env.get("GBNAMES_CENSUS_YEARS")}"; use census years separated by spaces')
    if any(y not in ALL_CENSUS_YEARS for y in years):
        bad("CENSUS_YEARS", f"has a year that is not a census year we have ({' '.join(map(str, ALL_CENSUS_YEARS))})")
    return {"sources": sources, "chunks": chunks, "limit": limit, "facts": env.get("GBNAMES_FACTS", "").split() or None,
            "census_years": sorted(set(years)), "sources_were_set": "GBNAMES_SOURCES" in env}


RUN = read_run_settings(os.environ)
RUN_SOURCES, RUN_CHUNKS, RUN_LIMIT, RUN_FACTS = RUN["sources"], RUN["chunks"], RUN["limit"], RUN["facts"]


def describe_run():
    """One line for the top of a stage's output: which settings it is running with."""
    return (f"run settings: sources {' '.join(RUN_SOURCES)}; chunks {RUN_CHUNKS}; "
            f"names {'the first ' + str(RUN_LIMIT) if RUN_LIMIT else 'all'}; facts {' '.join(RUN_FACTS) if RUN_FACTS else 'all'}"
            f"{'; census years ' + ' '.join(map(str, RUN['census_years'])) if 'census' in RUN_SOURCES else ''}"
            " (from run.settings; a flag overrides)")

# Which environment variable suffix belongs to which database group: PGHOST_LCR, PGDATABASE_ICEM,
# and so on (see pg_env() below). Used by both this file and pipeline/db.py (for the password).
PG_ENV_SUFFIX = {"register": "LCR", "census": "ICEM"}


def pg_env(group, field, default=None):
    """One Postgres setting for one database group, e.g. pg_env("census", "host") reads PGHOST_ICEM."""
    return os.environ.get(f"PG{field.upper()}_{PG_ENV_SUFFIX[group]}", default)


# ---------------------------------------------------------------------------
# 1. WHERE THE DATA LIVES
# ---------------------------------------------------------------------------
# schema.table and column names for your tables. "{year}"/"{boundaries}" are filled in per census
# year automatically (see CENSUS_PARISH_BOUNDARIES).
#
# register: needs a postcode lookup (ONSPD) for coordinates, unless the register has its own x/y.
#   - postcodes must be written the same way in both tables
#   - lookup rows with no grid reference (0) or missing from the file are left out - expected, fine
#   - lookup must have one row per postcode (stage 1 checks this)
#   - x/y must be British National Grid metres, not latitude/longitude
#   - extra_where: an extra SQL condition (aliases r = register, a = lookup); used here for GB only
#
# census: one table per year, an "_att" table, and a parish table holding the parish centroid (x, y)

_CENSUS_COLUMNS = {
    "forename": "pname",                                        # census table ("surname" set per profile below)
    "recid": "recid", "source": "source",                      # join keys, census <-> _att
    "parish": "gid", "sex": "sex",                              # _att table (parish: not in 1921, see CENSUS_PARISH_COLUMN)
    "parish_id": "conparid", "x": "x", "y": "y",                # parish table (centroid)
    "parish_name": "parish", "county": "regcnty",
}

PROFILES = {
    "fake": {
        "backend": "sqlite",
        "database": str(WORK / "fake.db"),
        "register": {
            "table": "register", "surname": "surname", "forename": "forename",
            "key": "postcode", "first": "first", "last": "last",
            "address_table": "postcode_lookup", "address_key": "postcode", "x": "easting", "y": "northing",
            "extra_where": "a.ctry IN ('E92000001', 'S92000003', 'W92000004')",  # England, Scotland, Wales
            # the neighbourhood codes in the lookup (stage 5): logical name -> column
            "areas": {"oa": "oa21cd", "lsoa": "lsoa21cd", "lsoa_2011": "lsoa11cd", "msoa": "msoa21cd",
                      "district": "lad25cd", "country": "ctry"},
        },
        "census": dict(_CENSUS_COLUMNS, surname="sname_clean_stand", table="gb{year}", att_table="gb{year}_att",
                       parish_table="conpar{boundaries}"),
        # stage 5 (facts): the neighbourhood tables, the forename -> gender table, and the register
        # with the ethnicity estimate attached (in the fake data that is just the register itself)
        "facts": {
            "tables": {"oac": "nbhd_oac", "loac": "nbhd_loac", "ahah": "nbhd_ahah", "imd": "nbhd_imd", "fpc": "nbhd_fpc"},
            "gender": {"table": "forename_gender", "name": "forename", "gender": "gender"},
            "ethest": {"table": "register", "surname": "surname", "key": "postcode", "first": "first",
                       "last": "last", "eth": "eth"},
        },
    },
    "tre": {
        "backend": "postgres",
        # Two databases, each fully self-contained (no falling back to the other's settings, so
        # each variable belongs to exactly one database - see PG_ENV_SUFFIX above). "register" also
        # serves ONSPD (they are in the same database). The two PGPASSWORD_* variables are read
        # directly by pipeline/db.py and never stored here.
        "connections": {
            "register": {"host": pg_env("register", "host"), "port": int(pg_env("register", "port", 5432)),
                        "dbname": pg_env("register", "database"), "user": pg_env("register", "user")},
            "census": {"host": pg_env("census", "host"), "port": int(pg_env("census", "port", 5432)),
                      "dbname": pg_env("census", "database"), "user": pg_env("census", "user")},
        },
        "register": {
            "table": "registers_linked.lcr_consol2026", "surname": "surname", "forename": "forename",
            "key": "postcode", "first": "first", "last": "last",
            "address_table": "registers_lookup.onspd_2026_feb", "address_key": "stdpcd",
            "x": "east1m", "y": "north1m",  # 2026 ONSPD: renamed from the usual oseast1m/osnrth1m
            "extra_where": "a.ctry25cd IN ('E92000001', 'S92000003', 'W92000004')",  # England, Scotland, Wales; ctry -> ctry25cd in the 2026 ONSPD
            # the neighbourhood codes in ONSPD (stage 5); confirmed to exist in the TRE copy
            "areas": {"oa": "oa21cd", "lsoa": "lsoa21cd", "lsoa_2011": "lsoa11cd", "msoa": "msoa21cd",
                      "district": "lad25cd", "country": "ctry25cd"},
        },
        # "surname": "sname_clean_stand" is the surname as cleaned by the old project's SQL function (leading initials,
        # bracketed text and everything after " or " removed, junk names emptied); names.surname_key() is then applied to it,
        # as for the register. Every census table needs the column; the TRE's backup lacks it, so tools/sql/make_sname_clean_stand.sh makes it for every year.
        # The surname index (how-to, "The census surname") has to be made on this column.
        "census": dict(_CENSUS_COLUMNS, surname="sname_clean_stand", table="census.gb{year}", att_table="census.gb{year}_att",
                       # spatial.conpar1851 and spatial.conpar1901: conparid, geom, centroid, x, y (centroid, British
                       # National Grid metres), regcnty, parish - as given by the data owner; stage 1 checks the join
                       parish_table="spatial.conpar{boundaries}"),
        # stage 5 (facts). check: the schema the neighbourhood tables are uploaded into (registers_lookup
        # is a guess, next to ONSPD; see  python3 -m pipeline.nbhd_tables ddl), the columns of lookup_monica
        # (name, gender: as the old monica_gender, not yet confirmed), and that lcr_consol_ethest has the
        # same columns as lcr_consol2026 plus `eth` (only `eth` is confirmed).
        "facts": {
            "tables": {"oac": "registers_lookup.nbhd_oac", "loac": "registers_lookup.nbhd_loac",
                       "ahah": "registers_lookup.nbhd_ahah", "imd": "registers_lookup.nbhd_imd",
                       "fpc": "registers_lookup.nbhd_fpc"},
            "gender": {"table": "registers_lookup.lookup_monica", "name": "name", "gender": "gender"},
            "ethest": {"table": "registers_derived.lcr_consol_ethest", "surname": "surname", "key": "postcode",
                       "first": "first", "last": "last", "eth": "eth"},
        },
    },
}


def settings(profile=None):
    """The settings block for the chosen profile."""
    return PROFILES[profile or PROFILE]


# ---------------------------------------------------------------------------
# 2. YEARS
# ---------------------------------------------------------------------------

CENSUS_YEARS = RUN["census_years"]                             # 1871 is not available; run.settings can leave a year out
REGISTER_YEARS = list(range(1997, 2027))                       # every year we count (2026 is a part year)

# The years that get a map (the slider positions on the website).
MAP_YEARS = {
    "census": CENSUS_YEARS,
    "register": [1997, 2000, 2005, 2010, 2015, 2020, 2025, 2026],
}
PERIODS = [{"id": str(year), "year": year, "source": source}
           for source in ("census", "register") for year in MAP_YEARS[source]]

# Census parishes come in two boundary versions; each census year uses one. 1921 uses the 1901 one too.
CENSUS_PARISH_BOUNDARIES = {1851: 1851, 1861: 1851, 1881: 1851, 1891: 1851,
                            1901: 1901, 1911: 1901, 1921: 1901}

# The column of gb<year>_att that holds the parish id: "gid" (the original ids, cleaned up by the data owner) - except in
# 1921. The ids recorded for 1921 do not link to the standardised parishes, so its records were assigned to the 1901
# parishes by point in polygon, and that result is the column conparid1901. Any year not listed uses the profile's column.
CENSUS_PARISH_COLUMN = {1921: "conparid1901"}

# How gid was made from the ids the census files carry (the note pg_conpar_dic.txt, applied to the 1851 and 1901 numberings):
# five ids that are in no parish list are moved to a neighbouring parish, and Scotland in the 1901 numbering has 100,000
# added (200001-200853 became 300001-300853) so that it lines up with the 1901 geometries. Only the parish check reads these,
# to say so when an attributes column still holds the old ids.
CONPAR_ID_FIXES = {1903: 1891, 6598: 6596, 7283: 7289, 12412: 12414, 12413: 12414}
SCOTLAND_1901_SHIFT = 100000


# ---------------------------------------------------------------------------
# 3. COUNTING AND DISCLOSURE
# ---------------------------------------------------------------------------

# Minimum bearers before a map is made, per source, and (s1_counts.py) before a period counts
# towards a name getting a page at all. Census data is over 100 years old and treated as no
# disclosure risk, so this floor is only to keep the map itself meaningful, not for privacy -
# register's is the standard disclosure floor. Both are 100: on real data, a 30-bearer census map
# looked too thin/noisy to be worth showing (2026-09-23), so census was raised to match register
# rather than keep a separate, lower "meaningful" floor that turned out not to be. A name's OTHER
# years still show their raw count once it has a page (COUNT_FLOOR below is the much lower floor
# for that) - this floor only decides map/page eligibility, not whether a count is ever recorded.
THRESHOLD = {"census": 100, "register": 100}

COUNT_FLOOR = 10       # counts below this are not kept at all, in either source

# Counts are made per spelling first (SMITH, Smith, smith) and merged afterwards; only then is
# COUNT_FLOOR applied. 1 (= exact) is the safe setting; a higher number would undercount names
# spread over many spellings.
SQL_PREFILTER = 1


# ---------------------------------------------------------------------------
# 4. THE MAP CALCULATION
# ---------------------------------------------------------------------------

# The grid every map is calculated on: 1 km cells over Great Britain, British National Grid.
GRID = {"x0": -19693, "y0": -15372, "cell": 1000, "nx": 696, "ny": 1254}

# Bandwidth (metres): how far each bearer's "influence" spreads. Grows with the number of bearers,
# from BANDWIDTH_MIN_M at BANDWIDTH_N[0] bearers to BANDWIDTH_MAX_M at BANDWIDTH_N[1] or more (see
# pipeline/kde.py). The lower limit also stops small names from tracing individual streets.
BANDWIDTH_MIN_M = 8000
BANDWIDTH_MAX_M = 18000
BANDWIDTH_N = (100, 100000)

# Population weighting:  value = density of the name / (density of everybody) ** WEIGHT_POWER
#   0 = plain density (the biggest cities always show)   1 = fully relative (share of the population)
#   0.5 = a bit relative, the current setting
# WEIGHT_FLOOR: areas with fewer people per km2 than this are treated as having that many, so a
# handful of people in an empty area cannot dominate the map.
# WEIGHT_CEILING and POPULATION_BANDWIDTH_M together fix a real problem found and confirmed on real
# data (2026-09-23): a big name's own bandwidth can be much wider than the population surface's, so
# right on an extremely dense exact city centre, the population surface still had a sharp local peak
# that the name's own, more smoothed-out surface did not - dividing by that peak created a dip
# exactly there, which looked like a ring or a "C" shape around the city instead of a filled-in
# area. WEIGHT_CEILING caps the population used in the division itself (not the underlying data);
# POPULATION_BANDWIDTH_M (widened from 10,000 to 15,000, closer to a big name's own bandwidth)
# fixes the mismatch directly - confirmed together on real data to remove the ring/"C" shape
# artefact across every city size tried, from London down to smaller ones (Birmingham, Cheltenham,
# Nottingham) that WEIGHT_CEILING alone had not fully caught.
WEIGHT_POWER = 0.5
WEIGHT_FLOOR = 50
WEIGHT_CEILING = 8000
POPULATION_BANDWIDTH_M = 15000     # smoothing of the "everybody" surface - see above

# A separate blob (not connected to any other) is dropped if it holds less than this share of the
# name's total (weighted) density - a handful of people on their own somewhere, not a real
# concentration. This is not the same problem as MIN_AREA_KM2 below: at these bandwidths even one
# person's own smoothed "bump" can cover well over 100 km2, so a small number of people can easily
# pass an area test; what marks them as not worth showing is how little of the name's total they
# represent, not their physical size. Only helps a name with a large enough total for "a few people"
# to genuinely be a small share of it - see MIN_BLOB_BEARERS for names too small for that (measured
# cost: about 2% of one map's calculation time even for a very widespread name, not a real cost at
# scale). Tested on synthetic data only so far, not real names - a starting point, not settled.
MIN_BLOB_SHARE = 0.02

# A separate blob is ALSO dropped if its own actual (unweighted) bearer count is below this many
# people, whatever share of the name's total that is - complements MIN_BLOB_SHARE above rather than
# replacing it: for a name with only a few hundred bearers in total (Van Dijk, Lansley), "1-2 people
# on their own" is never a small enough SHARE of the total for MIN_BLOB_SHARE to catch (confirmed on
# real data, 2026-09-23 - the "separate areas" count barely moved between 0.02 and 0.10), but it is
# always a small absolute COUNT, which this checks directly instead. An unvalidated starting guess.
MIN_BLOB_BEARERS = 5

# The three map levels, level 1 outermost (lightest) to level 3 innermost (darkest).
#   "mass": each level is the smallest area holding this share of the name's (weighted) density -
#           a widespread name gets large areas, a local name small ones, both get all three levels
#   "peak": each level starts at this share of the name's own highest value
LEVEL_MODE = "mass"
LEVEL_MASS = (0.85, 0.65, 0.40)
LEVEL_PEAK = (0.10, 0.25, 0.45)

# Tidying of the outlines (metres and square kilometres)
# SMOOTH_M widened from 5,000 to 10,000 on 2026-09-23, matching the old pipeline's equivalent step
# (data-prep/py/fn_prerender.py used the same 10,000) - confirmed on real data to read as more
# solid/concentric, closer to how the old maps looked, without reintroducing the old pipeline's
# other issues.
SMOOTH_M = 10000           # fills gaps and notches narrower than 2x this
SIMPLIFY_M = 400           # fewer points, smaller files
MIN_AREA_KM2 = 25          # blobs and holes smaller than this are dropped


# ---------------------------------------------------------------------------
# 5. CENSUS YEARS WITHOUT SCOTLAND
# ---------------------------------------------------------------------------

# 1911 and 1921 have no data for Scotland. A Scottish name still has plenty of bearers in England,
# so a map built straight from that year's own data would just show the English part and look like
# the name had moved south. Instead, for a name with more than SCOTLAND_MAX_SHARE of its bearers in
# Scotland in SCOTLAND_REFERENCE_YEAR (a census that does have Scotland), we reuse that year's map
# instead of building a new one - so a heavily Scottish name shows the same 1901 map for 1901, 1911
# and 1921. See pipeline/rules.py.
SCOTLAND_MISSING_YEARS = [1911, 1921]
SCOTLAND_REFERENCE_YEAR = 1901
SCOTLAND_MAX_SHARE = 0.30


# ---------------------------------------------------------------------------
# 6. THE FACTS ABOUT EACH NAME (stage 5)
# ---------------------------------------------------------------------------

# Contemporary facts (neighbourhood classifications, top neighbourhoods, ethnicity) are worked out
# in each name's REFERENCE YEAR: the latest register year in which it has at least THRESHOLD["register"]
# bearers (from counts.csv, stage 1). Forenames are the exception: pooled over every register year.
# A fact is only reported when the category it reports (the most common group, decile or census group)
# has at least FACT_MIN_IN_CATEGORY bearers, so nothing is ever said about fewer people than that. The
# 100-bearer floor applies to the name as a whole, through the reference year above, not to each fact. This
# is a disclosure floor, not a statistical one: a fact that few bearers have a value for (LOAC covers London
# only; some bearers have no ethnicity code) can rest on few people, and n_bearers in the output says how many.
FACT_MIN_IN_CATEGORY = 5

# The same minimum applies to everything that is listed: a neighbourhood, a parish or a forename needs at least
# FACT_MIN_IN_CATEGORY people (5) to appear. (The historic census is over 100 years old and needs no disclosure
# floor, but the same one keeps the two sources alike and the lists free of one-off oddities.)
PLACES_TOP = 10                           # top neighbourhoods (MSOA or Scottish intermediate zone) and top parishes listed
FORENAMES_TOP = 10                        # top forenames per sex listed
FORENAMES_KEEP = 25                       # the database keeps this many per surname and sex before the merge
                                          # of spelling variants, which bounds what has to be fetched. A forename
                                          # outside a variant's top 25 cannot count towards the merged list, which
                                          # only matters for near-ties at the edge of the top ten
PARISHES_KEEP = 25                        # the same bound for parishes: the database keeps this many per surname and census
                                          # year before the years are pooled and spelling variants merged
SHARE_DECIMALS = 3                        # shares in the distributions; use 2 if the output checkers want less

COUNTRY_SCOTLAND = "S92000003"            # Scottish deprivation is on 2011 data zones, the rest on 2021 areas

# What version each fact is, written next to it in the output so a new version can sit alongside.
FACT_VERSIONS = {
    "oac": "UK OAC 2021/22", "loac": "London OAC 2021", "ahah": "AHAH v5.1",
    "imd": "IoD2025 / WIMD2025 / SIMD2020v2", "imd_score": "IoD2025 / WIMD2025 / SIMD2020v2",
    "fpc": "Financial Precarity Classification",
    "places": "MSOA 2021 / Scottish IZ 2022", "ethnicity": "Ethnicity Estimator",
    "forenames_register": "register 1997-2026",
    "forenames_census": "census {first}-{last}", "parishes": "consistent parishes, census {first}-{last}",   # the years actually pooled
}

# The neighbourhood tables (made by tools/prep_neighbourhood.py), loaded into the TRE with
# `python3 -m pipeline.nbhd_tables ddl`. Column -> SQL type; area_code is the primary key.
NBHD_TABLE_COLUMNS = {
    "oac": [("area_code", "text"), ("oac_supergroup", "text"), ("oac_group", "text"), ("oac_subgroup", "text")],
    "loac": [("area_code", "text"), ("loac_supergroup", "text"), ("loac_group", "text")],
    "ahah": [("area_code", "text"), ("ahah_score", "numeric"), ("ahah_rank", "integer"),
             ("ahah_pctile", "integer"), ("ahah_decile", "integer")],
    "imd": [("area_code", "text"), ("imd_country", "text"), ("imd_source", "text"), ("imd_rank", "integer"),
            ("imd_areas", "integer"), ("imd_pctile", "integer"), ("imd_decile", "integer")],
    # SAFEGUARDED data: the financial precarity classification's lookup from area to group. The table goes into
    # the TRE, but its area-level values may not appear anywhere in this repository (code, tests, docs). The
    # classification's published names are not safeguarded.
    "fpc": [("area_code", "text"), ("fpc_cluster", "text"), ("fpc_group", "text")],
}

# Which facts are counted from the register, and how. "key" is the postcode-directory column (a
# logical name from each profile's register "areas") that the table's area_code joins to. Deprivation
# is different for Scotland, whose ranking is on the 2011 data zones (scotland_key).
#   values: what the counts are grouped by (table columns, or directory columns when there is no table)
#   sums:   columns to add up as well, to get a mean and a spread later
FACT_QUERIES = {
    "oac": {"table": "oac", "key": "oa", "values": ["oac_group"]},
    "loac": {"table": "loac", "key": "oa", "values": ["loac_group"]},
    "ahah": {"table": "ahah", "key": "lsoa", "values": ["ahah_decile"]},
    "imd": {"table": "imd", "key": "lsoa", "scotland_key": "lsoa_2011", "values": ["imd_decile"],
            "sums": ["imd_pctile"]},
    "fpc": {"table": "fpc", "key": "lsoa", "values": ["fpc_group"]},
    "places": {"areas": ["msoa", "district"]},
    "eth": {},                                    # from the register with the ethnicity estimate, see sql.py
}

# The Ethnicity Estimator codes start with a census group (WAO-DE = White other, Germany). Only the
# group is used for now, but the distribution over the codes is kept for later. A code whose start is
# not in this list is left out of the counts and listed in the report.
ETH_GROUPS = {
    "WBR": "White - British", "WIR": "White - Irish", "WAO": "White - Other",
    "BAF": "Black - African", "BCA": "Black - Caribbean",
    "AIN": "Asian - Indian", "APK": "Asian - Pakistani", "ABD": "Asian - Bangladeshi",
    "ACN": "Asian - Chinese", "AAO": "Asian - Other",
    "OXX": "Other ethnic group",
}
ETH_UNKNOWN = "unknown"                # shown when too few bearers have a usable code
