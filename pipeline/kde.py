"""The map calculation: from "bearers per 1 km cell" to three levels of outline.

The steps, for one surname in one year (the numbers live in config.py):

  1. put the bearers on the 1 km grid                              to_grid
  2. spread each bearer over the surroundings (a Gaussian
     "kernel density"); how far is the bandwidth, which grows
     with the number of bearers                                    choose_bandwidth, smooth
  3. divide by the local population, partly ("a bit relative"),
     so that big cities do not show for every name                 weigh
  4. drop separate blobs that are too small a share of the name's
     own total to be worth showing - a handful of people on their
     own, not a real concentration                                 drop_minor_blobs
  5. cut at three levels, giving nested areas                      level_cutoffs, nested_regions
  6. tidy: fill small gaps, drop specks, clip to the coast,
     simplify                                                      tidy
  7. turn the nested areas into three bands that do not overlap    make_bands
  8. write GeoJSON in longitude/latitude, 4 decimals               geojson

The old pipeline did the same in spirit, but ran R and Python for every single map. Here the
heavy part (step 2) takes a few hundredths of a second, because the smoothing is done on the
whole grid in one go.

All geometry is in British National Grid metres until step 7.
"""
import json
import warnings
from collections import defaultdict

import contourpy
import numpy as np
import shapely
from pyproj import Transformer
from scipy import ndimage
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
    return ndimage.gaussian_filter(grid, sigma=bandwidth_m / CELL, mode="constant")


def population_surface(ix, iy, n, bandwidth_m=None):
    """The smoothed surface of everybody, used for weighting. bandwidth_m overrides
    config.POPULATION_BANDWIDTH_M (used to compare settings, e.g. against a big name's own,
    possibly wider, bandwidth - see WEIGHT_CEILING in config.py)."""
    return smooth(to_grid(ix, iy, n), config.POPULATION_BANDWIDTH_M if bandwidth_m is None else bandwidth_m)


# ---------------------------------------------------------------------------
# 3. weighting
# ---------------------------------------------------------------------------

def weigh(name_smooth, pop_smooth, land_grid, power=None):
    """Make the map "a bit relative": divide the name's density by the density of everybody to a
    power (config.WEIGHT_POWER: 0 = plain density, 1 = fully relative). Population is clipped
    between WEIGHT_FLOOR and WEIGHT_CEILING first, so that neither a handful of people in an empty
    area nor one extremely dense pixel in a city centre can dominate the division. Everything that
    is not land is set to 0."""
    power = config.WEIGHT_POWER if power is None else power
    surface = name_smooth.astype(np.float64)
    if power:
        per_km2 = pop_smooth.astype(np.float64) / (CELL / 1000.0) ** 2
        per_km2 = np.clip(per_km2, config.WEIGHT_FLOOR, config.WEIGHT_CEILING)
        surface = surface / per_km2 ** power
    return np.where(land_grid, surface, 0.0)


# ---------------------------------------------------------------------------
# 4. dropping minor blobs
# ---------------------------------------------------------------------------

def drop_minor_blobs(surface, min_share=None):
    """Zero out any separate blob (a connected patch of nonzero cells) that holds less than
    MIN_BLOB_SHARE of the name's total (weighted) density.

    This is different from MIN_AREA_KM2 (in tidy(), later): that drops blobs that are physically
    small, but at this pipeline's bandwidths even a single person's own smoothed "bump" can cover
    well over 100 km2, so a handful of people on their own, scattered somewhere on its own, would
    still pass an area test easily. What actually marks it as not worth showing is that it holds
    almost none of the name's total density, wherever it is - that is what this checks instead.

    A "separate blob" only means what the smoothing has already made separate: two concentrations
    close enough that their smoothed surfaces never actually reach zero between them (roughly,
    within a few times the bandwidth) are one connected blob as far as this is concerned, and are
    kept or dropped together, not compared to each other. It only tells apart things that are
    genuinely far apart, such as a real regional concentration versus a handful of individuals
    scattered elsewhere in the country - which is the case this was built for."""
    min_share = config.MIN_BLOB_SHARE if min_share is None else min_share
    if not min_share or not surface.any():
        return surface
    labels, count = ndimage.label(surface > 0)
    totals = ndimage.sum(surface, labels, index=np.arange(1, count + 1))
    keep = np.zeros(count + 1, bool)
    keep[1:] = totals >= min_share * surface.sum()
    return np.where(keep[labels], surface, 0.0)


