"""Stage 6: turn stage 4's per-chunk maps and stage 5's facts.csv into the release
docs/data-contract.md describes - one small JSON file per surname, work/release/names/<xx>/<name>.json.
No database access at all, like stage 4: everything it needs was already written to disk.

    python3 -m pipeline.s6_assemble --prepare                     # once, before the array job (see below)
    python3 -m pipeline.s6_assemble --chunk 0 --chunks 200         # one chunk, from an array job (pipeline/hpc/stage6.sh)

`--prepare` splits work/facts.csv and work/counts.csv into one file per chunk (work/facts/chunks/<n>.csv,
work/counts/chunks/<n>.csv), using the SAME chunk_of() every other stage uses, so a chunk task only ever
reads its own slice - not the whole file, 200 times over. It is cheap (one read, N small writes) and is
meant to run once, directly, not through qsub - the same as check_parishes.py or merge_stats.py. Skipped
if it is already current (work/facts/chunks/CHUNKS matches --chunks and facts.csv/counts.csv have not
changed since); pass --force to redo it anyway.

`--chunk N` (an SGE array task, see pipeline/hpc/stage6.sh) reads work/maps/chunk_N.jsonl (stage 4) and its
own facts/counts slices (from --prepare), and for every name that chunk owns:

    maps    a "build" row's geojson as-is (already lon/lat, stage 4's kde.geojson()); a "substitute" row
            becomes a COPY of the geometry it names, with copyOf added (a GeoJSON foreign member) so the
            website knows not to draw the Scotland mask on it (data-contract.md, decided 2026-09-26); an
            "omit" row is left out entirely. A name with no maps at all (should not happen - being in the
            name list at all means at least one period cleared the threshold - but checked anyway, since
            data-contract.md is explicit that a file with no map is not published) gets no file.
    facts   stage 5's facts.csv rows, regrouped into data-contract.md's shape: imd + imd_score merge into
            one imd object; places (register) + parishes (census) merge into one places object, fields
            renamed to {area, name} (already the shape tools/validate_data.py expects); forenames_register
            + forenames_census merge into one forenames object; ethnicity is renamed to eth. Only the
            fields data-contract.md actually asks for are copied across - not "tie" or "years", which are
            for stage 5's own report, not the public file. NOT put in the name files by default (decided
            2026-09-26): they go to one table instead, work/release/facts_parts/chunk_N.csv per chunk (merged by
            merge_release.py into facts.csv: one row per name and fact, name,fact,data with data the same JSON
            that would sit under facts.<fact> in the name file). A name file is then only counts and maps -
            plain static files that never change when a classification does - and folding the facts into them,
            or into a database, is a job for the website build outside the TRE. --facts-in-names writes them
            into the name files as well, as data-contract.md's original shape has it. Only names that get a
            file get facts rows.
    counts  every (source, year) this name has, straight from counts.csv - not only the mapped years.

Also writes work/release/index_parts/chunk_N.txt (the names this chunk wrote, one per line - the input to
merge_release.py's search index, and to a by-hand export/wipe later if HPC storage ever needs it: each
chunk's own file names exactly what is safe to move and delete together, which matters because the 200
chunks are split by a hash of the name, not alphabetically, so two different chunks can both write into
names/sm/) and work/release/chunk_N.done, reusing stage 4's exact done-marker logic (a marker is only
trusted if it names the same --chunks this run is using and its own output is still actually present).

A chunk is refused if stage 4 has not finished it (no work/maps/chunk_N.done: the maps file may be half written), and
a finished chunk is redone, not skipped, if its maps or its --prepare slices are newer than its own .done (stage 4 or
--prepare was run again since), so a re-run stage cannot leave stale files quietly in the release.

A single name's own facts/maps failing to combine (a genuinely unexpected shape) does not take the rest
of the chunk down with it - logged to work/release/chunk_N.errors.log and skipped, the same as stage 4.

--free-maps (off by default) deletes this chunk's own work/maps/chunk_N.jsonl once the whole chunk has been
assembled with no failures - the largest raw artifact (full GeoJSON), and the one that makes raw output and
the assembled release coexist on disk at the same time. Only for when HPC storage is actually the binding
constraint: it cannot be undone (re-assembling or re-building that chunk means re-running stage 4 for it), and
facts.csv/stats are untouched. If any name in the chunk failed, nothing is deleted - the raw rows are still
needed to look at why.
"""
import argparse
import copy
import csv
import errno
import itertools
import json
import re
import sys
import time
import traceback
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path

