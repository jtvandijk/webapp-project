"""What happens to a name's map in each period: built fresh, copied from another year, or left out.

Two rules, applied by resolve():

  disclosure  a period needs at least THRESHOLD[source] bearers (config.py) before a map is built.

  Scotland    1911 and 1921 have no census data for Scotland (config.SCOTLAND_MISSING_YEARS). A
              Scottish name still has plenty of bearers in England, so its count that year is not
              small - a map built from it would just show the English part and look like the name
              had moved south. So instead of building one, we copy the map from a census that does
              have Scotland (1901, config.SCOTLAND_REFERENCE_YEAR), whenever more than
              SCOTLAND_MAX_SHARE of the name's bearers were there that year. A heavily Scottish name
              ends up showing the same 1901 map for 1901, 1911 and 1921. If 1901 itself has too few
              bearers to build a map, there is nothing to copy, and the year falls back to the
              ordinary disclosure check on its own count.

build_maps() applies resolve() to a set of periods and computes the maps, reusing one build for
every period that copies from it.
"""
import json
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import shapely
from shapely.geometry import shape

from . import config, kde

_scotland = None


def scotland_grid():
    """Which 1 km cells have their centre in Scotland (made once)."""
    global _scotland
    if _scotland is None:
        doc = json.loads((config.REFERENCE / "scotland_outline.geojson").read_text())
        outline = shape(doc["features"][0]["geometry"])
        shapely.prepare(outline)
        x, y = np.meshgrid(kde.XC, kde.YC)
        _scotland = shapely.contains_xy(outline, x.ravel(), y.ravel()).reshape(x.shape)
    return _scotland


def scotland_share(cells):
    """The share of a name's bearers (cells = cell x, cell y, n) who are in Scotland."""
    ix, iy, n = cells
    total = float(n.sum())
    return float(n[scotland_grid()[iy, ix]].sum()) / total if total else 0.0


@dataclass
class Resolution:
    action: str                        # "build", "substitute" or "omit"
    reason: str                        # why (for "omit" and "substitute")
    reference: Optional[str] = None    # for "substitute": the period id to copy


def resolve(period, cells_by_period):
    """What happens to one name in one period. cells_by_period: {period id: (cell x, cell y, n) or
    None} for this name, covering at least `period` and, for a Scotland year, the reference year."""
    threshold = config.THRESHOLD[period["source"]]

    if period["source"] == "census" and period["year"] in config.SCOTLAND_MISSING_YEARS:
        reference_id = str(config.SCOTLAND_REFERENCE_YEAR)
        reference = cells_by_period.get(reference_id)
        if reference is not None:
            share = scotland_share(reference)
            if share > config.SCOTLAND_MAX_SHARE and int(reference[2].sum()) >= config.THRESHOLD["census"]:
                return Resolution("substitute",
                    f"{share:.0%} of its bearers were in Scotland in {config.SCOTLAND_REFERENCE_YEAR}",
                    reference_id)
            # else: not Scottish enough, or nothing to copy - fall through to the ordinary check

    cells = cells_by_period.get(period["id"])
    total = 0 if cells is None else int(cells[2].sum())
    if total < threshold:
        return Resolution("omit", f"{total} bearers, below {threshold}")
    return Resolution("build", "")


def build_maps(periods, cells_by_period, bandwidth, pop_surfaces, land, *, power=None, mode=None, levels=None,
               min_share=None, min_bearers=None, timings=None):
    """The map for one name in every one of `periods`, applying resolve() to each.
    pop_surfaces: {period id: population surface}, covering the same periods as cells_by_period.
    timings: optional dict, filled in with the seconds each fresh build took (not "substitute" ones).
    Returns {period id: (bands or None, Resolution)} for every period in `periods`.
    Keyword-only from power on, on purpose: a positional call from preview.py silently passed its
    timings dict into the min_share slot instead (found 2026-09-23 - MIN_BLOB_SHARE was never
    actually applied all night because of it, and the timings dict was never filled in either,
    which is why every "ms" column read 0 all along). A keyword-only mismatch raises a TypeError
    immediately instead of failing silently like that again."""
    resolved = {p["id"]: resolve(p, cells_by_period) for p in periods}
    needed = {pid for pid, r in resolved.items() if r.action == "build"}
    needed |= {r.reference for r in resolved.values() if r.action == "substitute"}

    built = {}
    for pid in needed:
        cells = cells_by_period.get(pid)
        if cells is None:
            built[pid] = None
            continue
        started = time.perf_counter()
        built[pid] = kde.make_map(kde.to_grid(*cells), bandwidth, pop_surfaces[pid], land, power=power, mode=mode,
                                  levels=levels, min_share=min_share, min_bearers=min_bearers)
        if timings is not None:
            timings[pid] = time.perf_counter() - started

    out = {}
    for p in periods:
        r = resolved[p["id"]]
        bands = None if r.action == "omit" else built.get(r.reference if r.action == "substitute" else p["id"])
        out[p["id"]] = (bands, r)
    return out
