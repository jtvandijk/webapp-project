#!/usr/bin/env python3
"""Check a GBNames data release against docs/data-contract.md.

Usage:   python3 tools/validate_data.py site/data
         python3 tools/validate_data.py path/to/release --threshold 100

Run this on every release BEFORE it leaves the TRE and again before it goes on the web server.
Exit code 0 = no errors (warnings are allowed), 1 = at least one error.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Rough box around Great Britain in longitude/latitude. It catches coordinates that were not
# reprojected (British National Grid metres) or that have longitude and latitude swapped.
LON_RANGE = (-9.0, 2.5)
LAT_RANGE = (49.5, 61.5)

NAME_RE = re.compile(r"^[a-z]+$")
YEAR_RE = re.compile(r"^\d{4}$")
TOP_LEVEL_KEYS = {"schema", "name", "synthetic", "counts", "maps", "facts"}
FACT_KEYS = {"forenames", "places", "oac", "loac", "fpc", "imd", "ahah", "eth"}
GROUP_SCHEMES = ("oac", "loac", "fpc")          # a most-common group code, plus a distribution over every group seen
DECILE_SCHEMES = ("imd", "ahah")                # a most-common decile (1-10), plus a 10-number distribution


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where, message):
        self.errors.append(f"ERROR   {where}: {message}")

    def warn(self, where, message):
        self.warnings.append(f"warning {where}: {message}")


def load(path, report):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.error(path.name, "file is missing")
    except ValueError as exc:
        report.error(path.name, f"not valid JSON ({exc})")
    return None


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# ---------------------------------------------------------------------------
# shared files
# ---------------------------------------------------------------------------

def check_manifest(manifest, root, report):
    where = "manifest.json"
    if manifest.get("schema") != 1:
        report.error(where, "schema must be 1")
    if not is_int(manifest.get("threshold")):
        report.error(where, "threshold must be a whole number")
    release = manifest.get("release", {})
    if not release.get("version"):
        report.error(where, "release.version is missing")
    if not isinstance(release.get("synthetic"), bool):
        report.error(where, "release.synthetic must be true or false")

    sources = manifest.get("sources", {})
    if not sources:
        report.error(where, "sources is empty")
    for key, source in sources.items():
        for field in ("label", "short", "counts"):
            if not source.get(field):
                report.error(where, f"sources.{key}.{field} is missing")
        coverage = source.get("coverage")
        if not (isinstance(coverage, list) and len(coverage) == 2 and all(is_int(c) for c in coverage)):
            report.error(where, f"sources.{key}.coverage must be [first year, last year]")

    masks = manifest.get("masks", {})
    for key, mask in masks.items():
        if not (root / mask.get("url", "?")).exists():
            report.error(where, f"masks.{key}.url points to a file that does not exist")

    seen = set()
    for period in manifest.get("periods", []):
        pid = period.get("id")
        if pid in seen:
            report.error(where, f"period id {pid} appears twice")
        seen.add(pid)
        if period.get("source") not in sources:
            report.error(where, f"period {pid}: source {period.get('source')!r} is not in sources")
        if str(period.get("year")) != pid:
            report.error(where, f"period {pid}: id must equal the year")
        if period.get("mask") and period["mask"] not in masks:
            report.error(where, f"period {pid}: mask {period['mask']!r} is not defined in masks")
    if not seen:
        report.error(where, "periods is empty")

    if not manifest.get("levels"):
        report.error(where, "levels is empty")
    if not manifest.get("basemap", {}).get("tiles"):
        report.error(where, "basemap.tiles is empty")


def check_lookups(lookups, report):
    where = "lookups.json"
    if lookups.get("schema") != 1:
        report.error(where, "schema must be 1")
    for scheme in ("oac", "loac"):
        groups = lookups.get(scheme, {}).get("groups", {})
        supers = lookups.get(scheme, {}).get("supergroups", {})
        if not groups or not supers:
            report.error(where, f"{scheme} needs both supergroups and groups")
        for code, group in groups.items():
            if group.get("supergroup") not in supers:
                report.error(where, f"{scheme} group {code} has an unknown supergroup")
            for field in ("name", "colour"):
                if not group.get(field):
                    report.error(where, f"{scheme} group {code} has no {field}")
    # fpc has no supergroup concept (yet): just a name and colour per group
    for code, group in lookups.get("fpc", {}).get("groups", {}).items():
        for field in ("name", "colour"):
            if not group.get(field):
                report.error(where, f"fpc group {code} has no {field}")
    if not lookups.get("eth"):
        report.error(where, "eth is empty")
    for scale in ("imd", "ahah"):
        colours = lookups.get("scales", {}).get(scale, {}).get("colours", [])
        if len(colours) != 10:
            report.error(where, f"scales.{scale}.colours needs exactly 10 colours")


# ---------------------------------------------------------------------------
# one surname
# ---------------------------------------------------------------------------

def walk_positions(coords):
    if coords and is_number(coords[0]):
        yield coords
    else:
        for item in coords:
            yield from walk_positions(item)


def check_map(fc, levels, where, report):
    if not (isinstance(fc, dict) and fc.get("type") == "FeatureCollection" and fc.get("features")):
        report.error(where, "map must be a GeoJSON FeatureCollection with at least one feature")
        return
    for i, feature in enumerate(fc["features"]):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in ("Polygon", "MultiPolygon"):
            report.error(where, f"feature {i}: geometry must be Polygon or MultiPolygon")
            continue
        level = (feature.get("properties") or {}).get("level")
        if level not in levels:
            report.error(where, f"feature {i}: properties.level must be one of {sorted(levels)}")
        for lon, lat in (p[:2] for p in walk_positions(geometry["coordinates"])):
            if not (LON_RANGE[0] <= lon <= LON_RANGE[1] and LAT_RANGE[0] <= lat <= LAT_RANGE[1]):
                report.error(where, f"feature {i}: coordinate ({lon}, {lat}) is not longitude/latitude in Great Britain")
                return


def check_decile(fact, where, report):
    if not (is_int(fact.get("mode")) and 1 <= fact["mode"] <= 10):
        report.error(where, "mode must be a whole number from 1 to 10")
    dist = fact.get("distribution")
    if dist is not None:
        if not (isinstance(dist, list) and len(dist) == 10 and all(is_number(d) and d >= 0 for d in dist)):
            report.error(where, "distribution must be 10 numbers, one per decile")
        elif not 0.97 <= sum(dist) <= 1.03:
            report.error(where, f"distribution adds up to {sum(dist):.3f}, expected 1")
    for field in ("mean", "sd"):
        if field in fact and not is_number(fact[field]):
            report.error(where, f"{field} must be a number")


def check_group(fact, where, report):
    """oac, loac, fpc: a most-common group code, plus (optional) the share of bearers in every group seen."""
    if not (isinstance(fact.get("group"), str) and fact["group"]):
        report.error(where, "group must be a non-empty string")
    dist = fact.get("distribution")
    if dist is not None:
        if not (isinstance(dist, dict) and dist and all(is_number(v) and v >= 0 for v in dist.values())):
            report.error(where, "distribution must be a non-empty {group code: share}")
        elif not 0.97 <= sum(dist.values()) <= 1.03:
            report.error(where, f"distribution adds up to {sum(dist.values()):.3f}, expected 1")


def check_facts(facts, lookups, where, report):
    for key in facts:
        if key not in FACT_KEYS:
            report.warn(where, f"facts.{key} is not part of the contract and will be ignored")

    for source, block in facts.get("forenames", {}).items():
        for sex in ("f", "m"):
            names = block.get(sex, [])
            if len(names) > 10 or not all(isinstance(n, str) and n == n.lower() and n for n in names):
                report.error(where, f"forenames.{source}.{sex} must be at most 10 lowercase names")
    for source, rows in facts.get("places", {}).items():
        if len(rows) > 10 or not all(isinstance(r, dict) and r.get("area") and r.get("name") for r in rows):
            report.error(where, f"places.{source} must be at most 10 rows of {{area, name}}")

    for scheme in GROUP_SCHEMES:
        if scheme not in facts:
            continue
        check_group(facts[scheme], f"{where} {scheme}", report)
        if facts[scheme].get("group") not in lookups.get(scheme, {}).get("groups", {}):
            report.error(where, f"{scheme}.group {facts[scheme].get('group')!r} is not in lookups.json")
    if "eth" in facts:
        eth = facts["eth"]
        if str(eth.get("group")) not in lookups.get("eth", {}):
            report.error(where, f"eth.group {eth.get('group')!r} is not in lookups.json")
        countries = eth.get("countries")
        if countries is not None and (not isinstance(countries, list) or len(countries) > 3 or
                                      not all(isinstance(c, list) and len(c) == 2 and isinstance(c[0], str) and is_number(c[1]) for c in countries)):
            report.error(where, "eth.countries must be at most 3 [code, share] pairs")
        dist = eth.get("distribution")
        if dist is not None and not (isinstance(dist, dict) and all(is_number(v) and v >= 0 for v in dist.values())):
            report.error(where, "eth.distribution must be a {group code: share}")
    for scale in DECILE_SCHEMES:
        if scale in facts:
            check_decile(facts[scale], f"{where} {scale}", report)


def check_bundle(path, manifest, lookups, threshold, report):
    where = f"names/{path.parent.name}/{path.name}"
    bundle = load(path, report)
    if bundle is None:
        return None
    stem = path.stem
    if not NAME_RE.match(stem):
        report.error(where, "file name must be lowercase letters a-z only")
    if path.parent.name != stem[:2]:
        report.error(where, f"file must sit in the folder named after the first two letters ({stem[:2]!r})")
    if bundle.get("schema") != 1:
        report.error(where, "schema must be 1")
    if bundle.get("name") != stem:
        report.error(where, f"name {bundle.get('name')!r} does not match the file name")
    for key in bundle:
        if key not in TOP_LEVEL_KEYS:
            report.warn(where, f"unknown top-level field {key!r}")

    # made-up data must never be mistaken for a real release, and the other way round
    if bool(bundle.get("synthetic")) != bool(manifest["release"]["synthetic"]):
        report.error(where, "synthetic flag does not match manifest.release.synthetic")

    sources = manifest["sources"]
    counts = bundle.get("counts", {})
    for source, years in counts.items():
        if source not in sources:
            report.error(where, f"counts.{source}: unknown source")
            continue
        for year, value in years.items():
            if not YEAR_RE.match(year) or not is_int(value) or value < 0:
                report.error(where, f"counts.{source}.{year} must map a 4-digit year to a whole number")

    periods = {p["id"]: p for p in manifest["periods"]}
    levels = {lv["level"] for lv in manifest["levels"]}
    maps = bundle.get("maps", {})
    if not maps:
        report.error(where, "a bundle needs at least one map (names without a map are not published)")
    for pid, fc in maps.items():
        if pid not in periods:
            report.error(where, f"maps.{pid}: not a period in the manifest")
            continue
        copy_of = fc.get("copyOf") if isinstance(fc, dict) else None
        if copy_of is not None:
            # a copied map shows ANOTHER year's geometry, built from THAT year's bearers - so it is that
            # year's count the disclosure guard has to check, not this period's own (which is exactly why
            # a copy was made: this period's own count on its own is not a fair picture, e.g. Scotland
            # missing from the census that year)
            if copy_of not in periods:
                report.error(where, f"maps.{pid}: copyOf {copy_of!r} is not a period in the manifest")
                continue
            if copy_of not in maps:
                report.error(where, f"maps.{pid}: copyOf {copy_of!r} has no map of its own in this file")
                continue
            if isinstance(maps[copy_of], dict) and maps[copy_of].get("copyOf") is not None:
                report.error(where, f"maps.{pid}: copyOf {copy_of!r} is itself a copy - copy the original, not a copy of a copy")
                continue
            disclosure_pid = copy_of
        else:
            disclosure_pid = pid
        # disclosure guard: no map for a name-year with fewer bearers than the threshold
        count = counts.get(periods[disclosure_pid]["source"], {}).get(disclosure_pid)
        if count is None:
            report.error(where, f"maps.{pid}: there is no count for {disclosure_pid}, so the threshold cannot be checked")
        elif count < threshold:
            report.error(where, f"maps.{pid}: only {count} bearers in {disclosure_pid}, below the threshold of {threshold}")
        check_map(fc, levels, f"{where} maps.{pid}", report)

    check_facts(bundle.get("facts", {}), lookups, where, report)
    return bundle


# ---------------------------------------------------------------------------
# whole release
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("release", type=Path, help="folder that holds manifest.json, lookups.json, names/ ...")
    parser.add_argument("--threshold", type=int, help="override the threshold in the manifest (only to be stricter)")
    args = parser.parse_args()
    root = args.release
    report = Report()

    manifest = load(root / "manifest.json", report)
    lookups = load(root / "lookups.json", report)
    if manifest is None or lookups is None:
        print("\n".join(report.errors))
        return 1
    check_manifest(manifest, root, report)
    check_lookups(lookups, report)
    if report.errors:  # no point checking names against a broken manifest
        print("\n".join(report.errors))
        return 1

    threshold = manifest["threshold"]
    if args.threshold is not None:
        if args.threshold < threshold:
            report.warn("--threshold", f"{args.threshold} is lower than the manifest threshold {threshold}; using {threshold}")
        threshold = max(threshold, args.threshold)

    found = {}
    total_bytes = 0
    for path in sorted((root / "names").glob("*/*.json")):
        total_bytes += path.stat().st_size
        if check_bundle(path, manifest, lookups, threshold, report) is not None:
            found.setdefault(path.parent.name, set()).add(path.stem)

    # the search index must list exactly the names that have a file
    for shard_path in sorted((root / "index").glob("*.json")):
        listed = load(shard_path, report) or []
        if listed != sorted(listed):
            report.error(f"index/{shard_path.name}", "names must be sorted")
        if set(listed) != found.get(shard_path.stem, set()):
            report.error(f"index/{shard_path.name}", "does not match the files in names/" + shard_path.stem)
    for prefix in set(found) - {p.stem for p in (root / "index").glob("*.json")}:
        report.error(f"index/{prefix}.json", "missing")

    n_names = sum(len(v) for v in found.values())
    for line in report.warnings + report.errors:
        print(line)
    status = "FAILED" if report.errors else "OK"
    print(f"\n{status}: {n_names} names, {total_bytes / 1e6:.1f} MB of name files, "
          f"{len(report.errors)} errors, {len(report.warnings)} warnings")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
