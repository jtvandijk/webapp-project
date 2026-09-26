# How to build the dataset

A working guide: what each step does, the commands in order, where every setting lives, how to look at a few
names before running everything, and how to follow a job. It assumes the census tables are already checked and
ready - see [census-data-checks.md](census-data-checks.md) for that (one-time work, done once after a data load, not
part of an ordinary run). It describes what is there now. For *why* things are as they are, see
[pipeline.md](pipeline.md); for the file format the website reads, [data-contract.md](data-contract.md).

Everything runs from the project folder (the one that contains `pipeline/`, `work/`, `.env` and `run.settings`).
For a build from scratch, with a check between the stages, go straight to section 10.

## 1. Every session in the TRE

```
conda activate gbnames
cd <project folder>
set -a; source .env; source run.settings; set +a   # .env: database settings incl. passwords (not in git); run.settings: the run choices (in git)
export GBNAMES_PROFILE=tre           # without this the code uses the FAKE database
```

The qsub scripts do the same thing themselves, so this is only for commands you type. Because of `run.settings`, a
typed `python3 -m pipeline.s5_facts --names smith` uses the same sources as the qsub jobs; a flag still overrides it.

## 2. The steps

| # | Step | What it does | Reads | Writes (in `work/`) | How it runs | Measured |
|---|---|---|---|---|---|---|
| 0 | Neighbourhood tables | Turn the downloads in `raw-indicators/` into five lookup tables and load them into the database | downloads (on your laptop) | `neighbourhood/*.csv` | laptop: `python3 tools/prep_neighbourhood.py`, then in the TRE `nbhd_tables ddl` + psql | done once, redo when a table changes |
| 1 | Counts | Bearers of every surname in every year; the list of names that get a page | register, census | `counts.csv`, `names.csv` | `qsub pipeline/hpc/stage1.sh` | about 27 min, both sources, full run |
| 2 | Surfaces | One smoothed density of *everybody* per map period, for weighting the maps | register, census | `surfaces/<period>.npy` | `qsub pipeline/hpc/stage2.sh` | about 12 min, both sources, full run (15 periods) |
| 3 | Extracts | One query per period pulls where every listed name's bearers are; split into chunks by name | register, census | `chunks/<period>/<n>.csv`, `chunks/CHUNKS` | `qsub pipeline/hpc/stage3.sh` | about 21 min, both sources, a 5,000-name sample; not yet measured on the full list |
| 4 | Maps | The map of every name and period, no database access; an array job, one task per chunk | steps 2 and 3 | `maps/chunk_<n>.jsonl`, `stats/chunk_<n>.csv` | `qsub -t 1-<GBNAMES_CHUNKS> pipeline/hpc/stage4.sh`, then `python3 -m pipeline.merge_stats` | about 2-3 min per chunk, 200 chunks, both sources, a 5,000-name sample |
| 5 | Facts | Neighbourhood classifications, top neighbourhoods, ethnicity, forenames, and from the census historic forenames and parishes | step 1, register, census, the tables of step 0 | `facts/facts.csv`, `facts/report.txt` | `qsub pipeline/hpc/stage5.sh` | about 23 min, both sources, a 5,000-name sample; not yet measured on the full list |
| 6 | Assemble | Turn stage 4's maps and stage 5's facts into one JSON file per surname (`docs/data-contract.md`); the search index; `manifest.json`; the real Scotland mask | step 1 (counts.csv), steps 4 and 5 | `release/names/<xx>/<name>.json` (counts and maps), `release/facts.csv` (all the facts, one row per name and fact), `release/index/<xx>.json`, `release/manifest.json`, `release/masks/scotland.json` | once: `python3 -m pipeline.s6_assemble --prepare`, then `qsub -t 1-<GBNAMES_CHUNKS> pipeline/hpc/stage6.sh`, then `python3 -m pipeline.merge_release` | built, tested on fake data; not yet run on real output. `lookups.json` and *why* a period has no map (`mapNotes`) are deliberately not built yet (docs/pipeline.md) |