def drop_tiny_blobs(weighted_surface, raw_smooth, min_bearers=None):
    """Zero out any separate blob (same connectivity test as drop_minor_blobs()) whose own actual
    (unweighted) bearer count - raw_smooth, i.e. smooth(grid, bandwidth_m) BEFORE weigh() - is below
    min_bearers, regardless of what share of the name's total that is.

    Built for names too small for drop_minor_blobs()/MIN_BLOB_SHARE to do its job at all: with very
    few total bearers, a real small cluster and 1-2 coincidentally close individuals are not
    reliably different in RELATIVE share of an already-tiny total (checked on real data, 2026-09-23
    - Van Dijk's and Lansley's "separate areas" count barely moved between MIN_BLOB_SHARE 0.02 and
    0.10). This checks an ABSOLUTE count instead, which does not have that problem - "1-2 people" is
    "1-2 people" whatever the name's total is. Complements MIN_BLOB_SHARE, does not replace it: this
    is the only one of the two that can ever help a small name, and MIN_BLOB_SHARE (a share of the
    total) is the only one of the two that makes sense for a large one, where a small, genuinely
    isolated pocket is still an absolute count too big for this to sensibly drop.

    A real disclosure/honesty judgement, not just a technical one: this only makes a KEPT blob's
    bearer count no smaller than min_bearers, not larger - a surviving blob at or just above the
    floor is still a small number of real people, shown as a smoothed area covering a wide enough
    region (a name's own bandwidth, kilometres to tens of kilometres) not to point at a specific
    place, but still worth choosing deliberately rather than defaulting to. config.MIN_BLOB_BEARERS
    is an unvalidated starting guess, like MIN_BLOB_SHARE originally was."""
    min_bearers = config.MIN_BLOB_BEARERS if min_bearers is None else min_bearers
    if not min_bearers or not weighted_surface.any():
        return weighted_surface
    labels, count = ndimage.label(weighted_surface > 0)
    raw_totals = ndimage.sum(raw_smooth, labels, index=np.arange(1, count + 1))
    keep = np.zeros(count + 1, bool)
    keep[1:] = raw_totals >= min_bearers
    return np.where(keep[labels], weighted_surface, 0.0)


# ---------------------------------------------------------------------------
# 5. levels
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
# 6. tidying
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
    """All the non-empty polygons inside a geometry (which may be a collection of mixed shapes).
    An empty polygon (e.g. _repair()'s fallback when GEOS cannot fix something at all) is excluded,
    not returned as "one polygon" - callers count these (separate areas, points, GeoJSON features)
    and an empty one is really zero of all three, not one."""
    if geometry.geom_type == "Polygon":
        return [] if geometry.is_empty else [geometry]
    return [p for g in getattr(geometry, "geoms", []) for p in _polygons(g)]


def _repair(geometry):
    """Fix the tiny topology faults that clipping and subtracting shapes can leave behind.
    GEOS sometimes reports "invalid value encountered" while doing this on a shape with a
    near-zero-area or near-degenerate part; this is a normal side effect of cleaning such a shape
    up, not a sign the result is wrong (checked by the geometry tests and the stress test, which
    look at the actual output, not just whether it ran quietly), so it is suppressed here rather
    than left to alarm whoever runs this without saying where it came from.

    Real incident (2026-09-23): on some real, very small/thinly-scattered names, make_valid() itself
    raised GEOSException("UnsupportedOperationException") instead of fixing the geometry - on a
    genuinely pathological shape it cannot repair at all, most likely after MIN_BLOB_BEARERS trims
    most of a small name's blobs away, leaving something small relative to SMOOTH_M's now-larger
    buffer. Not reproduced locally (tried real library versions and many small-scattered-name
    scenarios) to pin down further. Treated as "nothing worth showing here" (empty geometry), the
    same way a real gap between concentrations is - a shape even GEOS's own repair cannot fix is not
    one this pipeline can trust to draw correctly anyway, and the alternative is crashing the whole
    name's map rather than just this one band of it."""
    if geometry.is_valid:
        return geometry
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="invalid value encountered")
        try:
            return shapely.make_valid(geometry)
        except shapely.errors.GEOSException:
            return Polygon()


def drop_small(geometry):
    """Remove blobs and holes smaller than MIN_AREA_KM2."""
    smallest = config.MIN_AREA_KM2 * 1e6
    kept = []
    for polygon in _polygons(_repair(geometry)):
        if polygon.area >= smallest:
            kept.append(Polygon(polygon.exterior, [h for h in polygon.interiors if Polygon(h).area >= smallest]))
    return unary_union(kept) if kept else Polygon()


