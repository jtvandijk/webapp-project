"""Stage 5: the facts about each name - neighbourhood classifications, top neighbourhoods, ethnicity, forenames,
and, from the census, historic forenames and parishes.

    python3 -m pipeline.s5_facts                      # every fact, for every name in work/names.csv
    python3 -m pipeline.s5_facts --limit 500          # a sample run: the first 500 names, as in stage 3
    python3 -m pipeline.s5_facts --names smith macdonald   # a few names, to look at by eye: work/preview_facts/
    python3 -m pipeline.s5_facts --facts oac imd      # only some facts (say, after loading a new table)
    python3 -m pipeline.s5_facts --compute-only       # no database: redo the calculation from the saved extracts
    python3 -m pipeline.s5_facts --sources register   # only the register facts, e.g. while the census database is not ready
    python3 -m pipeline.s5_facts --sources census --census-years 1851 1861 1881 1891 1901 1911   # 1921 not loaded yet

The rules (all in config.py, section 6):
  * Contemporary facts are worked out in each name's REFERENCE YEAR, the latest register year in which
    it has at least THRESHOLD["register"] bearers (counts.csv, from stage 1). Each fact is the most
    common value among the bearers who have one, and is only kept when that value has at least
    FACT_MIN_IN_CATEGORY bearers (the 100-bearer floor applies to the name, through the reference year).
    A tie is broken at random, but always the same way for the same name and fact (so a re-run gives
    the same answer, and the output says when it happened).
  * Forenames are the exception: pooled over every register year, since a name with no bearers in
    the newest year should still have forenames.
  * A source gives facts only to a name that has at least THRESHOLD[source] bearers in at least one year of that
    source: the register facts (forenames included) need 100 register bearers in some year, the historic facts need
    100 census bearers in some census year. So a name with a page only for its register bearers has no historic
    forenames or parishes, and a name that is only a historic one has no contemporary facts.
  * Historic facts come from the census and are pooled over the census years: forenames (with the sex in
    the census) and parishes, the most common first, each with at least FACT_MIN_IN_CATEGORY people. A parish is
    counted by county and name, so it is one parish whichever boundaries (1851 or 1901) number it. Which
    years were pooled is written in `detail`. The people counted are the ones the census counts and maps use.

Two steps, so a change of rule never needs the database again:
  1. extract: one query per fact and per reference year, saved under work/facts/extract/. A saved
     extract is reused while the names it was made for are unchanged (--refresh forces a new query).
  2. compute: the facts and the report, from the extracts.

Writes (work/facts/, or work/preview_facts/ for a --names run, which also keeps a numbered copy of each run's
facts.csv and report.txt as facts<N>.csv and report<N>.txt, so an earlier run is never lost; --out-dir chooses
another folder):
  by_fact/<fact>.csv   one file per fact, so a run of only some facts leaves the others as they were
  facts.csv            all of them together: surname, fact, version, ref_year, n_bearers, value, detail
  report.txt           how many names got each fact, why others did not, and what looked odd
`detail` is JSON: the distribution over the values, the spread, the list for places and forenames, and
`tie` when a tie was broken. `version` says which release of the classification the value is from.
"""
import argparse
import csv
import hashlib
import json
import math
import random
import textwrap
import time
from collections import Counter, defaultdict
from pathlib import Path

from . import config, db, files, sql
from .names import forename_clean, name_key, place_label, surname_key
from .s3_extracts import load_names

FIELDS = ["surname", "fact", "version", "ref_year", "n_bearers", "value", "detail"]
QUERIED = ["oac", "loac", "ahah", "imd", "fpc", "places", "eth"]   # one query per reference year
REGISTER_FACTS = QUERIED + ["forenames"]                           # forenames: one query in all
CENSUS_FACTS = ["forenames_census", "parishes"]                    # one query per census year
ALL = REGISTER_FACTS + CENSUS_FACTS
POOLED = ["forenames_register", "forenames_census", "parishes"]    # facts about all the years, so no reference year


# ---------------------------------------------------------------------------
# which year, which names
# ---------------------------------------------------------------------------