"Register" and "census" are two different databases; a step only opens the ones `GBNAMES_SOURCES` (in `run.settings`) names -
currently both.

The order matters: 1, then 2 and 3, then 4; 5 needs only 1 (and the tables). A finished step can be re-run
without redoing the ones before it.

## 3. Where every setting lives

Two files hold what changes; everything else is in `config.py`.

| Setting | Where | Notes |
|---|---|---|
| Database host, user, password | `.env` (`_LCR` = register, `_ICEM` = census) | not in git. Read by every qsub script (except stage 4, which needs no database) |
| **Which sources** (`register`, `census`) | `GBNAMES_SOURCES` in **`run.settings`** | every stage; `--sources` overrides it for one typed command |
| **Number of chunks** | `GBNAMES_CHUNKS` in `run.settings` | stages 3 and 4, one number for both. Stage 4 is submitted as `qsub -t 1-<that number>`; its script stops at once if the range ends anywhere else |
| **A sample** (only the first N names) | `GBNAMES_LIMIT` in `run.settings` | stages 3 and 5; empty = every name. Not applied to `s5_facts --names`, which asks for names by name |
| **Which facts** | `GBNAMES_FACTS` in `run.settings` | stage 5; empty = all facts of the sources |
| **Census years in use** | `GBNAMES_CENSUS_YEARS` in `run.settings` | every stage; leave a year out while its data is not loaded |
| Memory and time requested | `#$ -l h_vmem=...` and `#$ -l h_rt=...` at the top of each `pipeline/hpc/stage*.sh` | SGE reads these before any script runs, so they cannot come from a settings file. Repository values (2026-09-26, register + census; stage 1 and 2 measured on a real full run, 1,591s/11.3G and 738s/126M; stages 3 and 5 scaled up with headroom from a 5,000-name sample, not yet measured on the full list): stage 1: 16G, 2 h; stage 2: 2G, 30 min; stage 3: 6G, 2 h; stage 4: 2G, 1 h; stage 5: 16G, 3 h. Tighten 3 and 5 once `qacct` gives their real full-list numbers. To change one for a single run, use the command line: `qsub -l h_rt=01:00:00 pipeline/hpc/stage5.sh` |
| Databases, table and column names, years, thresholds, all map and fact rules | `pipeline/config.py` | one file: edit this, not the code |
| Output folder | `--out-dir` (steps 2 to 5); defaults are in the table in section 6 | |

`run.settings` is a plain list of `NAME="value"` lines with a comment above each. It is in git (it holds nothing
secret), so a change to it is a commit like any other. A typo in it (say `register` written `registers`) stops the run
with a message that names the setting. Every stage prints the settings it is running with, first thing:
`run settings: sources register; chunks 200; names all; ...`.

## 4. Looking at a few names first

Both previews read the real database (they open only the databases they need), so run them where the environment
of section 1 is set. They are light enough for the login node for a handful of names; anything larger goes through
qsub.

### Maps: `python3 -m pipeline.preview`

```
python3 -m pipeline.preview --names smith macdonald davies --sources register      # all eight register map years
python3 -m pipeline.preview --names smith --periods 1901 1911 1921 2026            # chosen periods
```

Writes `work/preview_maps/preview<N>.html` (the next number; earlier ones are kept; the page says which command made
it). It is one file with the maps in it, so it opens with no internet. Below the maps is a table of bearers,
bandwidth and time per map. A map that was left out says why.

| Flag | What it does |
|---|---|
| `--names a b c` | surname keys (lower case, letters only: `obrien`, not `O'Brien`) |
| `--sources register` / `census` | use every map year of these sources as the periods |
| `--periods 1901 2026 ...` | exactly these periods (`1851 1861 1881 1891 1901 1911 1921`, `1997 2000 2005 2010 2015 2020 2025 2026`); overrides `--sources` |
| `--out file.html` | write to this file instead of the next numbered one |
| `--refresh-cache` | fetch from the database again; use after a new register or census load (what was fetched is kept in `work/cache/`, so adding a name fetches only that name) |

