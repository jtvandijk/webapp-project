"""
Settings for the GBNames pipeline. Edit this file, not the others.

  Fake data (default):  python3 -m pipeline.fake_data, then run any stage as normal.
  Real run in the TRE:  the register+ONSPD and the census+parish tables live in two different
                         databases, so there are two sets of connection variables (see "tre" below
                         and pipeline/db.py). Set them (e.g. source an env file), export PGPASSWORD
                         and CENSUS_PGPASSWORD separately, then export GBNAMES_PROFILE=tre.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"                                   # everything the pipeline writes (git-ignored)
REFERENCE = Path(__file__).resolve().parent / "reference"

PROFILE = os.environ.get("GBNAMES_PROFILE", "fake")


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
    "surname": "sname_clean_stand", "forename": "pname",       # census table
    "recid": "recid", "source": "source",                      # join keys, census <-> _att
    "parish": "gid", "sex": "sex",                              # _att table
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
        },
        "census": dict(_CENSUS_COLUMNS, table="gb{year}", att_table="gb{year}_att",
                       parish_table="conpar{boundaries}"),
    },
    "tre": {
        "backend": "postgres",
        # Two databases. "register" also serves ONSPD (they are in the same database). "census"
        # falls back to the register host/port/user if its own are not set - set CENSUS_PGDATABASE
        # at least, since that always differs. PGPASSWORD/CENSUS_PGPASSWORD are read directly by
        # pipeline/db.py and never stored here.
        "connections": {
            "register": {"host": os.environ.get("PGHOST"), "port": int(os.environ.get("PGPORT", 5432)),
                        "dbname": os.environ.get("PGDATABASE"), "user": os.environ.get("PGUSER")},
            "census": {"host": os.environ.get("CENSUS_PGHOST", os.environ.get("PGHOST")),
                      "port": int(os.environ.get("CENSUS_PGPORT", os.environ.get("PGPORT", 5432))),
                      "dbname": os.environ.get("CENSUS_PGDATABASE"),
                      "user": os.environ.get("CENSUS_PGUSER", os.environ.get("PGUSER"))},
        },
        "register": {
            "table": "registers_linked.lcr_consol2026", "surname": "surname", "forename": "forename",
            "key": "postcode", "first": "first", "last": "last",
            "address_table": "registers_lookup.onspd_2026_feb", "address_key": "stdpcd",
            "x": "east1m", "y": "north1m",  # 2026 ONSPD: renamed from the usual oseast1m/osnrth1m
            "extra_where": "a.ctry25cd IN ('E92000001', 'S92000003', 'W92000004')",  # England, Scotland, Wales; ctry -> ctry25cd in the 2026 ONSPD
        },
        "census": dict(_CENSUS_COLUMNS, table="census.gb{year}", att_table="census.gb{year}_att",
                       parish_table="spatial.conpar{boundaries}"),  # check: guessed from the old scripts
    },
}


def settings(profile=None):
    """The settings block for the chosen profile."""
    return PROFILES[profile or PROFILE]


# ---------------------------------------------------------------------------
# 2. YEARS
# ---------------------------------------------------------------------------

CENSUS_YEARS = [1851, 1861, 1881, 1891, 1901, 1911, 1921]      # 1871 is not available
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


# ---------------------------------------------------------------------------
# 3. COUNTING AND DISCLOSURE
# ---------------------------------------------------------------------------

# Minimum bearers before a map is made, per source. Census data is over 100 years old and treated
# as no disclosure risk, so its floor (30) is only to keep the map itself meaningful; register data
# uses the standard 100.
THRESHOLD = {"census": 30, "register": 100}

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
WEIGHT_POWER = 0.5
WEIGHT_FLOOR = 50
POPULATION_BANDWIDTH_M = 10000     # smoothing of the "everybody" surface

# The three map levels, level 1 outermost (lightest) to level 3 innermost (darkest).
#   "mass": each level is the smallest area holding this share of the name's (weighted) density -
#           a widespread name gets large areas, a local name small ones, both get all three levels
#   "peak": each level starts at this share of the name's own highest value
LEVEL_MODE = "mass"
LEVEL_MASS = (0.85, 0.65, 0.40)
LEVEL_PEAK = (0.10, 0.25, 0.45)

# Tidying of the outlines (metres and square kilometres)
SMOOTH_M = 5000            # fills narrow gaps and notches
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