def load_counts(path=None):
    """{(source, year, key): n} from counts.csv (stage 1)."""
    path = path or config.WORK / "counts.csv"
    if not Path(path).exists():
        raise SystemExit(f"{path} does not exist yet. Stage 1 makes it (with names.csv): run  qsub pipeline/hpc/stage1.sh  first "
                         "- see docs/how-to-build-the-dataset.md, section 10.")
    with open(path, newline="") as f:
        return {(row["source"], int(row["year"]), row["surname"]): int(row["n"]) for row in csv.DictReader(f)}


def reference_years(counts, names):
    """{name: year}: the latest register year with at least THRESHOLD["register"] bearers, for each of
    `names` that has one. A name with none (say, listed for its census bearers only) has no
    contemporary facts."""
    wanted = set(names)
    best = {}
    for (source, year, key), n in counts.items():
        if source == "register" and n >= config.THRESHOLD["register"] and key in wanted and year > best.get(key, 0):
            best[key] = year
    return best


def names_with_enough(counts, names, source, years=None):
    """The `names` with at least THRESHOLD[source] bearers in at least one year of `source` (only among `years`, if
    given): the names that source may give facts to."""
    wanted, threshold = set(names), config.THRESHOLD[source]
    return sorted({key for (src, year, key), n in counts.items()
                   if src == source and n >= threshold and key in wanted and (years is None or year in years)})


def names_by_year(ref_years):
    by_year = defaultdict(list)
    for key, year in ref_years.items():
        by_year[year].append(key)
    return {year: sorted(keys) for year, keys in sorted(by_year.items())}


# ---------------------------------------------------------------------------
# step 1: extract
# ---------------------------------------------------------------------------
# An extract is trusted only while it was made for exactly the names now asked for: its .done marker
# records a fingerprint of them and is written last, so an interrupted run leaves no marker.

def fingerprint(names):
    return hashlib.md5("\n".join(sorted(names)).encode()).hexdigest()[:12]


def _paths(out_dir, stem):
    return out_dir / "extract" / f"{stem}.csv", out_dir / "extract" / f"{stem}.done"


def is_current(out_dir, stem, names):
    csv_path, done = _paths(out_dir, stem)
    return csv_path.exists() and done.exists() and done.read_text().strip() == f"names={fingerprint(names)}"


def _save(out_dir, stem, header, rows, names):
    csv_path, done = _paths(out_dir, stem)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    done.unlink(missing_ok=True)
    with open(csv_path, "w", newline="") as f:
        out = csv.writer(f)
        out.writerow(header)
        out.writerows(rows)
    done.write_text(f"names={fingerprint(names)}\n")


def _shape(fact):
    """(number of value columns, number of extra sum columns) in a fact's query result."""
    spec = config.FACT_QUERIES[fact]
    return len(spec.get("values") or spec.get("areas") or ["code"]), 2 * len(spec.get("sums", []))


def extract_fact(conn, cfg, fact, year, names, out_dir, refresh=False):
    """One query for one fact in one year, for `names` (those whose reference year it is). Spelling
    variants are merged by surname key here, and only the listed names are kept, whatever the
    coarse database filter let through. Returns the number of rows saved, or None if a current
    extract was already there."""
    stem = f"{fact}_{year}"
    if not refresh and is_current(out_dir, stem, names):
        return None
    n_values, n_sums = _shape(fact)
    wanted = set(names)
    totals = {}
    for row in db.fetch(conn, sql.fact_counts(cfg, fact, year, surnames=names)):
        key = surname_key(row[0])
        if key not in wanted:
            continue
        values = tuple("" if v is None else str(v) for v in row[1:1 + n_values])
        acc = totals.setdefault((key,) + values, [0] + [0.0] * n_sums)
        acc[0] += int(row[1 + n_values])
        for i, v in enumerate(row[2 + n_values:]):
            acc[1 + i] += float(v)
    header = ["surname"] + [f"value{i + 1}" for i in range(n_values)] + ["n"] + [f"sum{i + 1}" for i in range(n_sums)]
    _save(out_dir, stem, header, sorted(k + tuple(v) for k, v in totals.items()), names)
    return len(totals)


