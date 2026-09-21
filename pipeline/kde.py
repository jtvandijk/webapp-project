"""The map calculation: from "bearers per 1 km cell" to three levels of outline.

The steps, for one surname in one year (the numbers live in config.py):

  1. put the bearers on the 1 km grid                              to_grid
  2. spread each bearer over the surroundings (a Gaussian
     "kernel density"); how far is the bandwidth, which grows
     with the number of bearers                                    choose_bandwidth, smooth
  3. divide by the local population, partly ("a bit relative"),
     so that big cities do not show for every name                 weigh
  4. cut at three levels, giving nested areas                      level_cutoffs, nested_regions
  5. tidy: fill small gaps, drop specks, clip to the coast,
     simplify                                                      tidy
  6. turn the nested areas into three bands that do not overlap    make_bands
  7. write GeoJSON in longitude/latitude, 4 decimals               geojson

The old pipeline did the same in spirit, but ran R and Python for every single map. Here the
heavy part (step 2) takes a few hundredths of a second, because the smoothing is done on the
whole grid in one go.

All geometry is in British National Grid metres until step 7.
"""
import json
from collections import defaultdict

import contourpy
import numpy as np
import shapely
from pyproj import Transformer
from scipy.ndimage import gaussian_filter
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union

from . import config
from .names import surname_key

G = config.GRID
CELL = G["cell"]
XC = G["x0"] + CELL * (np.arange(G["nx"]) + 0.5)          # x of every cell centre
YC = G["y0"] + CELL * (np.arange(G["ny"]) + 0.5)          # y of every cell centre


# ---------------------------------------------------------------------------
# 1. from database rows to the grid
# ---------------------------------------------------------------------------

def group_by_name(rows):
    """Rows of (raw surname, cell x, cell y, n) -> {key: (cell x, cell y, n)}, spellings merged."""
    seen = {}
    parts = defaultdict(lambda: ([], [], []))
    for raw, ix, iy, n in rows:
        key = seen.get(raw)
        if key is None:
            key = seen[raw] = surname_key(raw)
        if key:
            p = parts[key]
            p[0].append(ix)
            p[1].append(iy)
            p[2].append(n)
    return {k: (np.array(p[0], int), np.array(p[1], int), np.array(p[2], float)) for k, p in parts.items()}


def to_grid(ix, iy, n):
    grid = np.zeros((G["ny"], G["nx"]), np.float32)
    np.add.at(grid, (iy, ix), n)
    return grid


# ---------------------------------------------------------------------------
# 2. smoothing
# ---------------------------------------------------------------------------

def size_bandwidth(n):
    """The bandwidth for a name with n bearers: BANDWIDTH_MIN_M at the smaller of the two sizes in
    config.BANDWIDTH_N, rising steadily (with the logarithm of n) to BANDWIDTH_MAX_M at the larger.

    This replaces the old rule, which also used a per-surname "isonymy class" that cannot be made
    for new names. (The textbook rule of Scott, which measures how widely the bearers are spread,
    was tried and does not work here: every name has some national scatter, so it always asked
    for the widest bandwidth.)"""
    low, high = config.BANDWIDTH_N
    share = (np.log10(max(n, 1)) - np.log10(low)) / (np.log10(high) - np.log10(low))
    return float(config.BANDWIDTH_MIN_M + (config.BANDWIDTH_MAX_M - config.BANDWIDTH_MIN_M) * np.clip(share, 0, 1))


def choose_bandwidth(cell_sets):
    """One bandwidth for a name, from its biggest year, and used for all its years so that the maps
    along the slider are smoothed the same way and can be compared."""
    return size_bandwidth(max(cells[2].sum() for cells in cell_sets))


def smooth(grid, bandwidth_m):
    return gaussian_filter(grid, sigma=bandwidth_m / CELL, mode="constant")


def population_surface(ix, iy, n):
    """The smoothed surface of everybody, used for weighting."""
    return smooth(to_grid(ix, iy, n), config.POPULATION_BANDWIDTH_M)


# ---------------------------------------------------------------------------
# 3. weighting
# ---------------------------------------------------------------------------

def weigh(name_smooth, pop_smooth, land_grid, power=None):
    """Make the map "a bit relative": divide the name's density by the density of everybody to a
    power (config.WEIGHT_POWER: 0 = plain density, 1 = fully relative). Where fewer than
    WEIGHT_FLOOR people live per km2 the floor is used instead, so that a few people in an empty
    area cannot dominate. Everything that is not land is set to 0."""
    power = config.WEIGHT_POWER if power is None else power
    surface = name_smooth.astype(np.float64)
    if power:
        per_km2 = pop_smooth.astype(np.float64) / (CELL / 1000.0) ** 2
        surface = surface / np.maximum(per_km2, config.WEIGHT_FLOOR) ** power
    return np.where(land_grid, surface, 0.0)


# ---------------------------------------------------------------------------
# 4. levels
# ---------------------------------------------------------------------------

def level_cutoffs(surface, mode=None, levels=None):
    """The three cut-offs as shares of the surface's peak, level 1 (lowest) first.

    "mass": level 1 is the smallest area that holds LEVEL_MASS[0] of all the density, level 2 the
            smallest that holds LEVEL_MASS[1], and so on. The cut-off is simply the value of the
            cell at which the running total (highest cells first) reaches that share.
    "peak": fixed shares of the highest value, LEVEL_PEAK."""
    mode = mode or config.LEVEL_MODE
    if mode == "peak":
        return tuple(levels or config.LEVEL_PEAK)
    if mode != "mass":
        raise ValueError(f"unknown LEVEL_MODE {mode!r}")
    values = np.sort(surface[surface > 0])[::-1]
    running = np.cumsum(values)
    reached = np.searchsorted(running, np.array(levels or config.LEVEL_MASS) * running[-1])
    return tuple(float(values[min(i, values.size - 1)] / values[0]) for i in reached)


