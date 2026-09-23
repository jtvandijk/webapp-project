"""The database queries, built from the names in config.py.

All the rules about WHICH rows count live here, once, so that the counts (stage 1) and the maps
(later stages) can never disagree about who is included:

  register:  a person counts in year Y when first <= Y <= last, and the postcode has coordinates
             (and passes the extra condition in config.py, for example Great Britain only).
  census:    a person counts when their parish is found in the parish boundaries that belong to that
             census year (and the parish id is not 0).

The queries only use plain SQL that works in both SQLite (the fake data) and Postgres (the TRE).
"""
from . import config


# ---------------------------------------------------------------------------
# pieces
# ---------------------------------------------------------------------------

def _register(cfg):
    """(join to the postcode lookup, x expression, y expression, WHERE conditions) for the register."""
    r = cfg["register"]
    if r.get("address_table"):
        join = f'JOIN {r["address_table"]} a ON a.{r["address_key"]} = r.{r["key"]}'
        x, y = f'a.{r["x"]}', f'a.{r["y"]}'
    else:
        join, x, y = "", f'r.{r["x"]}', f'r.{r["y"]}'
    where = f"{x} > 0 AND {y} > 0"                      # not missing, and not the 0 that ONSPD uses for "no grid reference"
    if r.get("extra_where"):
        where += f' AND ({r["extra_where"]})'
    return join, x, y, where


def _census(cfg, year):
    """(census table, att table, parish table, columns) for one census year."""
    c = cfg["census"]
    boundaries = config.CENSUS_PARISH_BOUNDARIES[year]
    return (c["table"].format(year=year), c["att_table"].format(year=year),
            c["parish_table"].format(boundaries=boundaries), c)


def _cell(cfg, expr, origin):
    """The number of the 1 km grid cell that a coordinate falls in."""
    g = config.GRID
    inner = f"(({expr}) - ({origin})) / {g['cell']}.0"
    if cfg["backend"] == "postgres":
        return f"CAST(FLOOR({inner}) AS INTEGER)"
    return f"CAST({inner} AS INTEGER)"          # SQLite: fine here, coordinates are inside the grid


def _inside_grid(x, y):
    g = config.GRID
    return (f"{x} >= {g['x0']} AND {x} < {g['x0'] + g['nx'] * g['cell']} "
            f"AND {y} >= {g['y0']} AND {y} < {g['y0'] + g['ny'] * g['cell']}")


# ---------------------------------------------------------------------------
# stage 1: counts
# ---------------------------------------------------------------------------

def register_counts(cfg, years):
    """Bearers per surname for every one of the years, in one query: (year, raw surname, n)."""
    r = cfg["register"]
    join, _, _, where = _register(cfg)
    values = ",".join(f"({int(y)})" for y in years)
    return f"""
WITH years(yr) AS (VALUES {values})
SELECT yr.yr, r.{r["surname"]}, COUNT(*)
FROM years yr
JOIN {r["table"]} r ON r.{r["first"]} <= yr.yr AND r.{r["last"]} >= yr.yr
{join}
WHERE {where}
GROUP BY yr.yr, r.{r["surname"]}
HAVING COUNT(*) >= {config.SQL_PREFILTER}"""


def census_counts(cfg, year):
    """Bearers per surname in one census year: (surname, n)."""
    table, att, parish, c = _census(cfg, year)
    return f"""
SELECT c.{c["surname"]}, COUNT(*)
FROM {table} c
JOIN {att} a ON a.{c["recid"]} = c.{c["recid"]} AND a.{c["source"]} = c.{c["source"]}
JOIN {parish} p ON p.{c["parish_id"]} = a.{c["parish"]}
WHERE p.{c["parish_id"]} <> 0 AND c.{c["surname"]} IS NOT NULL
GROUP BY c.{c["surname"]}
HAVING COUNT(*) >= {config.SQL_PREFILTER}"""


def register_totals(cfg, years, matched):
    """Register rows per year: (year, n). With matched=True only the rows that get usable
    coordinates, otherwise all of them. The share between the two is the postcode match rate."""
    r = cfg["register"]
    join, _, _, where = _register(cfg)
    if not matched:
        join, where = "", "1 = 1"
    values = ",".join(f"({int(y)})" for y in years)
    return f"""
WITH years(yr) AS (VALUES {values})
SELECT yr.yr, COUNT(*)
FROM years yr
JOIN {r["table"]} r ON r.{r["first"]} <= yr.yr AND r.{r["last"]} >= yr.yr
{join}
WHERE {where}
GROUP BY yr.yr"""