def tidy(region, land):
    """Also where buffer()/simplify() can raise the same benign "invalid value encountered"
    warning as _repair() does, on the same kind of awkward shape - suppressed for the same reason."""
    if region.is_empty:
        return region
    smooth_m = config.SMOOTH_M
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="invalid value encountered")
        region = drop_small(region.buffer(smooth_m).buffer(-smooth_m))  # closes gaps narrower than 2 x SMOOTH_M
        if not region.is_empty:
            region = drop_small(land.clip(region).simplify(config.SIMPLIFY_M, preserve_topology=True))
    return region


# ---------------------------------------------------------------------------
# 7. bands
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


def make_map(grid, bandwidth_m, pop_smooth, land, *, power=None, mode=None, levels=None, min_share=None, min_bearers=None):
    """One surname in one year: the bearers on the grid -> the three bands (or None).
    power, mode, levels, min_share and min_bearers override the settings in config.py (used to
    compare settings). Keyword-only from power on: a positional call that silently landed one of
    these in the wrong slot (found in preview.py/rules.py, 2026-09-23 - MIN_BLOB_SHARE was never
    actually applied all night because of exactly this) fails loudly instead of failing silently."""
    raw_smooth = smooth(grid, bandwidth_m)
    surface = weigh(raw_smooth, pop_smooth, land.grid, power)
    surface = drop_minor_blobs(surface, min_share)
    surface = drop_tiny_blobs(surface, raw_smooth, min_bearers)
    if not surface.any():
        return None
    return make_bands(surface, land, level_cutoffs(surface, mode, levels))


def concentration(grid, bandwidth_m, pop_smooth, land, power=None, min_share=None, share=0.5):
    """How piled-up (rather than spread thin) a name's map is, from near 0 (share is reached almost
    anywhere, even at low values - spread evenly across everywhere it has any presence at all) to
    near 1 (only the very peak counts - almost all of the density sits in a few cells): the "mass"
    cut-off value for `share`, as returned by level_cutoffs(), which is already a fraction of the
    surface's own peak. Not used by make_map() - exploratory, for judging whether a name's own
    concentration (rather than its bearer count) predicts how tight LEVEL_MASS should be for it. As
    cheap as one level_cutoffs() call, since that is exactly what this is."""
    surface = weigh(smooth(grid, bandwidth_m), pop_smooth, land.grid, power)
    surface = drop_minor_blobs(surface, min_share)
    if not surface.any():
        return None
    return level_cutoffs(surface, mode="mass", levels=(share,))[0]


def second_blob_share(grid, bandwidth_m, pop_smooth, land, power=None, min_share=None):
    """How big a SECOND separate concentration is, relative to the biggest one, after
    drop_minor_blobs(): 0 if there is only one (surviving) blob, up to just under 1 if there are two
    of nearly equal size. Exploratory, like concentration() above, but answers a different question:
    concentration cannot tell "one tall peak" apart from "two comparably tall peaks", since both
    pile mass close to their own peak value - this can, since it looks at separate blobs' masses
    directly rather than the shape of the whole value histogram. Candidate explanation for why Smith
    (highest concentration of the names tried, 2026-09-23) wanted the LOOSEST LEVEL_MASS rather than
    the tightest: tightening a name with two comparably strong regions can carve a gap between them
    (the "holes" seen on real data) even though each region on its own is highly concentrated."""
    surface = weigh(smooth(grid, bandwidth_m), pop_smooth, land.grid, power)
    surface = drop_minor_blobs(surface, min_share)
    if not surface.any():
        return None
    labels, count = ndimage.label(surface > 0)
    if count < 2:
        return 0.0
    totals = np.sort(ndimage.sum(surface, labels, index=np.arange(1, count + 1)))[::-1]
    return float(totals[1] / totals[0])


