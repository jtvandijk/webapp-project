#!/usr/bin/env python3
"""Make gb_outline_lonlat.geojson: a rough coastline in longitude/latitude for pipeline/preview_web.py to draw under
a name's maps, so a blob can be seen to be where it is. Not used for the maps themselves (those are clipped to
gb_outline.geojson): this one is simplified to 2 km, rounded to 2 decimals, and leaves out islands under 150 km2, since
a preview panel is about 100 pixels tall and cannot show them anyway. That keeps it a few tens of KB, and it is read
with nothing but Python's own json module, which is the point of preview_web.py needing no shapely or pyproj.

This is a one-off job: the result is stored in the repository, so you only run it to change the outline.

    python3 pipeline/reference/make_preview_outline.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline import config, kde                                # noqa: E402

TOLERANCE_M = 2000
MIN_AREA_KM2 = 150
DECIMALS = 2


def main():
    doc = json.loads((config.REFERENCE / "gb_outline.geojson").read_text())
    land = shape(doc["features"][0]["geometry"])
    parts = list(land.geoms) if hasattr(land, "geoms") else [land]
    kept = [p.simplify(TOLERANCE_M) for p in parts if p.area >= MIN_AREA_KM2 * 1e6]
    rings = []
    for part in kept:
        if part.is_empty:
            continue
        lonlat = shapely.transform(part, lambda c: np.column_stack(kde._to_lonlat.transform(c[:, 0], c[:, 1])))
        lonlat = shapely.set_precision(lonlat, 10.0 ** -DECIMALS)
        polygons = [lonlat] if lonlat.geom_type == "Polygon" else list(lonlat.geoms)
        rings += [[[round(x, DECIMALS), round(y, DECIMALS)] for x, y in polygon.exterior.coords] for polygon in polygons if not polygon.is_empty]
    out = config.REFERENCE / "gb_outline_lonlat.geojson"
    out.write_text(json.dumps({"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {}, "geometry": {"type": "MultiPolygon", "coordinates": [[ring] for ring in rings]}}]},
        separators=(",", ":")))
    print(f"{len(rings)} pieces, {sum(len(r) for r in rings):,} points, {out.stat().st_size / 1024:.0f} KB -> {out}")


if __name__ == "__main__":
    main()