These change *how the maps are drawn*, to compare settings. They are for calibration, not for normal use; each
overrides the value in `config.py` for this preview only:

| Flag | What it does |
|---|---|
| `--variants 0.5/mass 1/mass` | several settings side by side: `<weighting power>/<level mode>` or `<power>/mass:0.85,0.65,0.4` |
| `--auto-level-mass` | each name's own level cut-offs (the default when `--variants` is not given) |
| `--min-area` `--min-blob-share` `--min-blob-bearers` | how small a blob or hole may be before it is dropped |
| `--smooth` | fill gaps and notches narrower than twice this many metres |
| `--weight-ceiling` `--population-bandwidth` | the population weighting (see `config.py`) |

### Facts: `python3 -m pipeline.s5_facts --names ...`

```
python3 -m pipeline.s5_facts --sources register --names smith macdonald davies patel nowak
python3 -m pipeline.s5_facts --sources census --census-years 1851 1861 1881 1891 1901 1911 --names smith macdonald
```

Writes `work/preview_facts/facts.csv` (always the latest) and keeps each run as `facts<N>.csv` and `report<N>.txt`. The
report says how many names got each fact and how much of the data was covered.

| Flag | What it does |
|---|---|
| `--names a b c` | only these names, which must be in `names.csv` |
| `--limit N` | the first N names of `names.csv` (a sample run; not with `--names`) |
| `--sources register census` | which databases and facts (default both) |
| `--census-years 1851 ...` | which census years to pool (default all; leave 1921 out until it is loaded) |
| `--facts oac imd ...` | only some facts: `oac loac ahah imd fpc places eth forenames forenames_census parishes` |
| `--refresh` | query again even where a saved extract exists (after new data or a new table) |
| `--compute-only` | no database: redo the calculation from the saved extracts, with the same names |
| `--out-dir dir` | write elsewhere (default `work/facts`, or `work/preview_facts` for `--names`) |

Reading `facts.csv`: `value` is the headline, `detail` the rest (shares, lists); see "Stage 5 output" in
[pipeline.md](pipeline.md).

### The assembled release: `python3 -m pipeline.preview_web`

Once stage 6 has run (even just for a chunk or two), a quick look at what it actually wrote - no database,
no computation, so it can run anywhere stage 6 itself ran:

```
python3 -m pipeline.preview_web --names smith macdonald davies
python3 -m pipeline.preview_web --sample 20              # a random sample of whatever is already assembled
```

Writes `work/preview_web/preview<N>.html`: a small picture of each of a name's maps (which periods it has,
and whether one is a copy of another year's), and its facts (read from `release/facts.csv`) and counts as plain tables. `--names` on a name
with no assembled file yet is just noted, not an error.

To see what an assembled release and this page look like before there is any real output (or after changing stage 6
or the maps), on your own computer with no database: `python3 tools/build_demo_release.py` builds one from the fake
data in `work/demo_release/` (about 15 seconds) and writes `work/demo_release/preview_web/preview.html`. Made-up names
and shapes, real code and file formats. It cannot reach the real database, whatever `GBNAMES_PROFILE` says.

## 5. Following a qsub job

```
qstat                                         # your jobs: qw = waiting, r = running; the job leaves the list when it is done
tail -f work/logs/gbnames_stage5.o<jobid>     # its output, as it prints (the job id is printed when you qsub)
qacct -j <jobid>                              # after it has finished, if the cluster keeps accounting: wall-clock time (ru_wallclock) and memory used (maxvmem)
```

- **Done?** The job is gone from `qstat`, and the end of the log shows the report and a line `N facts in ...`. A
  `Traceback` in the log means it failed; the saved extracts are kept, so submitting it again carries on.
- **Total time.** Stage 5 prints each query's time as it goes and, at the end, `time: ... in total` (also the last line
  of `work/facts/report.txt`). For any stage `qacct -j` (where available) gives the total and the memory it really used,
  which is what to base the next `h_rt` and `h_vmem` on; otherwise add up the times in the log.
