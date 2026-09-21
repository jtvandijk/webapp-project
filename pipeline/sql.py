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

def register_cells(cfg, year, by_surname=True):
    """Bearers per 1 km cell in one year: (raw surname, cell x, cell y, n), or without the surname
    for the surface of everybody (used for the population weighting)."""
    r, g = cfg["register"], config.GRID
    join, x, y, where = _register(cfg)
    ix, iy = _cell(cfg, x, g["x0"]), _cell(cfg, y, g["y0"])
    name, group = (f'r.{r["surname"]}, ', "1, 2, 3") if by_surname else ("", "1, 2")
    return f"""
SELECT {name}{ix}, {iy}, COUNT(*)
FROM {r["table"]} r
{join}
WHERE r.{r["first"]} <= {int(year)} AND r.{r["last"]} >= {int(year)}
  AND {where} AND {_inside_grid(x, y)}
GROUP BY {group}"""


def census_cells(cfg, year, by_surname=True):
    """The same for a census year, using the parish centroids as the location."""
    table, att, parish, c = _census(cfg, year)
    g = config.GRID
    x, y = f'p.{c["x"]}', f'p.{c["y"]}'
    ix, iy = _cell(cfg, x, g["x0"]), _cell(cfg, y, g["y0"])
    name, group = (f'c.{c["surname"]}, ', "1, 2, 3") if by_surname else ("", "1, 2")
    return f"""
SELECT {name}{ix}, {iy}, COUNT(*)
FROM {table} c
JOIN {att} a ON a.{c["recid"]} = c.{c["recid"]} AND a.{c["source"]} = c.{c["source"]}
JOIN {parish} p ON p.{c["parish_id"]} = a.{c["parish"]}
WHERE p.{c["parish_id"]} <> 0 AND c.{c["surname"]} IS NOT NULL AND {_inside_grid(x, y)}
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
