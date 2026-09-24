# How to build the dataset

A working guide: what each step does, the commands in order, where every setting lives, how to look at a few
names before running everything, and how to follow a job. It describes what is there now. For *why* things are as
they are, see [pipeline.md](pipeline.md); for the file format the website reads, [data-contract.md](data-contract.md).

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
| 1 | Counts | Bearers of every surname in every year; the list of names that get a page | register, census | `counts.csv`, `names.csv` | `qsub pipeline/hpc/stage1.sh` | not measured yet; run once per data load |
| 2 | Surfaces | One smoothed density of *everybody* per map period, for weighting the maps | register, census | `surfaces/<period>.npy` | `qsub pipeline/hpc/stage2.sh` | minutes |
| 3 | Extracts | One query per period pulls where every listed name's bearers are; split into chunks by name | register, census | `chunks/<period>/<n>.csv`, `chunks/CHUNKS` | `qsub pipeline/hpc/stage3.sh` | about 5 min, 5,000 names, register |
| 4 | Maps | The map of every name and period, no database access; an array job, one task per chunk | steps 2 and 3 | `maps/chunk_<n>.jsonl`, `stats/chunk_<n>.csv` | `qsub -t 1-<GBNAMES_CHUNKS> pipeline/hpc/stage4.sh`, then `python3 -m pipeline.merge_stats` | about 5 min, 40 chunks, register |
| 5 | Facts | Neighbourhood classifications, top neighbourhoods, ethnicity, forenames, and from the census historic forenames and parishes | step 1, register, census, the tables of step 0 | `facts/facts.csv`, `facts/report.txt` | `qsub pipeline/hpc/stage5.sh` | 8 names about 50 s; 5,000 names about 20 min (mostly the ethnicity query) |
| 6 | Assemble | Join maps and facts into the release, check it | steps 4 and 5 | not built yet | | |

"Register" and "census" are two different databases; a step only opens the ones `GBNAMES_SOURCES` (in `run.settings`) names.
Until the census database is ready every step is register-only.

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
| Memory and time requested | `#$ -l h_vmem=...` and `#$ -l h_rt=...` at the top of each `pipeline/hpc/stage*.sh` | SGE reads these before any script runs, so they cannot come from a settings file. Repository values: stage 1: 16G, 2 h (a guess); stages 2 and 3: 2G, 30 min; stage 4: 2G, 1 h; stage 5: 16G, 1 h. To change one for a single run, use the command line: `qsub -l h_rt=03:00:00 pipeline/hpc/stage5.sh` |
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

## 6. What is in `work/`

Everything here is written by the pipeline and ignored by git. Deleting a folder only costs the time to rebuild it.

| Path | Made by | Contains |
|---|---|---|
| `counts.csv`, `names.csv` | step 1 | bearers per name and year; the names that get a page |
| `surfaces/` | step 2 | the population surface of each period |
| `chunks/` | step 3 | the points of each name, split into chunks (and `CHUNKS`, the number used) |
| `maps/`, `stats/`, `stats.csv` | step 4, merge | one line per name and period (GeoJSON), and its statistics |
| `facts/` | step 5 | `facts.csv`, `report.txt`, `by_fact/`, and `extract/` (the saved queries) |
| `preview_maps/`, `cache/` | `preview.py` | numbered preview pages; the data they fetched |
| `preview_facts/` | `s5_facts --names` | facts of a few names, each run kept |
| `neighbourhood/` | `tools/prep_neighbourhood.py` | the five lookup tables (**one is safeguarded data: never leaves this machine or the TRE**) |
| `logs/` | qsub | one log per job (create it once: `mkdir -p work/logs`, before the first qsub) |
| `fake.db`, `fake_truth.json` | `fake_data.py` | the fake database, for development on a laptop |

To start a stage from clean: `bash pipeline/hpc/clean.sh` (stages 3 and 4; it asks about 1 and 2), `--all`, or
`--facts` (stage 5 only). Saved extracts of stage 5 do not notice new data: use `--refresh` after a new load.

## 7. When something changes, what to run again

| What changed | Run again |
|---|---|
| A new register or census load | 1, then 2, 3, 4 and 5 (`--refresh`); check what step 1 prints: the postcode match rate (register) and how the census people divide up (census) |
| The list of names (thresholds in `config.py`) | 1, then 3, 4, 5 |
| The grid (`GRID`) | 2, 3 and 4 |
| The smoothing of the population (`POPULATION_BANDWIDTH_M`) | 2, then 4 |
| How a map is drawn (bandwidth, weighting, levels, smoothing, blob rules) | 4 again (`--force`, or `clean.sh --stage34`) |
| A new version of a neighbourhood table | 0 (load it), then 5 with `--facts <that fact> --refresh` |
| A rule for the facts (`FACT_MIN_IN_CATEGORY`, list lengths) | 5 with `--compute-only` |

## 8. What to put in the TRE when code changes

The TRE has no git, so files go across one at a time. Only these are needed there:

- `pipeline/*.py` and `pipeline/hpc/*.sh` (not `tests/`, not `reference/`, not `fake_data.py` unless you use it there),
  and `run.settings` in the project folder;