- **The log looks empty?** Python buffers its output when it is not a terminal, so a log could stay empty for a long time
  while the job was fine. Every stage script now switches this off (`PYTHONUNBUFFERED=1`), so the log fills as the job runs.
- Array jobs (stage 4) write one log per task: `work/logs/gbnames_stage4.o<jobid>.<task>`.
- **Stopped by its time limit (`h_rt`) or memory limit (`h_vmem`)?** The scheduler ends the job without a word: no `Traceback`, the log just stops, and
  the closing line below is missing. The job is gone from `qstat`; `qacct -j <jobid>` (where available) usually shows `exit_status 137` and, for the time limit,
  a `ru_wallclock` just over `h_rt` (for memory, a `maxvmem` near what was asked). What a stage leaves behind, and what a second `qsub` does:

  | Stage | Closing line of the log | If it was stopped |
  |---|---|---|
  | 1 | `names with a map, by period: ...` | **Nothing is kept**: `counts.csv` and `names.csv` are written at the very end. The whole stage runs again, so give it enough time |
  | 2 | `N surfaces written to work/surfaces` | Each period's file is kept, but a second `qsub` **starts again from the first period** (census periods come first) and is stopped at the same place unless it has more time. `manifest.csv` only exists after a full run |
  | 3 | `N names, N chunks, N periods written to work/chunks` | The same, and `work/chunks/CHUNKS` is only written at the very end: a stopped run leaves a mix of new and old files, so run `bash pipeline/hpc/clean.sh --stage34` before running it again |
  | 4 | `chunk N done: ...` in every task's log | Finished chunks are kept (`ls work/maps/*.done \| wc -l` says how many); submit the same `qsub -t 1-N` again and only the missing ones are done |
  | 5 | `N facts in ...` and `time: ... in total` | Every saved query is kept; submit it again and it carries on from there |

- **With the census on, the times change.** Every census period is a pass over a table of about 30 million people (person table, attributes table and parish table
  joined). The repository limits (section 3) already allow for this - stages 1 and 2 from a real full run, stages 3 and 5 estimated with headroom from a
  5,000-name sample, not yet measured on the full name list. Read the times in the logs or from `qacct` and tighten 3 and 5 once you have real numbers.

## 6. What is in `work/`

Everything here is written by the pipeline and ignored by git. Deleting a folder only costs the time to rebuild it.