from . import config
from .names import chunk_of

FACTS_HEADER = ["surname", "fact", "version", "ref_year", "n_bearers", "value", "detail"]
COUNTS_HEADER = ["source", "year", "surname", "n"]
FACTS_TABLE_HEADER = ["name", "fact", "data"]         # the public facts table (merge_release.py's facts.csv)

# fact -> (public key, how to build its public object from {"value": str, "detail": dict}). A scheme not
# listed here (imd_score, forenames_register, forenames_census, places, parishes) is folded into another
# key's object instead - see build_facts().
GROUP_SCHEMES = ("oac", "loac", "fpc")             # {"group": code, "distribution": {code: share}}
DECILE_SCHEMES = ("ahah",)                          # {"mode": decile, "distribution": [10 numbers]}; imd is its own case (+ imd_score)


def _group_fact(row):
    detail = json.loads(row["detail"])
    out = {"group": row["value"]}
    if "distribution" in detail:
        out["distribution"] = detail["distribution"]
    return out


def _decile_fact(row):
    detail = json.loads(row["detail"])
    out = {"mode": int(row["value"])}
    if "distribution" in detail:
        out["distribution"] = detail["distribution"]
    return out


def build_facts(rows):
    """The public "facts" object for one name, from its rows of stage 5's facts.csv (fact, value, detail -
    detail already the parsed JSON, not the raw string). Only what data-contract.md asks for is copied
    across; internal-only detail (a tied pick, the years pooled) is not."""
    by_fact = {r["fact"]: r for r in rows}
    facts = {}
    for scheme in GROUP_SCHEMES:
        if scheme in by_fact:
            facts[scheme] = _group_fact(by_fact[scheme])
    for scheme in DECILE_SCHEMES:
        if scheme in by_fact:
            facts[scheme] = _decile_fact(by_fact[scheme])
    if "imd" in by_fact:
        imd = _decile_fact(by_fact["imd"])
        if "imd_score" in by_fact:
            imd["mean"] = float(by_fact["imd_score"]["value"])
            imd["sd"] = json.loads(by_fact["imd_score"]["detail"])["sd"]
        facts["imd"] = imd
    if "ethnicity" in by_fact:
        detail = json.loads(by_fact["ethnicity"]["detail"])
        eth = {"group": by_fact["ethnicity"]["value"]}
        if "distribution" in detail:
            eth["distribution"] = detail["distribution"]
        if "codes" in detail:
            eth["countries"] = detail["codes"]
        facts["eth"] = eth
    places = {}
    if "places" in by_fact:
        detail = json.loads(by_fact["places"]["detail"])
        places["register"] = [{"area": p["district"], "name": p["msoa"]} for p in detail.get("places", [])]
    if "parishes" in by_fact:
        detail = json.loads(by_fact["parishes"]["detail"])
        places["census"] = [{"area": p["county"], "name": p["parish"]} for p in detail.get("parishes", [])]
    if places:
        facts["places"] = places
    forenames = {}
    if "forenames_register" in by_fact:
        detail = json.loads(by_fact["forenames_register"]["detail"])
        forenames["register"] = {"f": detail.get("f", []), "m": detail.get("m", [])}
    if "forenames_census" in by_fact:
        detail = json.loads(by_fact["forenames_census"]["detail"])
        forenames["census"] = {"f": detail.get("f", []), "m": detail.get("m", [])}
    if forenames:
        facts["forenames"] = forenames
    return facts


def build_counts(rows):
    """The public "counts" object for one name: {source: {year: n}}, every year, from counts.csv."""
    counts = defaultdict(dict)
    for r in rows:
        counts[r["source"]][r["year"]] = int(r["n"])
    return dict(counts)