- `pipeline/reference/*.geojson` (the coastline used for the maps; it does not change);
- the neighbourhood tables (`work/neighbourhood/nbhd_*.csv`) when they change.

Not needed: `docs/`, `tools/` (they run on your laptop), `site/`, `gbnames/`, `data-prep/`, `raw-indicators/`.
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

## 10. A register-only build, start to finish

Set `run.settings` first: `GBNAMES_SOURCES="register"`, `GBNAMES_CHUNKS=200`, `GBNAMES_LIMIT=""` (every name). For a
rehearsal on a sample instead, set `GBNAMES_LIMIT=5000` and `GBNAMES_CHUNKS=40` (the same number of names per chunk).

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
| 1 | `qsub pipeline/hpc/stage1.sh` | the log: the postcode match rate (at least 95%), the number of names that reach the threshold; `work/names.csv` exists. With the census on: one line per year (see below) |
| 2 | `qsub pipeline/hpc/stage2.sh` | one file per register map period in `work/surfaces/` (eight) |
| 3 | `qsub pipeline/hpc/stage3.sh` | the log's line per period; `work/chunks/CHUNKS` holds the chunk number you set |
| 4 | `qsub -t 1-200 pipeline/hpc/stage4.sh` (the range ends at `GBNAMES_CHUNKS`), then `python3 -m pipeline.merge_stats` | every chunk finished: as many `work/maps/*.done` as chunks; `merge_stats` warns if a stats file is missing |
| 5 | `qsub pipeline/hpc/stage5.sh` | `work/facts/report.txt`: the "bearers covered" column and the ethnicity codes it did not recognise; the time at the end |

**Before stage 1 for the census: check the parish ids.** Once the parish tables (`spatial.conpar1851`, `spatial.conpar1901`) are loaded:

```
python3 -m pipeline.check_parishes | tee work/parish_check.txt
python3 -m pipeline.check_parishes --lookup conpar_lookup.csv     # also compare with the old lookup file
```

It reads the two small parish tables and makes one pass over each year's attributes table (about a minute or two per year, no maps and no names involved), changes nothing, and prints what it found; the lines that start with `LOOK` are the ones to read. It shows, per year, the range of parish ids the people carry, how many are id 0 (expected), have no id, or carry an id that is not in the parish table it should use (or is in the *other* table: the sign of the wrong table or column). For the tables it shows repeated ids, ids shared between the two tables, parishes without a name (`-`), counties in capitals, centroids that are missing, at 0,0 or not in metres, and whether the id columns can hold fractional ids such as `200136.3`.

**Also before stage 1 for the census: the surnames.** The pipeline reads the raw surname (`sname`) and standardises it itself. The old project made a
cleaned column, `sname_clean_stand`, with a SQL function that did more: it moved bracketed text and everything after " or " out of the name,
removed leading initials, and emptied names that were mostly punctuation. To see how much that matters:

```
python3 -m pipeline.check_surnames | tee work/surname_check.txt
```

It makes one pass over each year's census table (a year without the cleaned column is skipped) and prints, per year, the share of people who are
under a different name, which kind of difference it is, and the biggest cases with both readings. If the shares are small (under about 1%) the raw
reading is fine; if they are not, the old cleaning should be rebuilt in `pipeline/names.py`.

**What stage 1 prints for the census** (only when `census` is in `GBNAMES_SOURCES`), one line per year:
`1881: 26,000,000 people; 97.1% counted; 2.3% parish id 0; 0.60% not counted although they should be ...`

- *counted*: the person has a surname, an attributes row, and a parish that is in that year's boundaries. Only these are in the maps and the counts.
- *parish id 0*: **expected, not a fault.** Some people were counted in the census but not in a parish of Great Britain (soldiers, sailors, British citizens in the colonies and protectorates). They are left out on purpose.
- *not counted although they should be*: a parish id other than 0 that is not in the boundaries for that year, no surname, or no attributes row. A few per cent is normal (the boundary files are a clean-up of the original). Above 5% stage 1 says so; above 20% it stops, because the ids then almost certainly belong to other boundaries (say the 1851 ones for 1911).
- *1921 is the one year whose attributes table is read differently:* its parish id is the column `conparid1901`, not `gid`. The ids originally recorded for 1921 do not link to the standardised parishes, so the 1921 records were assigned to the 1901 parishes by point in polygon. `CENSUS_PARISH_COLUMN` in `config.py` says so; the parish names and counties of the places lists come from the parish tables (`parish` and `regcnty` in `spatial.conpar1851` / `conpar1901`), so every census stage needs those tables.
- Stage 1 also stops, and writes nothing, if a parish id appears twice in a parish table or if there are more than 1% more attributes rows than people (a person would count twice).

Stages 2 and 3 do not depend on each other, so they can be submitted together; stage 4 needs both, and stage 5 needs
only stage 1 (so it can run beside stages 2 to 4). When a job fails, read the end of its log in `work/logs/`, fix the
cause and submit it again: stages 3 to 5 keep what they finished, and stage 4 skips finished chunks. For the full run of
stage 5 ask for more time on the command line (`qsub -l h_rt=03:00:00 pipeline/hpc/stage5.sh`) until you have measured it.