| Path | Made by | Contains |
|---|---|---|
| `counts.csv`, `names.csv` | step 1 | bearers per name and year; the names that get a page |
| `surfaces/` | step 2 | the population surface of each period |
| `chunks/` | step 3 | the points of each name, split into chunks (and `CHUNKS`, the number used) |
| `maps/`, `stats/`, `stats.csv` | step 4, merge | one line per name and period (GeoJSON), and its statistics |
| `facts/` | step 5 | `facts.csv`, `report.txt`, `by_fact/`, and `extract/` (the saved queries) |
| `facts/chunks/`, `counts/chunks/` | step 6's `--prepare` | `facts.csv`/`counts.csv` split by chunk, so an array task reads only its own slice |
| `release/` | step 6, merge | `names/<xx>/<name>.json` (counts and maps), `facts.csv` (the facts, one table), `index_parts/` and `facts_parts/` (each chunk's own name list and facts), `index/`, `manifest.json`, `masks/scotland.json`, and per-chunk `.done`/`errors.log` |
| `preview_maps/`, `cache/` | `preview.py` | numbered preview pages; the data they fetched |
| `preview_facts/` | `s5_facts --names` | facts of a few names, each run kept |
| `preview_web/` | `preview_web.py` | numbered preview pages of already-assembled release files |
| `neighbourhood/` | `tools/prep_neighbourhood.py` | the five lookup tables (**one is safeguarded data: never leaves this machine or the TRE**) |
| `logs/` | qsub | one log per job (create it once: `mkdir -p work/logs`, before the first qsub) |
| `fake.db`, `fake_truth.json` | `fake_data.py` | the fake database, for development on a laptop |

To start a stage from clean: `bash pipeline/hpc/clean.sh` (stages 3 and 4; it asks about 1 and 2), `--all`, or
`--facts` (stage 5 only). Saved extracts of stage 5 do not notice new data: use `--refresh` after a new load.

## 7. When something changes, what to run again

| What changed | Run again |
|---|---|
| A new register or census load | 1, then 2, 3, 4 and 5 (`--refresh`), then 6; check what step 1 prints: the postcode match rate (register) and how the census people divide up (census) |
| The list of names (thresholds in `config.py`) | 1, then 3, 4, 5, 6 |
| The grid (`GRID`) | 2, 3 and 4, then 6 |
| The smoothing of the population (`POPULATION_BANDWIDTH_M`) | 2, then 4, then 6 |
| How a map is drawn (bandwidth, weighting, levels, smoothing, blob rules) | 4 again (`--force`, or `clean.sh --stage34`), then 6 |
| A new version of a neighbourhood table | 0 (load it), then 5 with `--facts <that fact> --refresh`, then 6 |
| A rule for the facts (`FACT_MIN_IN_CATEGORY`, list lengths) | 5 with `--compute-only`, then 6 |
| Step 6's own field mapping, or `manifest.json`/masks (`s6_assemble.py`, `merge_release.py`) | 6 only - `python3 -m pipeline.s6_assemble --prepare --force` first if facts.csv/counts.csv did not themselves change (a plain re-run skips `--prepare` when it is already current), then every chunk with `--force`, then `merge_release.py` |

## 8. What to put in the TRE when code changes

The TRE has no git, so files go across one at a time. Only these are needed there:

- `pipeline/*.py` and `pipeline/hpc/*.sh` (not `tests/`, not `reference/`, not `fake_data.py` unless you use it there),
  and `run.settings` in the project folder;
- `pipeline/reference/*.geojson` (the coastline used for the maps; it does not change);
- the neighbourhood tables (`work/neighbourhood/nbhd_*.csv`) when they change.

Not needed: `docs/`, most of `tools/` (they run on your laptop, the exception being `tools/sql/`, which runs in the
TRE with `psql` - one-time, see [census-data-checks.md](census-data-checks.md)), `site/`, `gbnames/`, `data-prep/`, `raw-indicators/`.
After a change, the list of files that differ is `git diff --name-only <last commit you copied from> HEAD -- pipeline`.
Replace files only when no job of yours is queued (a queued job starts with whatever is there).

## 9. What is still not standardised

Most of what was spread out is now in one place (`run.settings`, section 3). What is left, so nothing surprises you:

1. **Memory and time are inside each script** (SGE needs them there), so the copies in the TRE can drift from the
   repository if you edit them by hand. Prefer the command line for a one-off change (`qsub -l h_rt=...`), and change the
   script in the repository, then upload it, for a lasting one.
2. **No single command builds everything**, on purpose: each stage is submitted by hand so there is a check between
   stages (section 10).
3. `preview.py` names its folders `preview_maps` and `cache`, stage 5 uses `preview_facts` and `facts`; consistent enough,
   but the maps cache is not under the previews it belongs to.

## 10. A build, start to finish (register and census)

The census tables need to be checked and prepared once before this - see
[census-data-checks.md](census-data-checks.md); done for the current data load (dated there). This section assumes
that is done and just runs the pipeline.

`run.settings` as shipped is a full run of both sources, every name: `GBNAMES_SOURCES="register census"`,
`GBNAMES_CHUNKS=200`, `GBNAMES_LIMIT=""`. For a rehearsal on a sample instead, set `GBNAMES_LIMIT=5000` and
`GBNAMES_CHUNKS=40` (the same number of names per chunk) - and remember a sample taken this way is `work/names.csv`'s
first N names in alphabetical order, so it is not a representative slice of the real name list (early letters skew
towards old surnames with few or no contemporary bearers); it is fine for checking the pipeline runs, not for judging
typical coverage or timing from.

**Once, after a fresh upload of the project folder**

```
mkdir -p work/logs
```

and put `.env` (yours), `run.settings`, `pipeline/` and, if the neighbourhood tables are not in the database yet,
`work/neighbourhood/nbhd_*.csv` in place. The neighbourhood tables live in the database, so they survive a wipe of the
HPC folder; load them only if they are missing (section 2, step 0).

**Then, one stage at a time, looking before you go on**

| Stage | Submit | Look at, before the next |
|---|---|---|
| 1 | `qsub pipeline/hpc/stage1.sh` | the log: the postcode match rate (at least 95%), the number of names that reach the threshold; `work/names.csv` exists; one line per census year (see below) |
| 2 | `qsub pipeline/hpc/stage2.sh` | one file per map period in `work/surfaces/` (15: 8 register, 7 census) |
| 3 | `qsub pipeline/hpc/stage3.sh` | the log's line per period; `work/chunks/CHUNKS` holds the chunk number you set |
| 4 | `qsub -t 1-200 pipeline/hpc/stage4.sh` (the range ends at `GBNAMES_CHUNKS`), then `python3 -m pipeline.merge_stats` | every chunk finished: as many `work/maps/*.done` as chunks; `merge_stats` warns if a stats file is missing |
| 5 | `qsub pipeline/hpc/stage5.sh` | `work/facts/report.txt`: the "bearers covered" column and the ethnicity codes it did not recognise; the time at the end |
| 6 | `python3 -m pipeline.s6_assemble --prepare` (once, on the login node), then `qsub -t 1-200 pipeline/hpc/stage6.sh`, then `python3 -m pipeline.merge_release` | as many `work/release/chunk_*.done` as chunks; `merge_release`'s printed total; a quick look with `python3 -m pipeline.preview_web --sample 20` |

**What stage 1 prints for the census** (only when `census` is in `GBNAMES_SOURCES`), one line per year:
`1881: 26,000,000 people; 97.1% counted; 2.3% parish id 0; 0.60% not counted although they should be ...`

- *counted*: the person has a surname, an attributes row, and a parish that is in that year's boundaries. Only these are in the maps and the counts.
- *parish id 0*: **expected, not a fault.** Some people were counted in the census but not in a parish of Great Britain (soldiers, sailors, British citizens in the colonies and protectorates). They are left out on purpose. In 1911 and 1921 this same group has no parish id at all (NULL) instead of 0 - stage 1 folds them into this same percentage (`config.CENSUS_NULL_PARISH_IS_NONE`), so the printed figure means the same thing in every year.
- *not counted although they should be*: a parish id other than 0 that is not in the boundaries for that year, no surname, or no attributes row. A few per cent is normal (the boundary files are a clean-up of the original). Above 5% stage 1 says so; above 20% it stops, because the ids then almost certainly belong to other boundaries (say the 1851 ones for 1911).
- *1921 is the one year whose attributes table is read differently:* its parish id is the column `conparid1901`, not `gid`. The ids originally recorded for 1921 do not link to the standardised parishes, so the 1921 records were assigned to the 1901 parishes by point in polygon. `CENSUS_PARISH_COLUMN` in `config.py` says so; the parish names and counties of the places lists come from the parish tables (`parish` and `regcnty` in `spatial.conpar1851` / `conpar1901`), so every census stage needs those tables.
- Stage 1 also stops, and writes nothing, if people carry a parish id that appears twice in a parish table (a repeated id nobody carries is only noted) or if there are more than 1% more attributes rows than people (a person would count twice).

Stages 2 and 3 do not depend on each other, so they can be submitted together; stage 4 needs both, and stage 5 needs
only stage 1 (so it can run beside stages 2 to 4). When a job fails, read the end of its log in `work/logs/`, fix the
cause and submit it again: stages 3 to 5 keep what they finished, and stage 4 skips finished chunks. Stage 3 and 5's
repository time limits (section 3) are estimates for the full name list; if one is not enough, override it for that
run only (`qsub -l h_rt=04:00:00 pipeline/hpc/stage3.sh`) and, once `qacct` gives the real number, tighten it in the
script for next time.