def build_maps(rows):
    """The public "maps" object for one name, from its rows of stage 4's maps.jsonl (already parsed JSON,
    one dict per (name, period)). A "build" row's geojson is used as-is; a "substitute" row becomes a copy
    of the geometry it names, with copyOf added; an "omit" row, or a substitute whose reference did not
    itself build (should not normally happen - rules.py only substitutes a period whose reference already
    has enough bearers - but the geometry can still fail to survive weighting/repair), is left out."""
    builds = {r["period"]: r["geojson"] for r in rows if r["action"] == "build" and r.get("geojson")}
    maps = dict(builds)
    for r in rows:
        if r["action"] == "substitute" and r["reference"] in builds:
            maps[r["period"]] = {**copy.deepcopy(builds[r["reference"]]), "copyOf": r["reference"]}
    return maps


def build_bundle(name, map_rows, fact_rows, count_rows, include_facts=False):
    """The per-name JSON (counts and maps; the facts too if include_facts), or None if it would have no map
    at all (data-contract.md: a file with no map is not published - every name on the list should clear this,
    since that is what put it on the list, but a name is skipped rather than published broken if it somehow
    does not)."""
    maps = build_maps(map_rows)
    if not maps:
        return None
    bundle = {"schema": 1, "name": name, "counts": build_counts(count_rows), "maps": maps}
    if include_facts:
        facts = build_facts(fact_rows)
        if facts:
            bundle["facts"] = facts
    return bundle


def facts_table_rows(name, fact_rows):
    """[name, fact, data] rows for one name's facts table: one row per public fact key, data the compact JSON
    of that fact's object (the same as it would be under facts.<fact> in the name file)."""
    return [[name, key, json.dumps(obj, separators=(",", ":"), ensure_ascii=False)] for key, obj in sorted(build_facts(fact_rows).items())]


# ---------------------------------------------------------------------------
# splitting facts.csv/counts.csv by chunk (--prepare)
# ---------------------------------------------------------------------------

def _chunk_dir(stem):
    return config.WORK / stem / "chunks"


def _source_csv(stem):
    """Where stage 1/5 actually write it: work/counts.csv (flat, stage 1), work/facts/facts.csv (stage
    5's own out-dir, alongside its report.txt/by_fact/extract) - not the same shape, so not a formula."""
    return config.WORK / "counts.csv" if stem == "counts" else config.WORK / "facts" / "facts.csv"


def split_current(stem, chunks):
    marker = _chunk_dir(stem) / "CHUNKS"
    source = _source_csv(stem)
    return (marker.exists() and marker.read_text().strip() == str(chunks) and
            source.exists() and marker.stat().st_mtime >= source.stat().st_mtime)


def split_by_chunk(stem, header, chunks):
    """Splits work/counts.csv or work/facts/facts.csv into work/<stem>/chunks/<n>.csv by chunk_of() on its
    "surname" column - the same partitioning stage 3 used for the point extracts, so a name's facts/counts
    land in exactly the chunk its maps already are in. Returns the number of rows split.

    A stream: one row at a time from the source to the chunk file it belongs to, with every chunk file open at
    once (one per chunk, so a few hundred). The facts table has millions of rows, and holding it all in memory
    to sort it into chunks would need several GB on the login node this is meant to run on."""
    source = _source_csv(stem)
    if not source.exists():
        raise SystemExit(f"{source} does not exist - run stage {'5 (facts)' if stem == 'facts' else '1 (counts)'} first.")
    out_dir = _chunk_dir(stem)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = 0
    with ExitStack() as stack, open(source, newline="") as f:
        reader = csv.reader(f)
        found_header = next(reader, None)
        if found_header != header:
            raise SystemExit(f"{source} has the columns {found_header}, expected {header}.")
        surname = header.index("surname")
        try:
            writers = []
            for chunk in range(chunks):
                writer = csv.writer(stack.enter_context(open(out_dir / f"{chunk}.csv", "w", newline="")))
                writer.writerow(header)                         # every chunk file exists, even if it stays empty
                writers.append(writer)
        except OSError as error:
            if error.errno == errno.EMFILE:
                raise SystemExit(f"Cannot open {chunks} files at once (the limit is set by `ulimit -n`): raise it, or use fewer chunks.")
            raise
        for row in reader:
            writers[chunk_of(row[surname], chunks)].writerow(row)
            rows += 1
    (out_dir / "CHUNKS").write_text(str(chunks))
    return rows