# ---------------------------------------------------------------------------
# later stages: bearers per grid cell
# ---------------------------------------------------------------------------

def _surname_filter(cfg, column, surnames):
    """WHERE clause fragment that narrows to a small set of standardised surname keys, e.g.
    ["smith", "longley"] - a coarse match (lower case, letters only) done in the database, cheap
    enough to use even on an unindexed 150M-row table because it runs BEFORE any grouping, not
    instead of the exact match: pipeline/names.py's surname_key() still resolves it precisely once
    the (now small) result reaches Python. It does not fold accents the way surname_key() does (a
    plain-ASCII name like "Muller" would not catch a row spelled "Müller"), which is an acceptable
    gap for previewing a chosen name, not for anything that decides what gets published.

    Only applied on Postgres. Without a `surnames` list (or on SQLite - the small fake/test data),
    the query is unfiltered, exactly as before: register_counts()/census_counts() (stage 1, which
    counts every surname on purpose) never pass one."""
    if not surnames or cfg["backend"] != "postgres":
        return ""
    keys = ",".join("'" + s.replace("'", "''") + "'" for s in surnames)
    return f" AND regexp_replace(lower({column}), '[^a-z]', '', 'g') IN ({keys})"


def register_cells(cfg, year, by_surname=True, surnames=None):
    """Bearers per 1 km cell in one year: (raw surname, cell x, cell y, n), or without the surname
    for the surface of everybody (used for the population weighting). Pass `surnames` (standardised
    keys) whenever you only want specific names - see _surname_filter() above; leaving it out scans
    and groups the whole table, fine for a handful of names on the fake data, not on the real one."""
    r, g = cfg["register"], config.GRID
    join, x, y, where = _register(cfg)
    ix, iy = _cell(cfg, x, g["x0"]), _cell(cfg, y, g["y0"])
    name, group = (f'r.{r["surname"]}, ', "1, 2, 3") if by_surname else ("", "1, 2")
    only = _surname_filter(cfg, f'r.{r["surname"]}', surnames) if by_surname else ""
    return f"""
SELECT {name}{ix}, {iy}, COUNT(*)
FROM {r["table"]} r
{join}
WHERE r.{r["first"]} <= {int(year)} AND r.{r["last"]} >= {int(year)}
  AND {where} AND {_inside_grid(x, y)}{only}
GROUP BY {group}"""


def census_cells(cfg, year, by_surname=True, surnames=None):
    """The same for a census year, using the parish centroids as the location."""
    table, att, parish, c = _census(cfg, year)
    g = config.GRID
    x, y = f'p.{c["x"]}', f'p.{c["y"]}'
    ix, iy = _cell(cfg, x, g["x0"]), _cell(cfg, y, g["y0"])
    name, group = (f'c.{c["surname"]}, ', "1, 2, 3") if by_surname else ("", "1, 2")
    only = _surname_filter(cfg, f'c.{c["surname"]}', surnames) if by_surname else ""
    return f"""
SELECT {name}{ix}, {iy}, COUNT(*)
FROM {table} c
JOIN {att} a ON a.{c["recid"]} = c.{c["recid"]} AND a.{c["source"]} = c.{c["source"]}
JOIN {parish} p ON p.{c["parish_id"]} = a.{c["parish"]}
WHERE p.{c["parish_id"]} <> 0 AND c.{c["surname"]} IS NOT NULL AND {_inside_grid(x, y)}{only}
GROUP BY {group}"""


# ---------------------------------------------------------------------------
# safety check
# ---------------------------------------------------------------------------

def duplicate_lookup_keys(cfg):
    """How many postcodes appear more than once in the lookup table. It must be 0: a postcode that
    appears twice would make everybody living there count twice. None if there is no lookup table."""
    r = cfg["register"]
    if not r.get("address_table"):
        return None
    return f"""
SELECT COUNT(*) FROM (
  SELECT {r["address_key"]} FROM {r["address_table"]}
  WHERE {r["x"]} > 0 AND {r["y"]} > 0
  GROUP BY {r["address_key"]} HAVING COUNT(*) > 1
) d"""