def read_extract(out_dir, fact, year):
    """{name: [(values, n, sums), ...]} from a saved extract."""
    n_values, _ = _shape(fact)
    found = defaultdict(list)
    with open(_paths(out_dir, f"{fact}_{year}")[0], newline="") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            found[row[0]].append((tuple(row[1:1 + n_values]), int(row[1 + n_values]),
                                  [float(x) for x in row[2 + n_values:]]))
    return found


def extract_forenames(conn, cfg, names, out_dir, refresh=False):
    """Forenames per surname and sex, pooled over every register year: one query."""
    if not refresh and is_current(out_dir, "forenames", names):
        return None
    wanted = set(names)
    totals = Counter()
    for raw, sex, forename, n in db.fetch(conn, sql.forename_counts(cfg, surnames=names)):
        key, clean = surname_key(raw), forename_clean(forename)
        if key in wanted and clean and sex in ("F", "M"):
            totals[(key, sex, clean)] += int(n)
    _save(out_dir, "forenames", ["surname", "sex", "forename", "n"],
          sorted((k, s, f, n) for (k, s, f), n in totals.items()), names)
    return len(totals)


def read_forenames(out_dir, stems=("forenames",)):
    """{name: {"F": {forename: n}, "M": {...}}} from the saved forenames extract(s); several (one per census
    year) are added together."""
    found = defaultdict(lambda: {"F": {}, "M": {}})
    for stem in stems:
        with open(_paths(out_dir, stem)[0], newline="") as f:
            reader = csv.reader(f)
            next(reader)
            for key, sex, forename, n in reader:
                found[key][sex][forename] = found[key][sex].get(forename, 0) + int(n)
    return found


_norm = name_key           # a county or parish name as a key: a spelling of the case does not split a parish


def extract_census_forenames(conn, cfg, year, names, out_dir, refresh=False):
    """Forenames per surname and sex in one census year (the query keeps the most common per spelling)."""
    stem = f"forenames_census_{year}"
    if not refresh and is_current(out_dir, stem, names):
        return None
    wanted, totals = set(names), Counter()
    for raw, sex, forename, n in db.fetch(conn, sql.census_forename_counts(cfg, year, surnames=names)):
        key, clean = surname_key(raw), forename_clean(forename)
        if key in wanted and clean and sex in ("F", "M"):
            totals[(key, sex, clean)] += int(n)
    _save(out_dir, stem, ["surname", "sex", "forename", "n"], sorted((k, s, f, n) for (k, s, f), n in totals.items()), names)
    return len(totals)


def extract_parishes(conn, cfg, year, names, out_dir, refresh=False):
    """Parishes per surname in one census year, by county and name (spellings of the case merged)."""
    stem = f"parishes_{year}"
    if not refresh and is_current(out_dir, stem, names):
        return None
    wanted, totals = set(names), {}
    for raw, county, parish, n in db.fetch(conn, sql.census_parish_counts(cfg, year, surnames=names)):
        key = surname_key(raw)
        if key not in wanted or not _norm(parish):
            continue
        entry = totals.setdefault((key, _norm(county), _norm(parish)), [str(county or "").strip(), str(parish).strip(), 0])
        entry[2] += int(n)
    _save(out_dir, stem, ["surname", "county", "parish", "n"],
          sorted((k[0], e[0], e[1], e[2]) for k, e in totals.items()), names)
    return len(totals)


def read_parishes(out_dir, years):
    """{name: {(county key, parish key): [county, parish, n]}} added together over the census years."""
    found = defaultdict(dict)
    for year in years:
        with open(_paths(out_dir, f"parishes_{year}")[0], newline="") as f:
            reader = csv.reader(f)
            next(reader)
            for key, county, parish, n in reader:
                entry = found[key].setdefault((_norm(county), _norm(parish)), [county, parish, 0])
                entry[2] += int(n)
    return found