def size_level_mass(n, second_share=0.0):
    """A first-draft LEVEL_MASS triple for a name with n bearers (its biggest year) and the given
    second_blob_share (from that year's own surface) - NOT a fitted regression, a rough
    log-interpolated curve through where real names' hand-picked verdicts seemed to peak. Round 1
    (2026-09-23 evening, 8 names x 4 settings): Smith, Jones, Davies, Obrien, Macdonald, Longley,
    Cheshire, Van Dijk. Round 2 (2026-09-23 night, 28 names against round 1's curve, with a wider
    smoothing pass - see SMOOTH_M - also active): Smith, Longley, Van Dijk, Macdonald, Obrien,
    Cheshire, Davies, Jones, Patel, Lansley, Williams, Taylor, Evans, Thomas, Wilson, Johnson,
    Baker, Davidson, Brown, Fraser, Mackenzie, Pugh, Pascoe, Murphy, Kelly, Nguyen, Robinson, Cohen.
    Expect the anchor points to keep moving as more names are checked - this exists to be tested
    against real verdicts, not trusted as settled. Each level is interpolated on its own (not one
    triple scaled by a single factor), since the good settings did not keep the same shape (ratio
    between levels) at every size.

    Shaped like an inverted U, tightest for names in the low thousands to tens of thousands of
    bearers, loosest at both ends: very small names (Van Dijk, ~150 bearers; Lansley, ~400) may have
    too little real signal for any tight cut to reliably separate a genuine concentration from a few
    coincidentally close individuals, so forcing one is not obviously more honest than the
    untightened original - the smallest anchor is simply config.LEVEL_MASS, unchanged. At the large
    end (round 2): several names around 200k-400k bearers (Davies, Jones, Williams, Taylor, Thomas)
    read as more spread than wanted and were tightened; Smith's own second_blob_share turned out to
    be ~0 on real data, so round 1's "more than one comparably strong region" guess for it does not
    hold either.

    Round 2 also tried tightening Smith's level 3 on its own, in response to its "circles" complaint
    - reverted in round 3 (2026-09-23, still the same night) once real data showed this made a
    DIFFERENT complaint (a "C" shape/ring around dense cities, WEIGHT_CEILING's job, see config.py)
    visibly WORSE, not better. Mechanism: where the weighted surface dips at an exact dense city
    centre and rings higher around it (WEIGHT_CEILING's problem to fix, not this curve's), a LOOSER
    level threshold can sit below both the dip and the ring, reading as one solid area; tightening
    raises the threshold until it clears the dip but not the ring, which is exactly what a "circle"
    or "C" shape looks like - so tightening a name's tightest level does not fix that kind of
    artefact, it exposes it. The 500,000-bearer anchor's level 3 is back at its round-1 value (0.30)
    for this reason - the "circles" complaint that motivated tightening it was itself probably this
    same weighting artefact, to be fixed at its source (WEIGHT_CEILING/POPULATION_BANDWIDTH_M), not
    compensated for here.

    Longley/Cheshire (~2,000 bearers) and Obrien/Macdonald/Davidson (~35,000) each share an anchor
    point but did not all want the same setting - a real residual this curve cannot capture since it
    is a function of n (and second_share) alone. Longley/Cheshire stopped visibly diverging once
    the wider smoothing pass was tried, suggesting at least part of that gap may have been a
    smoothing artefact rather than something size_level_mass() itself needs to fix. Obrien/Davidson
    were happy with the current ~35,000 setting while Macdonald (and Fraser, and Mackenzie, all
    Scottish clan names, all missing a real secondary region - London for Macdonald/Fraser) wanted
    it looser - handled below via second_share, not by moving the shared anchor and unsettling
    Obrien/Davidson.

    second_share used to be a hard override past 0.35 (one comparably-sized second region, as
    tested on synthetic data). Real names never reached anywhere near that - Mackenzie's very real,
    clearly-wanted secondary region measured only 0.03, Lansley 0.05 - so a high threshold could
    never have helped the cases it needed to. Replaced with a continuous blend towards the loosest
    (500,000-bearer) anchor, weighted by sqrt(second_share) rather than second_share itself so a
    small-but-real secondary region (0.03-0.08, the range actually seen) still moves the result
    noticeably rather than being rounded away. Unconfirmed whether this is enough to bring
    Macdonald/Fraser/Mackenzie's missing regions back - needs checking against their actual
    second_share (only Mackenzie's was reported this round) and the resulting map, not assumed."""
    anchors_n = np.log10([100, 2_000, 35_000, 300_000, 500_000])
    anchor_triples = [config.LEVEL_MASS, (0.40, 0.20, 0.10), (0.50, 0.25, 0.10), (0.60, 0.38, 0.17), (0.85, 0.60, 0.30)]
    x = np.log10(max(n, 1))
    levels = tuple(float(np.interp(x, anchors_n, [t[i] for t in anchor_triples])) for i in range(3))
    if second_share:
        weight = min(second_share, 1.0) ** 0.5
        levels = tuple(v + weight * (loose - v) for v, loose in zip(levels, anchor_triples[-1]))
    return tuple(round(v, 3) for v in levels)


# ---------------------------------------------------------------------------
# 8. output
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