def load_chunk_csv(stem, chunk):
    """{name: [row, ...]} for one chunk's slice of facts.csv or counts.csv (made by split_by_chunk)."""
    path = _chunk_dir(stem) / f"{chunk}.csv"
    if not path.exists():
        raise SystemExit(f"No {path} - run  python3 -m pipeline.s6_assemble --prepare  first.")
    grouped = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            grouped[row["surname"]].append(row)
    return grouped


_ROW_START = '{"surname":"'


def _surname_of(line):
    """The surname a maps.jsonl line is about, without parsing the line (a build row carries a whole GeoJSON): stage 4
    writes every row as {"surname":"<name>","period":...} in that order, and a surname is letters a-z only. A line that
    does not start that way is parsed properly instead, so the shortcut can only ever save time, never be wrong."""
    if line.startswith(_ROW_START):
        end = line.find('"', len(_ROW_START))
        if end > 0:
            return line[len(_ROW_START):end]
    return json.loads(line)["surname"]


def iter_maps_by_name(maps_dir, chunk):
    """(name, [row, ...]) for each name of one chunk's maps.jsonl (stage 4), one name at a time - the file holds
    a name's rows together, names in sorted order, so only one name's maps are ever in memory (a whole chunk of real
    GeoJSON would be a gigabyte or more once parsed). A name that comes back later, or out of order, means the
    file is not what stage 4 writes: stopped, not guessed at, since everything after relies on the order (the
    facts parts must come out sorted for merge_release.py)."""
    path = Path(maps_dir) / f"chunk_{chunk}.jsonl"
    if not path.exists():
        raise SystemExit(f"No {path} - run s4_maps.py first (with a matching --chunks).")
    previous = None
    with open(path) as f:
        for name, lines in itertools.groupby(f, key=_surname_of):
            if previous is not None and name <= previous:
                raise SystemExit(f"{path}: {name!r} comes after {previous!r} - the names in a chunk's maps file are meant to be "
                                 "together and in sorted order, as s4_maps.py writes them.")
            previous = name
            yield name, [json.loads(line) for line in lines]


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true", help="split facts.csv/counts.csv by chunk; run once, before the array job")
    mode.add_argument("--chunk", type=int, help="which chunk this task assembles (0-based); an array job, see pipeline/hpc/stage6.sh")
    parser.add_argument("--chunks", type=int, default=config.RUN_CHUNKS,
                        help="total number of chunks (must match s3_extracts.py/s4_maps.py; default GBNAMES_CHUNKS in run.settings)")
    parser.add_argument("--maps-dir", default=str(config.WORK / "maps"))
    parser.add_argument("--out-dir", default=str(config.WORK / "release"))
    parser.add_argument("--force", action="store_true", help="redo --prepare or this chunk even if it already finished")
    parser.add_argument("--facts-in-names", action="store_true",
                        help="also put the facts in each name's file (data-contract.md's original shape); by default they go to the one facts table only")
    parser.add_argument("--free-maps", action="store_true",
                        help="after a chunk assembles with no failures, delete its work/maps/chunk_N.jsonl (only if storage is tight; cannot be undone)")
    args = parser.parse_args()
    print(config.describe_run(), flush=True)

    if args.prepare:
        for stem, header in (("facts", FACTS_HEADER), ("counts", COUNTS_HEADER)):
            if not args.force and split_current(stem, args.chunks):
                print(f"{stem}: already split into {args.chunks} chunks - skipping. Use --force to redo it.")
                continue
            n = split_by_chunk(stem, header, args.chunks)
            print(f"{stem}: {n:,} rows split into {args.chunks} chunks")
        return

    chunks_marker = _chunk_dir("facts") / "CHUNKS"
    if not chunks_marker.exists() or chunks_marker.read_text().strip() != str(args.chunks):
        raise SystemExit(f"work/facts/chunks/ is not split into {args.chunks} chunks - "
                         "run  python3 -m pipeline.s6_assemble --prepare --chunks " + str(args.chunks))

    out_dir = Path(args.out_dir)
    names_dir = out_dir / "names"
    index_dir = out_dir / "index_parts"
    facts_dir = out_dir / "facts_parts"
    names_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    facts_dir.mkdir(parents=True, exist_ok=True)
    done_marker = out_dir / f"chunk_{args.chunk}.done"
    index_path = index_dir / f"chunk_{args.chunk}.txt"
    facts_path = facts_dir / f"chunk_{args.chunk}.csv"
    maps_path = Path(args.maps_dir) / f"chunk_{args.chunk}.jsonl"
    if done_marker.exists() and not args.force:
        marker_text = done_marker.read_text()
        marker_chunks = re.search(r"chunks=(\d+)", marker_text)
        stale_partitioning = marker_chunks is None or int(marker_chunks.group(1)) != args.chunks
        missing_output = not (index_path.exists() and facts_path.exists())
        # stage 4 or --prepare run again since this chunk was assembled: what it was made from has changed
        inputs = [maps_path, _chunk_dir("facts") / f"{args.chunk}.csv", _chunk_dir("counts") / f"{args.chunk}.csv"]
        outdated = any(p.exists() and p.stat().st_mtime > done_marker.stat().st_mtime for p in inputs)
        if not stale_partitioning and not missing_output and not outdated:
            print(f"chunk {args.chunk} already finished ({done_marker}) - skipping. Use --force to redo it.")
            return
        why = ("it was made under a different --chunks value" if stale_partitioning
               else "its index or facts part is missing even though .done exists" if missing_output
               else "its maps, facts or counts have been made again since")
        print(f"chunk {args.chunk}: {done_marker} exists but {why} - redoing it.")

    stage4_done = maps_path.with_suffix(".done")
    if not stage4_done.exists():
        raise SystemExit(f"Stage 4 has not finished chunk {args.chunk} ({stage4_done} is missing): its maps file may be half written. "
                         "Wait for stage 4 (or run it again), then submit this again.")

    started = time.perf_counter()
    facts_by_name = load_chunk_csv("facts", args.chunk)            # these two are small: the chunk's own slice of each
    counts_by_name = load_chunk_csv("counts", args.chunk)
    maps = iter_maps_by_name(args.maps_dir, args.chunk)            # this is not: one name at a time
    print(f"chunk {args.chunk}: facts and counts loaded in {time.perf_counter() - started:.1f}s", flush=True)

    errors_path = out_dir / f"chunk_{args.chunk}.errors.log"
    written, skipped, failed, facts_rows = [], [], [], []
    with open(errors_path, "w") as errors_file:
        for name, map_rows in maps:
            try:
                bundle = build_bundle(name, map_rows, facts_by_name.get(name, []), counts_by_name.get(name, []),
                                      include_facts=args.facts_in_names)
                rows = facts_table_rows(name, facts_by_name.get(name, [])) if bundle is not None else []
            except Exception:
                failed.append(name)
                errors_file.write(f"=== {name} ===\n{traceback.format_exc()}\n")
                print(f"chunk {args.chunk}: FAILED on {name} (see {errors_path}) - continuing")
                continue
            if bundle is None:
                skipped.append(name)
                continue
            path = names_dir / name[:2] / f"{name}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(bundle, separators=(",", ":"), ensure_ascii=False))
            written.append(name)
            facts_rows.extend(rows)
            if len(written) % 500 == 0:
                print(f"chunk {args.chunk}: {len(written):,} names written, {time.perf_counter() - started:.1f}s elapsed", flush=True)

    with open(facts_path, "w", newline="") as f:
        out = csv.writer(f)
        out.writerow(FACTS_TABLE_HEADER)
        out.writerows(facts_rows)                       # names iterate sorted and each name's facts are sorted: merge_release relies on it
    index_path.write_text("\n".join(written) + ("\n" if written else ""))
    note = ""
    if skipped:
        note += f", {len(skipped)} with no map (not published)"
    if failed:
        note += f", {len(failed)} FAILED (see {errors_path.name}): {', '.join(failed)}"
    done_marker.write_text(f"{len(written)} names, {time.perf_counter() - started:.1f}s, chunks={args.chunks}{note}\n")
    print(f"chunk {args.chunk} done: {len(written):,} names written to {names_dir}{note}")
    if args.free_maps and not failed:
        (Path(args.maps_dir) / f"chunk_{args.chunk}.jsonl").unlink(missing_ok=True)
        print(f"chunk {args.chunk}: work/maps/chunk_{args.chunk}.jsonl deleted (--free-maps)")


if __name__ == "__main__":
    main()