def check_tables(conn, cfg, facts):
    """Stop if a table that the queries join to has a key twice: everybody with it would count twice."""
    problems = []
    for fact in facts:
        table = config.FACT_QUERIES.get(fact, {}).get("table")
        if table and db.fetch(conn, sql.duplicate_nbhd_keys(cfg, table))[0][0]:
            problems.append(f"{cfg['facts']['tables'][table]} has area codes that appear more than once")
    if "forenames" in facts and db.fetch(conn, sql.duplicate_gender_names(cfg))[0][0]:
        problems.append(f"{cfg['facts']['gender']['table']} has forenames that appear more than once")
    if problems:
        raise SystemExit("Nothing has been queried, because:\n  " + "\n  ".join(problems) +
                         "\nMake each one row per key (or fix the table names in config.py) and run again.")


# ---------------------------------------------------------------------------
# step 2: compute
# ---------------------------------------------------------------------------

def pick_mode(counts, seed):
    """(value, tied): the most common value. A tie is broken at random, but the same way every time
    for the same seed, whichever machine or run it is (a string seed is hashed, not Python's own hash())."""
    top = max(counts.values())
    tied = sorted(v for v, n in counts.items() if n == top)
    if len(tied) == 1:
        return tied[0], False
    return random.Random(seed).choice(tied), True


def _duration(seconds):
    """45 s, 3 min 12 s, 1 h 05 min: a time you can read in a log."""
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} s"
    if seconds < 3600:
        return f"{seconds // 60} min {seconds % 60:02d} s"
    return f"{seconds // 3600} h {seconds % 3600 // 60:02d} min"


def _share(n, total):
    return round(n / total, config.SHARE_DECIMALS)


def _row(key, fact, year, n, value, detail, years=None):
    version = config.FACT_VERSIONS[fact]
    if years:                                    # the historic facts say which census years were pooled
        version = version.format(first=min(years), last=max(years))
    return {"surname": key, "fact": fact, "version": version, "ref_year": year,
            "n_bearers": n, "value": value, "detail": json.dumps(detail, separators=(",", ":"), ensure_ascii=False)}


def _with_tie(detail, tied):
    if tied:
        detail["tie"] = True
    return detail


def _tally_covered(tally, fact, total):
    """Bearers who live where the classification has a value, counted for every name that has any, whether or
    not the fact is then reported for that name (the report's coverage is about the data, not about the rule)."""
    tally[fact]["covered"] += total


def _tally_value(tally, fact, total, tied=False):
    tally[fact]["with_value"] += 1
    tally[fact]["ties"] += tied


def compute_groups(fact, extracted, ref_years, tally):
    """OAC, LOAC and FPC: the most common group, and the share of bearers in every group."""
    out = []
    for key, rows in sorted(extracted.items()):
        by_value = Counter()
        for (value,), n, _ in rows:
            by_value[value] += n
        total = sum(by_value.values())
        _tally_covered(tally, fact, total)
        if max(by_value.values(), default=0) < config.FACT_MIN_IN_CATEGORY:
            continue
        value, tied = pick_mode(by_value, f"{key}|{fact}")
        shares = {v: _share(n, total) for v, n in sorted(by_value.items(), key=lambda item: (-item[1], item[0]))}
        out.append(_row(key, fact, ref_years[key], total, value, _with_tie({"distribution": shares}, tied)))
        _tally_value(tally, fact, total, tied)
    return out


def compute_deciles(fact, extracted, ref_years, tally):
    """AHAH and IMD: the most common decile, and the share of bearers in each of the ten."""
    out = []
    for key, rows in sorted(extracted.items()):
        by_value = Counter()
        for (value,), n, _ in rows:
            by_value[value] += n
        total = sum(by_value.values())
        _tally_covered(tally, fact, total)
        if max(by_value.values(), default=0) < config.FACT_MIN_IN_CATEGORY:
            continue
        value, tied = pick_mode(by_value, f"{key}|{fact}")
        shares = [_share(by_value.get(str(d), 0), total) for d in range(1, 11)]
        out.append(_row(key, fact, ref_years[key], total, value, _with_tie({"distribution": shares}, tied)))
        _tally_value(tally, fact, total, tied)
    return out