# ---------------------------------------------------------------------------
# stage 5: facts
# ---------------------------------------------------------------------------
# Everybody counted here is somebody the counts and maps also count: the same register rows, the same
# postcode lookup, the same Great Britain condition (_register above). The surname filter is the same
# coarse one as for the maps and only ever narrows the rows, never widens them.

def _area_key(cfg, spec):
    """The postcode-directory column that a neighbourhood table's area_code joins to. Scottish
    deprivation is on the 2011 data zones and everything else on the 2021 areas, hence the CASE."""
    areas = cfg["register"]["areas"]
    key = f"a.{areas[spec['key']]}"
    if "scotland_key" in spec:
        return (f"CASE WHEN a.{areas['country']} = '{config.COUNTRY_SCOTLAND}' "
                f"THEN a.{areas[spec['scotland_key']]} ELSE {key} END")
    return key


def _with_ethest(cfg):
    """The same settings, but with the register table swapped for the register that carries the
    ethnicity estimate (it has the same columns, plus one for the estimate)."""
    e = cfg["facts"]["ethest"]
    return dict(cfg, register=dict(cfg["register"], table=e["table"], surname=e["surname"], key=e["key"],
                                   first=e["first"], last=e["last"]))


def fact_counts(cfg, fact, year, surnames=None):
    """Bearers per surname and value, in one register year, for one of config.FACT_QUERIES:
    (raw surname, value..., n, then for each of the spec's `sums` the sum and the sum of squares).
    Only people who have a value are counted, so n is 'bearers with a value'."""
    spec = config.FACT_QUERIES[fact]
    if fact == "eth":
        cfg = _with_ethest(cfg)
    r = cfg["register"]
    areas = r["areas"]
    join, _, _, where = _register(cfg)
    lookup, sums = "", ""
    if spec.get("table"):
        lookup = f'JOIN {cfg["facts"]["tables"][spec["table"]]} t ON t.area_code = {_area_key(cfg, spec)}'
        values = [f"t.{c}" for c in spec["values"]]
        sums = "".join(f", SUM(t.{c}), SUM(t.{c} * t.{c})" for c in spec.get("sums", []))
    elif fact == "eth":
        eth = f'r.{cfg["facts"]["ethest"]["eth"]}'
        values = [f"UPPER(TRIM({eth}))"]
        where += f" AND {eth} IS NOT NULL AND TRIM({eth}) <> ''"
    else:
        columns = [f"a.{areas[name]}" for name in spec["areas"]]
        values = columns
        where += f" AND {columns[0]} IS NOT NULL AND {columns[0]} <> ''"     # a postcode without a neighbourhood
    only = _surname_filter(cfg, f'r.{r["surname"]}', surnames)
    positions = ", ".join(str(i) for i in range(1, len(values) + 2))
    return f"""
SELECT r.{r["surname"]}, {", ".join(values)}, COUNT(*){sums}
FROM {r["table"]} r
{join}
{lookup}
WHERE r.{r["first"]} <= {int(year)} AND r.{r["last"]} >= {int(year)}
  AND {where}{only}
GROUP BY {positions}"""


def forename_counts(cfg, surnames=None):
    """Forenames per surname and sex, pooled over every register year: (raw surname, sex, forename, n),
    only the FORENAMES_KEEP most common per raw surname and sex. Only forenames that are in the gender
    table are counted (the same as the old pipeline, whose other forenames had no sex to list under)."""
    r, g = cfg["register"], cfg["facts"]["gender"]
    join, _, _, where = _register(cfg)
    only = _surname_filter(cfg, f'r.{r["surname"]}', surnames)
    sex = f'UPPER(SUBSTR(TRIM(g.{g["gender"]}), 1, 1))'
    forename = f'LOWER(r.{r["forename"]})'
    return f"""
SELECT surname, sex, forename, n FROM (
  SELECT r.{r["surname"]} AS surname, {sex} AS sex, {forename} AS forename, COUNT(*) AS n,
         ROW_NUMBER() OVER (PARTITION BY r.{r["surname"]}, {sex} ORDER BY COUNT(*) DESC, {forename}) AS rk
  FROM {r["table"]} r
  {join}
  JOIN {g["table"]} g ON LOWER(g.{g["name"]}) = {forename}
  WHERE {where}{only}
  GROUP BY r.{r["surname"]}, {sex}, {forename}
) ranked
WHERE rk <= {config.FORENAMES_KEEP}"""


