"""Rules about which maps are made and which are left out.

A map is left out when

  * the name has fewer than THRESHOLD bearers that year (the disclosure rule), or
  * the census year has no Scotland (1911) and the name lived largely in Scotland.

The second rule cannot use the 1911 count: a Scottish name still has many bearers in England, so
its 1911 count is high, yet a map of it would show only the English part and look as if the name
had moved south. So the rule looks at where the name lived in a census that DOES include Scotland
(1901, see config.py) and leaves the 1911 map out if more than SCOTLAND_MAX_SHARE of its bearers
were in Scotland then. It has to be decided after the fact, from another year.
"""
import json

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


def skip_reason(period, cells_by_period):
    """None if the map should be made, otherwise the reason it is left out.
    cells_by_period: {period id: (cell x, cell y, n) or None} for this name."""
    cells = cells_by_period.get(period["id"])
    total = 0 if cells is None else int(cells[2].sum())
    if total < config.THRESHOLD:
        return f"{total} bearers, below {config.THRESHOLD}"
    if period["source"] == "census" and period["year"] in config.SCOTLAND_MISSING_YEARS:
        reference = cells_by_period.get(str(config.SCOTLAND_REFERENCE_YEAR))
        if reference is not None:
            share = scotland_share(reference)
            if share > config.SCOTLAND_MAX_SHARE:
                return (f"no Scotland in {period['year']}, and {share:.0%} of its bearers "
                        f"were in Scotland in {config.SCOTLAND_REFERENCE_YEAR}")
    return None