def compute_imd_score(extracted, ref_years, tally):
    """The GBNames deprivation score: the mean and the spread (sd) of the deprivation percentile."""
    out = []
    for key, rows in sorted(extracted.items()):
        total = sum(n for _, n, _ in rows)
        _tally_covered(tally, "imd_score", total)
        if total < config.FACT_MIN_IN_CATEGORY:
            continue
        s, ss = sum(sums[0] for _, _, sums in rows), sum(sums[1] for _, _, sums in rows)
        sd = math.sqrt(max(ss - s * s / total, 0.0) / (total - 1))
        out.append(_row(key, "imd_score", ref_years[key], total, round(s / total, 2), {"sd": round(sd, 2)}))
        _tally_value(tally, "imd_score", total)
    return out


def compute_places(extracted, ref_years, tally):
    """The most common neighbourhoods, most common first, each with at least FACT_MIN_IN_CATEGORY people. The
    counts themselves are not written."""
    out = []
    for key, rows in sorted(extracted.items()):
        by_area, district = Counter(), {}
        for (area, dist), n, _ in rows:
            by_area[area] += n
            district.setdefault(area, dist)
        total = sum(by_area.values())
        _tally_covered(tally, "places", total)
        listed = sorted(((a, n) for a, n in by_area.items() if n >= config.FACT_MIN_IN_CATEGORY), key=lambda an: (-an[1], an[0]))
        if not listed:
            continue
        top = [{"msoa": a, "district": district[a]} for a, _ in listed[:config.PLACES_TOP]]
        out.append(_row(key, "places", ref_years[key], total, "", {"places": top}))
        _tally_value(tally, "places", total)
    return out


def eth_group(code):
    """The census group an Ethnicity Estimator code belongs to (WAO-DE -> WAO), or None if it is not a known one."""
    group = code.split("-")[0].strip().upper()
    return group if group in config.ETH_GROUPS else None


def compute_ethnicity(extracted, ref_years, tally):
    """The most common census group among the bearers with a usable code. Every name with a reference
    year gets an answer: 'unknown' when no census group has at least FACT_MIN_IN_CATEGORY bearers. The
    three most common codes (countries) are kept too, for later."""
    out = []
    for key in sorted(ref_years):
        groups, codes = Counter(), Counter()
        for (code,), n, _ in extracted.get(key, []):
            group = eth_group(code)
            if group is None:
                tally["unmapped codes"][code] += n
                continue
            groups[group] += n
            codes[code.strip().upper()] += n
        total = sum(groups.values())
        _tally_covered(tally, "ethnicity", total)
        if max(groups.values(), default=0) < config.FACT_MIN_IN_CATEGORY:
            out.append(_row(key, "ethnicity", ref_years[key], total, config.ETH_UNKNOWN, {}))
            tally["ethnicity"]["unknown"] += 1
            continue
        value, tied = pick_mode(groups, f"{key}|ethnicity")
        detail = {"distribution": {g: _share(n, total) for g, n in sorted(groups.items(), key=lambda item: (-item[1], item[0]))},
                  "codes": [[c, _share(n, total)] for c, n in sorted(codes.items(), key=lambda item: (-item[1], item[0]))[:3]]}
        out.append(_row(key, "ethnicity", ref_years[key], total, value, _with_tie(detail, tied)))
        _tally_value(tally, "ethnicity", total, tied)
    return out


def compute_forenames(extracted, names, tally, fact="forenames_register", years=None):
    """The most common forenames per sex, pooled over every year, each with at least FACT_MIN_IN_CATEGORY
    people. The counts themselves are not written. For the census, `years` says which census years were pooled."""
    out = []
    for key in sorted(names):
        if key not in extracted:
            continue
        lists = {}
        for sex in ("F", "M"):
            common = sorted(((f, n) for f, n in extracted[key][sex].items() if n >= config.FACT_MIN_IN_CATEGORY),
                            key=lambda fn: (-fn[1], fn[0]))
            lists[sex.lower()] = [f for f, _ in common[:config.FORENAMES_TOP]]
        if lists["f"] or lists["m"]:
            if years:
                lists["years"] = list(years)
            out.append(_row(key, fact, "", "", "", lists, years))
            tally[fact]["with_value"] += 1
    return out


