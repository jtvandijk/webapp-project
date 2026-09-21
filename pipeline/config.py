"""
Settings for the GBNames pipeline. This is the ONLY file you normally need to edit.

How to use it
-------------
* Test run on fake data:   change nothing (PROFILE = "fake"). See pipeline/README.md.
* Real run in the TRE:     fill in the "tre" block below (search for FILL_IN), then run

                               export GBNAMES_PROFILE=tre

                           before starting a stage.

Passwords are never written in here. Postgres reads them from the usual places
(~/.pgpass or the PGPASSWORD environment variable).
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"                                   # everything the pipeline writes (git-ignored)
REFERENCE = Path(__file__).resolve().parent / "reference"

PROFILE = os.environ.get("GBNAMES_PROFILE", "fake")


# ---------------------------------------------------------------------------
# 1. WHERE THE DATA LIVES  (fill in the "tre" block)
# ---------------------------------------------------------------------------
#
# Every table is written as  schema.table.  The column names are those of YOUR tables.
#
# REGISTER: one row per person at an address, with a postcode and the years first and last seen.
#   - "key" is the register column that says where the person lived (the postcode, written in the
#     standardised way: lower case, no spaces, like "ab123cd").
#   - The register has no coordinates, so they come from a postcode lookup table (the ONS Postcode
#     Directory, ONSPD): "address_table", the column that holds the standardised postcode
#     ("address_key", called stdpcd in the old scripts), and its easting and northing columns "x" and "y".
#       * The postcodes in both tables must be written the same way. Stage 1 reports how many register
#         rows find a postcode in the lookup, so a mismatch shows up straight away.
#       * Postcodes without a grid reference (ONSPD gives 0) are left out.
#       * A postcode that is missing from the lookup is left out, so use the newest ONSPD you have:
#         postcodes made after it will not be found.
#       * The lookup must have ONE row per postcode, otherwise people are counted twice. Stage 1
#         checks this and stops if it is not so.
#       * x and y must be British National Grid metres (EPSG:27700), not latitude and longitude.
#       * If the coordinates are already in the register table, set "address_table" to None and give
#         the x and y column names of the register table.
#   - "extra_where": optional extra condition, written with the aliases  r  (register) and
#     a  (lookup). We map Great Britain only, so the country codes of England, Scotland and Wales
#     are listed (Northern Ireland, the Isle of Man and the Channel Islands are left out).
#
# CENSUS: the old layout, one table per census year plus an "_att" table, and a parish table with
#   the parish centroid. "{year}" and "{boundaries}" are filled in by the pipeline
#   (see CENSUS_PARISH_BOUNDARIES).

_CENSUS_COLUMNS = {
    "surname": "sname_clean_stand", "forename": "pname",       # in the census table
    "recid": "recid", "source": "source",                      # join keys between table and _att
    "parish": "gid", "sex": "sex",                             # in the _att table
    "parish_id": "conparid", "x": "x", "y": "y",               # in the parish table (x, y = centroid)
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
            "extra_where": "a.ctry IN ('E92000001', 'S92000003', 'W92000004')",
        },
        "census": dict(_CENSUS_COLUMNS, table="gb{year}", att_table="gb{year}_att",
                       parish_table="conpar{boundaries}"),
    },
    "tre": {
        "backend": "postgres",
        "connection": {"host": "FILL_IN", "port": 5432, "dbname": "FILL_IN", "user": "FILL_IN"},
        "register": {
            "table": "registers_linked.lcr_consol2026", "surname": "surname", "forename": "forename",
            "key": "postcode", "first": "first", "last": "last",
            # ONSPD. The names below are GUESSES, taken from the old scripts and the standard ONSPD
            # column names (stdpcd, oseast1m, osnrth1m, ctry). Check them against your table.
            "address_table": "registers_lookup.onspd_2023_feb", "address_key": "stdpcd",
            "x": "oseast1m", "y": "osnrth1m",
            "extra_where": "a.ctry IN ('E92000001', 'S92000003', 'W92000004')",
        },
        # these names are copied from the old database scripts; check the parish table still holds
        "census": dict(_CENSUS_COLUMNS, table="census.gb{year}", att_table="census.gb{year}_att",
                       parish_table="spatial.conpar{boundaries}"),
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
    "register": [2000, 2005, 2010, 2015, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
}
PERIODS = [{"id": str(year), "year": year, "source": source}
           for source in ("census", "register") for year in MAP_YEARS[source]]

# Census parishes come in two boundary versions; each census year uses one of them.
# 1921 is assumed to work like 1901 (to be checked once the 1921 data is in).
CENSUS_PARISH_BOUNDARIES = {1851: 1851, 1861: 1851, 1881: 1851, 1891: 1851,
                            1901: 1901, 1911: 1901, 1921: 1901}


# ---------------------------------------------------------------------------
# 3. COUNTING AND DISCLOSURE
# ---------------------------------------------------------------------------

THRESHOLD = 100        # a map is only made for a name and year with at least this many bearers (rows)
COUNT_FLOOR = 10       # counts below this are not kept at all (small numbers are not published)

# Counts are first made per spelling (SMITH, Smith, smith) and merged afterwards, and only THEN is
# COUNT_FLOOR applied. Leaving out rare spellings already in the database query is faster but
# undercounts names that are spread over many spellings, so 1 (= exact) is the safe setting.
SQL_PREFILTER = 1


# ---------------------------------------------------------------------------
# 4. THE MAP CALCULATION
# ---------------------------------------------------------------------------

# The grid every map is calculated on: 1 km cells over Great Britain, British National Grid.
# (The same window the old pipeline used.)
GRID = {"x0": -19693, "y0": -15372, "cell": 1000, "nx": 696, "ny": 1254}

# How far each bearer's "influence" is spread on the map (the bandwidth), in metres. It grows with
# the number of bearers: BANDWIDTH_MIN_M for a name with BANDWIDTH_N[0] bearers, rising steadily to
# BANDWIDTH_MAX_M for BANDWIDTH_N[1] or more (see pipeline/kde.py). The lower limit also stops maps
# of small names from following individual streets.
BANDWIDTH_MIN_M = 8000
BANDWIDTH_MAX_M = 18000
BANDWIDTH_N = (100, 100000)

# Population weighting: how much the number of people living in an area is taken into account.
#     value = density of the name  /  (density of everybody) ** WEIGHT_POWER
#   0    plain density: the biggest cities always show, whatever the name
#   1    fully relative: shows only where the name is over-represented
#   0.5  in between: "a bit relative"
# Areas with fewer than WEIGHT_FLOOR people per km2 are treated as having that many, so that a
# handful of people in an empty area cannot dominate the map.
WEIGHT_POWER = 0.5
WEIGHT_FLOOR = 50
POPULATION_BANDWIDTH_M = 10000     # smoothing of the "everybody" surface

# The three map levels. Level 1 is the outermost (lightest), level 3 the innermost (darkest).
#   "mass": each level is the smallest area that holds this share of the name's (weighted) density.
#           A widespread name gets large areas, a local name small ones, and every name gets all three.
#   "peak": each level starts at this share of the name's own highest value.
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

# The 1911 census data has no Scotland. For a name that lived largely in Scotland, a 1911 map would
# show only its English part and look as if the name had moved south. So the 1911 map is left out
# when more than SCOTLAND_MAX_SHARE of the name's bearers were in Scotland in the reference year (a
# census that does include Scotland). See pipeline/rules.py.
SCOTLAND_MISSING_YEARS = [1911]
SCOTLAND_REFERENCE_YEAR = 1901
SCOTLAND_MAX_SHARE = 0.25