def postcode_lookup(cfg, postcodes):
    """What stage 5 would use for each of these (already standardised) postcodes: the codes in the
    postcode directory, whether the postcode counts at all (a grid reference, and Great Britain), and the
    row each neighbourhood table gives for it. It joins in exactly the way fact_counts() does."""
    r = cfg["register"]
    areas, tables = r["areas"], cfg["facts"]["tables"]
    _, _, _, where = _register(cfg)
    joins = "\n".join(f'LEFT JOIN {tables[k]} t_{k} ON t_{k}.area_code = {_area_key(cfg, config.FACT_QUERIES[k])}'
                      for k in ("oac", "loac", "ahah", "imd"))
    listed = ",".join("'" + p.replace("'", "''") + "'" for p in postcodes)
    return f"""
SELECT a.{r["address_key"]}, CASE WHEN {where} THEN 1 ELSE 0 END, a.{areas["country"]},
       a.{areas["oa"]}, a.{areas["lsoa"]}, a.{areas["lsoa_2011"]}, a.{areas["msoa"]}, a.{areas["district"]},
       t_oac.oac_supergroup, t_oac.oac_group, t_oac.oac_subgroup, t_loac.loac_group,
       t_ahah.ahah_rank, t_ahah.ahah_decile,
       t_imd.imd_source, t_imd.imd_rank, t_imd.imd_areas, t_imd.imd_decile, t_imd.imd_pctile
FROM {r["address_table"]} a
{joins}
WHERE a.{r["address_key"]} IN ({listed})"""


# ---------------------------------------------------------------------------
# safety checks for the neighbourhood tables and the gender table
# ---------------------------------------------------------------------------

def duplicate_gender_names(cfg):
    """How many forenames appear more than once in the gender table. It must be 0: a forename that
    appears twice would count everybody who has it twice."""
    g = cfg["facts"]["gender"]
    return f"""
SELECT COUNT(*) FROM (
  SELECT LOWER({g["name"]}) FROM {g["table"]} GROUP BY LOWER({g["name"]}) HAVING COUNT(*) > 1
) d"""


def duplicate_nbhd_keys(cfg, table):
    """How many area codes appear more than once in one neighbourhood table (must be 0)."""
    name = cfg["facts"]["tables"][table]
    return f"SELECT COUNT(*) - COUNT(DISTINCT area_code) FROM {name}"


def nbhd_coverage(cfg, year):
    """Per country, for the register rows in one year: (country, rows, then how many find a row in
    each neighbourhood table, how many are in London and how many of those find one in LOAC, and how
    many have a neighbourhood code). If a table was made for the wrong geography, or the upload is
    incomplete, it shows here as a country with a low share."""
    r = cfg["register"]
    areas, tables = r["areas"], cfg["facts"]["tables"]
    join, _, _, where = _register(cfg)
    joins = "\n".join(f'LEFT JOIN {tables[k]} t_{k} ON t_{k}.area_code = {_area_key(cfg, config.FACT_QUERIES[k])}'
                      for k in ("oac", "loac", "ahah", "imd"))
    london = f"a.{areas['district']} LIKE 'E09%'"
    return f"""
SELECT a.{areas["country"]}, COUNT(*),
       COUNT(t_oac.area_code), COUNT(t_ahah.area_code), COUNT(t_imd.area_code),
       SUM(CASE WHEN {london} THEN 1 ELSE 0 END),
       SUM(CASE WHEN {london} AND t_loac.area_code IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN a.{areas["msoa"]} IS NOT NULL AND a.{areas["msoa"]} <> '' THEN 1 ELSE 0 END)
FROM {r["table"]} r
{join}
{joins}
WHERE r.{r["first"]} <= {int(year)} AND r.{r["last"]} >= {int(year)} AND {where}
GROUP BY a.{areas["country"]}"""
