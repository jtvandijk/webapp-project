#!/usr/bin/env python3
"""Make an outline file in pipeline/reference/ from a shapefile.

Two are used: gb_outline.geojson (the coast, maps are clipped to it so that outlines do not spill
into the sea) and scotland_outline.geojson (used to judge the 1911 maps, see pipeline/rules.py).
This is a one-off job: the results are stored in the repository, so you only run it to change an outline.

Needs the extra package `pyshp` (pip install pyshp) on top of pipeline/requirements.txt.

    python3 pipeline/reference/make_outline.py path/to/gb_small.shp gb_outline.geojson
    python3 pipeline/reference/make_outline.py path/to/sct.shp scotland_outline.geojson

The shapefile must be in British National Grid (EPSG:27700), metres. The output is in the same
grid, simplified to 500 m and snapped to a 1 m grid, which is finer than the 1 km grid the maps are computed on.
"""
import json
import sys
from pathlib import Path

import shapefile                      # pyshp
import shapely
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union

TOLERANCE_M = 500


def polygons_only(geometry):
    """make_valid can return a mix of shapes; keep just the polygons."""
    if geometry.geom_type in ("Polygon", "MultiPolygon"):
        return geometry
    return unary_union([g for g in geometry.geoms if g.geom_type in ("Polygon", "MultiPolygon")])


def main(path, output):
    reader = shapefile.Reader(path)
    polygons = []
    for shp in reader.shapes():
        parts = list(shp.parts) + [len(shp.points)]
        rings = [shp.points[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]
        polygons.extend(Polygon(r) for r in rings if len(r) >= 4)
    # in a shapefile, outer rings run clockwise and holes anti-clockwise; the outline has no
    # holes we care about, so a union of all rings that are not inside another one is enough
    geometry = unary_union([p.buffer(0) for p in polygons])
    geometry = polygons_only(shapely.make_valid(geometry))         # repair small faults in the source
    geometry = polygons_only(shapely.make_valid(geometry.simplify(TOLERANCE_M, preserve_topology=True)))
    geometry = shapely.set_precision(geometry, 1.0)                # whole metres, and stays valid

    def rounded(coords):
        return [[round(x), round(y)] for x, y in coords]

    def clean(g):
        if g.geom_type == "Polygon":
            return {"type": "Polygon",
                    "coordinates": [rounded(g.exterior.coords)] + [rounded(i.coords) for i in g.interiors]}
        return {"type": "MultiPolygon", "coordinates": [clean(p)["coordinates"] for p in g.geoms]}

    out = Path(__file__).with_name(output)
    doc = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::27700"}},
           "features": [{"type": "Feature", "properties": {"name": Path(output).stem}, "geometry": clean(geometry)}]}
    out.write_text(json.dumps(doc, separators=(",", ":")))
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB, {geometry.geom_type}, "
          f"{sum(len(p.exterior.coords) for p in (geometry.geoms if hasattr(geometry, 'geoms') else [geometry]))} points)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