def compute_parishes(extracted, names, tally, years):
    """The most common parishes, pooled over the census years, most common first, each with at least
    FACT_MIN_IN_CATEGORY people. The counts themselves are not written."""
    out = []
    for key in sorted(names):
        parishes = extracted.get(key)
        if not parishes:
            continue
        # a place is shown under its label (config.UNNAMED_PARISH_LABELS gives the nameless London units of the 1901 table one
        # name, so they add up to one place); a parish with no name and no label is not a place to show
        pooled = {}
        for county, parish, n in parishes.values():
            label = place_label(county, parish, config.UNNAMED_PARISH_LABELS)
            if label:
                pooled.setdefault((_norm(label[0]), _norm(label[1])), [label[0], label[1], 0])[2] += n
        listed = sorted(((n, county, parish) for county, parish, n in pooled.values() if n >= config.FACT_MIN_IN_CATEGORY),
                        key=lambda item: (-item[0], _norm(item[1]), _norm(item[2])))
        if listed:
            top = [{"county": county, "parish": parish} for _, county, parish in listed[:config.PLACES_TOP]]
            out.append(_row(key, "parishes", "", "", "", {"parishes": top, "years": list(years)}, years))
            tally["parishes"]["with_value"] += 1
    return out


# ---------------------------------------------------------------------------
# writing and reporting
# ---------------------------------------------------------------------------

def write_fact(out_dir, fact, rows):
    path = out_dir / "by_fact" / f"{fact}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        out = csv.DictWriter(f, fieldnames=FIELDS)
        out.writeheader()
        out.writerows(sorted(rows, key=lambda r: r["surname"]))


def merge_facts(out_dir):
    """facts.csv: every by_fact file together, sorted by name and fact. Returns the number of rows."""
    rows = []
    for path in sorted((out_dir / "by_fact").glob("*.csv")):
        with open(path, newline="") as f:
            rows += list(csv.DictReader(f))
    rows.sort(key=lambda r: (r["surname"], r["fact"]))
    with open(out_dir / "facts.csv", "w", newline="") as f:
        out = csv.DictWriter(f, fieldnames=FIELDS)
        out.writeheader()
        out.writerows(rows)
    return len(rows)