def nested_regions(surface, cutoffs=None):
    """The areas where the surface is above each cut-off (a share of its own peak). The areas are
    nested: the second lies inside the first. Returned as shapely geometries in metres."""
    peak = float(surface.max())
    if not peak > 0:
        return None
    cutoffs = cutoffs or level_cutoffs(surface)
    generator = contourpy.contour_generator(x=XC, y=YC, z=surface / peak,
                                            fill_type=contourpy.FillType.OuterOffset)
    regions = []
    for cutoff in cutoffs:
        points, offsets = generator.filled(cutoff, 2.0)     # 2.0 is above everything: values are at most 1
        polygons = []
        for pts, offs in zip(points, offsets):
            rings = [pts[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)]
            if len(rings[0]) >= 4:
                polygons.append(Polygon(rings[0], [r for r in rings[1:] if len(r) >= 4]))
        regions.append(unary_union(polygons) if polygons else Polygon())
    return regions


# ---------------------------------------------------------------------------
# 5. tidying
# ---------------------------------------------------------------------------

class Land:
    """The coast: maps are clipped to it so that outlines do not run into the sea."""

    def __init__(self, path=None):
        doc = json.loads((path or config.REFERENCE / "gb_outline.geojson").read_text())
        geometry = shape(doc["features"][0]["geometry"])
        self.parts = list(geometry.geoms) if hasattr(geometry, "geoms") else [geometry]
        self.tree = shapely.STRtree(self.parts)
        union = shapely.union_all(self.parts)
        shapely.prepare(union)
        x, y = np.meshgrid(XC, YC)
        self.grid = shapely.contains_xy(union, x.ravel(), y.ravel()).reshape(x.shape)   # which 1 km cells are land

    def clip(self, region):
        near = self.tree.query(region)                       # only the coast pieces that are anywhere near
        if len(near) == 0:
            return Polygon()
        return region.intersection(MultiPolygon([self.parts[i] for i in near]))


def _polygons(geometry):
    """All the polygons inside a geometry (which may be a collection of mixed shapes)."""
    if geometry.geom_type == "Polygon":
        return [geometry]
    return [p for g in getattr(geometry, "geoms", []) for p in _polygons(g)]


def _repair(geometry):
    """Fix the tiny topology faults that clipping and subtracting shapes can leave behind."""
    return geometry if geometry.is_valid else shapely.make_valid(geometry)


def drop_small(geometry):
    """Remove blobs and holes smaller than MIN_AREA_KM2."""
    smallest = config.MIN_AREA_KM2 * 1e6
    kept = []
    for polygon in _polygons(_repair(geometry)):
        if polygon.area >= smallest:
            kept.append(Polygon(polygon.exterior, [h for h in polygon.interiors if Polygon(h).area >= smallest]))
    return unary_union(kept) if kept else Polygon()


def tidy(region, land):
    if region.is_empty:
        return region
    smooth_m = config.SMOOTH_M
    region = drop_small(region.buffer(smooth_m).buffer(-smooth_m))      # closes gaps narrower than 2 x SMOOTH_M
    if region.is_empty:
        return region
    region = drop_small(land.clip(region).simplify(config.SIMPLIFY_M, preserve_topology=True))
    return region


# ---------------------------------------------------------------------------
# 6. bands
# ---------------------------------------------------------------------------

def make_bands(surface, land, cutoffs=None):
    """Three bands that do not overlap, level 1 (outermost) to level 3 (highest), in metres.
    None if there is nothing to draw."""
    regions = nested_regions(surface, cutoffs)
    if regions is None:
        return None
    regions = [tidy(r, land) for r in regions]
    for i in range(1, len(regions)):                        # tidying one area at a time can break the nesting
        regions[i] = regions[i].intersection(regions[i - 1])
    bands = [drop_small(regions[i].difference(regions[i + 1])) if i + 1 < len(regions) else regions[i]
             for i in range(len(regions))]
    return bands if any(not b.is_empty for b in bands) else None


def make_map(grid, bandwidth_m, pop_smooth, land, power=None, mode=None, levels=None):
    """One surname in one year: the bearers on the grid -> the three bands (or None).
    power, mode and levels override the settings in config.py (used to compare settings)."""
    surface = weigh(smooth(grid, bandwidth_m), pop_smooth, land.grid, power)
    if not surface.any():
        return None
    return make_bands(surface, land, level_cutoffs(surface, mode, levels))


# ---------------------------------------------------------------------------
# 7. output
# ---------------------------------------------------------------------------

_to_lonlat = Transformer.from_crs(27700, 4326, always_xy=True)


def geojson(bands):
    """The bands as a GeoJSON FeatureCollection in longitude/latitude with 4 decimals, as the data
    contract asks. Level 1 is the outermost band."""
    features = []
    for level, band in enumerate(bands, start=1):
        if band.is_empty:
            continue
        lonlat = _repair(shapely.transform(band, lambda c: np.column_stack(_to_lonlat.transform(c[:, 0], c[:, 1]))))
        try:
            lonlat = shapely.set_precision(lonlat, 0.0001)          # 4 decimals, about 11 m
        except shapely.errors.GEOSException:
            lonlat = _repair(shapely.transform(lonlat, lambda c: np.round(c, 4)))
        polygons = _polygons(lonlat)
        if polygons:
            geometry = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
            features.append({"type": "Feature", "properties": {"level": level}, "geometry": mapping(geometry)})
    return {"type": "FeatureCollection", "features": features} if features else None