def build_report(names, ref_years, counts, tally, outputs, pooled_scopes=None):
    """The lines of the report: what was worked out, and what to look at."""
    registered = sum(counts.get(("register", year, key), 0) for key, year in ref_years.items())
    years = Counter(ref_years.values())
    lines = [f"names in this run: {len(names):,}",
             f"with a reference year (a register year with {config.THRESHOLD['register']}+ bearers): {len(ref_years):,}"
             f"; the other {len(names) - len(ref_years):,} get no contemporary facts",
             "reference years: " + "  ".join(f"{y}: {n:,}" for y, n in sorted(years.items(), reverse=True)[:8]),
             "", f"{'fact':20} {'names with a value':>19} {'no value':>9} {'ties broken':>12} {'bearers covered':>16}"]
    for fact in outputs:
        t = tally[fact]
        scope = (pooled_scopes or {}).get(fact, len(names)) if fact in POOLED else len(ref_years)
        coverage = "" if fact in POOLED or not registered else f"{t['covered'] / registered:>15.1%}"
        lines.append(f"{fact:20} {t['with_value']:>19,} {scope - t['with_value'] - t['unknown']:>9,} "
                     f"{t['ties']:>12,} {coverage:>16}")
    if "ethnicity" in outputs:
        lines.append(f"\nethnicity: {tally['ethnicity']['unknown']:,} names are 'unknown' (no census group with at least "
                     f"{config.FACT_MIN_IN_CATEGORY} bearers)")
        if tally["unmapped codes"]:
            lines.append("ethnicity codes not in config.ETH_GROUPS, left out of the counts (code: bearers): " +
                         ", ".join(f"{c}: {n:,}" for c, n in tally["unmapped codes"].most_common(20)))
    lines.append("")
    lines += textwrap.wrap(
        "'bearers covered' is about the data, not about the names: of ALL the bearers of these names, in their reference "
        "years, the share who live where the classification has a value (whether or not the fact is then reported for "
        "their name). About 99.9% is expected for OAC, AHAH, IMD, FPC and places; a lower share for one of them means a "
        "join problem. LOAC covers London only, so its share is about London's share of the bearers (roughly one in "
        "seven), by design, and it barely moves when a small name is added, since big names dominate the total. "
        "Ethnicity depends on how many bearers have a code.", width=100)
    return lines


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--facts", nargs="*", choices=ALL, default=config.RUN_FACTS,
                        help="which facts (default GBNAMES_FACTS in run.settings, else all those of the chosen sources)")
    parser.add_argument("--sources", nargs="*", choices=["register", "census"], default=config.RUN_SOURCES,
                        help="which sources' facts (default GBNAMES_SOURCES in run.settings); only their databases are opened")
    parser.add_argument("--census-years", nargs="*", type=int, choices=config.CENSUS_YEARS, default=config.CENSUS_YEARS,
                        help="which census years to pool for the historic facts (default: all; leave one out while its data is not ready)")
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--limit", type=int, default=config.RUN_LIMIT,
                       help="only the first N names from work/names.csv (a sample run; default GBNAMES_LIMIT in run.settings)")
    which.add_argument("--names", nargs="*", help="only these names, which must be in work/names.csv; the results go in "
                       "work/preview_facts/, so a few names never replace the files of a fuller run")
    parser.add_argument("--refresh", action="store_true", help="query again even where a current extract exists")
    parser.add_argument("--compute-only", action="store_true", help="no database: use the saved extracts")
    parser.add_argument("--out-dir", help="where to write (default: work/facts, or work/preview_facts for a --names run)")
    args = parser.parse_args()
    out_dir = Path(args.out_dir) if args.out_dir else config.WORK / ("preview_facts" if args.names else "facts")
    facts = list(args.facts) if args.facts else [f for f in ALL if ("census" if f in CENSUS_FACTS else "register") in args.sources]
    census_years = sorted(args.census_years)
    if not facts:
        raise SystemExit("Nothing to do: no facts for those sources.")

    print(config.describe_run(), flush=True)
    names = load_names(None if args.names else args.limit)         # a sample limit does not apply to names asked for by name
    if not names:
        raise SystemExit("No names in work/names.csv - run s1_counts.py first.")
    if args.names:
        chosen = sorted({surname_key(n) for n in args.names} - {""})
        missing = [k for k in chosen if k not in set(names)]
        if missing:
            raise SystemExit(f"Not in work/names.csv, so not names that get a page: {', '.join(missing)}")
        names = chosen
    counts = load_counts()
    ref_years = reference_years(counts, names)
    by_year = names_by_year(ref_years)
    census_names = names_with_enough(counts, names, "census", census_years)
    print(f"{len(names):,} names, {len(ref_years):,} with a reference year, in {len(by_year)} different years; "
          f"{len(census_names):,} with {config.THRESHOLD['census']}+ census bearers in some year")

    cfg = config.settings()
    register_facts = [f for f in REGISTER_FACTS if f in facts]
    census_facts = [f for f in CENSUS_FACTS if f in facts]

    began, spent = time.perf_counter(), defaultdict(float)     # seconds in the database, by fact

    def report_time(fact, label, rows, started):
        if rows is not None:
            spent[fact] += time.perf_counter() - started
        print(f"{label}: " + ("saved extract reused" if rows is None else f"{rows:,} rows, {time.perf_counter() - started:.1f}s"), flush=True)

    if not args.compute_only:
        if register_facts:
            conn = db.connect("register")
            check_tables(conn, cfg, facts)
            for fact in [f for f in QUERIED if f in facts]:
                for year, keys in by_year.items():
                    started = time.perf_counter()
                    rows = extract_fact(conn, cfg, fact, year, keys, out_dir, args.refresh)
                    report_time(fact, f"{fact} {year} ({len(keys):,} names)", rows, started)
            if "forenames" in facts:
                started = time.perf_counter()
                report_time("forenames", "forenames", extract_forenames(conn, cfg, names, out_dir, args.refresh), started)
            conn.close()
        if census_facts:
            conn = db.connect("census")
            for fact, extractor in (("forenames_census", extract_census_forenames), ("parishes", extract_parishes)):
                for year in (census_years if fact in facts else []):
                    started = time.perf_counter()
                    report_time(fact, f"{fact} {year}", extractor(conn, cfg, year, names, out_dir, args.refresh), started)
            conn.close()

    # the extracts must be for the names now in scope, whether or not this run made them
    stale = [f"{fact} {year}" for fact in QUERIED if fact in facts for year, keys in by_year.items()
             if not is_current(out_dir, f"{fact}_{year}", keys)]
    if "forenames" in facts and not is_current(out_dir, "forenames", names):
        stale.append("forenames")
    stale += [f"{fact} {year}" for fact in CENSUS_FACTS if fact in facts for year in census_years
              if not is_current(out_dir, f"{fact}_{year}", names)]
    if stale:
        raise SystemExit("These extracts are missing, or were made for other names: " + ", ".join(stale) +
                         "\nRun again without --compute-only.")

    def load(fact):
        merged = {}
        for year in by_year:
            merged.update(read_extract(out_dir, fact, year))     # each name has exactly one reference year
        return merged

    tally = defaultdict(Counter)
    results = {}
    if "oac" in facts:
        results["oac"] = compute_groups("oac", load("oac"), ref_years, tally)
    if "loac" in facts:
        results["loac"] = compute_groups("loac", load("loac"), ref_years, tally)
    if "fpc" in facts:
        results["fpc"] = compute_groups("fpc", load("fpc"), ref_years, tally)      # safeguarded: see nbhd_tables.py
    if "ahah" in facts:
        results["ahah"] = compute_deciles("ahah", load("ahah"), ref_years, tally)
    if "imd" in facts:
        imd = load("imd")
        results["imd"] = compute_deciles("imd", imd, ref_years, tally)
        results["imd_score"] = compute_imd_score(imd, ref_years, tally)
    if "places" in facts:
        results["places"] = compute_places(load("places"), ref_years, tally)
    if "eth" in facts:
        results["ethnicity"] = compute_ethnicity(load("eth"), ref_years, tally)
    if "forenames" in facts:
        results["forenames_register"] = compute_forenames(read_forenames(out_dir), sorted(ref_years), tally)     # a reference year = a register year with enough bearers
    if "forenames_census" in facts:
        pooled = read_forenames(out_dir, [f"forenames_census_{y}" for y in census_years])
        results["forenames_census"] = compute_forenames(pooled, census_names, tally, "forenames_census", census_years)
    if "parishes" in facts:
        results["parishes"] = compute_parishes(read_parishes(out_dir, census_years), census_names, tally, census_years)

    for fact, rows in results.items():
        write_fact(out_dir, fact, rows)
    total = merge_facts(out_dir)
    report = build_report(names, ref_years, counts, tally, list(results),
                          {"forenames_register": len(ref_years), "forenames_census": len(census_names), "parishes": len(census_names)})
    queried = ", ".join(f"{fact} {_duration(sec)}" for fact, sec in spent.items()) or "none: every extract was reused"
    report += ["", f"time: {_duration(time.perf_counter() - began)} in total; time in the database by fact: {queried}"]
    (out_dir / "report.txt").write_text("\n".join(report) + "\n")
    print("\n".join(report))
    print(f"\n{total:,} facts in {out_dir / 'facts.csv'}")
    if args.names:                     # keep this run, so the next set of names does not replace it
        number = files.next_number(out_dir, "facts", ".csv")
        (out_dir / f"facts{number}.csv").write_bytes((out_dir / "facts.csv").read_bytes())
        (out_dir / f"report{number}.txt").write_bytes((out_dir / "report.txt").read_bytes())
        print(f"kept as {out_dir / f'facts{number}.csv'} and report{number}.txt")


if __name__ == "__main__":
    main()
