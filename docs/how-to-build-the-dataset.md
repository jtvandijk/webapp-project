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
  joined). The repository limits were set for the register alone. For a first run with the census ask for much more on the command line (`qsub -l h_rt=06:00:00
  pipeline/hpc/stage1.sh`, and so on for stages 2, 3 and 5), read the times in the logs or from `qacct`, and set the repository values from those afterwards.

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

It reads the two small parish tables and makes one pass over each year's attributes table (about a minute or two per year, no maps and no names involved), changes nothing, and prints what it found; the lines that start with `LOOK` are the ones to read. It shows, per year, the range of parish ids the people carry, how many are id 0 (expected), have no id, or carry an id that is not in the parish table it should use (or is in the *other* table: the sign of the wrong table or column). For the tables it shows repeated ids, ids shared between the two tables, parishes without a name (`-`) or county, counties in capitals, centroids that are missing, at 0,0 or not in metres, and whether the id columns can hold fractional ids such as `200136.3`.

**A problem with a parish table is a `LOOK` only if census people are in the parishes it touches**, and the line says how many, per year (`1901 4,512,345 (14.1%)`). A stray shape that nobody carries is only noted ("no census person is in them"). Each year also has a line "N people (x%) cannot be put on a map: id 0 ..., no id ..., id not in the table ..., parish without a usable location ...", so you can see the whole loss in one place. What the parish tables of the real data hold, from the shapefiles and the old lookup:

- *Shapes that are not parishes.* 34 small shapes (from 0.001 to 1 km², 5.8 km² in all; ids 211512 to 212175 in `conpar1851`, 410374 to 411035 in `conpar1901`, the same shapes in both) have an id that is in no lookup, so no name and no county. Three of them are cut into two rows with the same id: those are the repeated ids. The ids of 1851 to 1911 come from the lookup, so nobody should carry them (the check counts); 1921 people were assigned by point in polygon and might be in one. **Stage 1 stops on a repeated id only if people carry it** (and says how many); otherwise it notes it and goes on.
- *London in the 1901 numbering* (used for 1901, 1911 and 1921) is not a set of parishes but four units (`London 1`, `London 2`, `London 3`, `City of London`, 335 km² in all), each with the parish name `-`. Their people are real, and on the maps they sit at those four centroids. In the places lists they are shown as one place, **London parishes** (`config.UNNAMED_PARISH_LABELS`; change the rule there). Twenty other parishes are also called `-` in the lookup (mostly rural, up to 30 km²); they have no label and are left out of the places lists, and the check says how many people that is.
- *Fractional ids.* Six Scottish parishes have ids like `200136.3` (and `300136.3` in the 1901 numbering). The attributes columns are integers in every year except 1901, so their people carry a whole number and cannot be told from the neighbouring parish; the check gives the most people that could be in the wrong parish (about 5,000 of 32 million in 1901).
- *1911 and 1921 have hardly any id 0.* About 300,000 people in each have no parish id at all (NULL), and almost nobody has id 0 (46 people, the Isle of Man). Stage 1 counts the NULL people with the id-0 people of the other years (`config.CENSUS_NULL_PARISH_IS_NONE`).

**The census surname: `sname_clean_stand`, for every year.** The pipeline reads the census surname from `sname_clean_stand`, the surname as cleaned
by the old project (leading initials, bracketed text and everything after " or " removed, names that are only junk emptied), and then applies
`surname_key()` to it as for the register. The census tables in the TRE are the original backup, which does not have that column, so it is made there,
for every year, by two files in `tools/sql/` (both go in the same folder in the TRE): `census_sname_clean_stand.sql` (the cleaning, as plain SQL) and
`make_sname_clean_stand.sh` (runs it for each year that lacks the column). It needs `psql` and the census settings of `.env`, and nothing else.

```
cd <project folder>
set -a; source .env; set +a                                 # only the database settings; no GBNAMES_PROFILE needed
bash tools/sql/make_sname_clean_stand.sh --list             # which years have the column: changes nothing. Expect "lacks" for all seven
```

Before the first real run, two things about the size. Each year's step rewrites every person of that table, so **while it runs the table needs room for
a second copy of itself** on the disk (the biggest year is the one to look at):

```sql
SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) FROM pg_class WHERE relnamespace = 'census'::regnamespace AND relkind = 'r' ORDER BY 1;
```

And do it **before building the other indexes on that table where you can**: if the recid/source indexes are already there the step still works, but it
is slower (every index is updated for every person) and they come out bloated; then run `REINDEX TABLE census.gb<year>;` afterwards, or drop them before and
build them again after. I could not time this on the real data: expect tens of minutes per year, not seconds.

Then start with one year (1851 is probably the smallest), read what it prints, and do the rest:

```
bash tools/sql/make_sname_clean_stand.sh 1851
nohup bash tools/sql/make_sname_clean_stand.sh > sname_clean.log 2>&1 &     # the other six, one after the other; follow it with:  tail -f sname_clean.log
```

Each year is one transaction: if it stops (an error, a lost connection) that year is left exactly as it was, and running the same command again does the
years that are still missing (a year that has the column is skipped, never redone). For each year it prints three small tables, in this order. Read them:

- **the biggest names the cleaning changed** (raw name, number of people, cleaned name): worth a glance, in case that year has junk that the old rules do not know;
- **people and people_with_no_cleaned_name**: the people whose name the cleaning empties. They are not counted, and stage 1 shows them under "not counted although they should be". Should be a small share; tell me the numbers if it is not;
- **people, with_a_surname, with_a_cleaned_name**: with_a_cleaned_name is with_a_surname minus the emptied names.

When it is done, `--list` says "has sname_clean_stand" for every year. The helper tables it leaves (`census.sname_1851` and so on, the different names of a
year with their cleaning, about a million rows each) are for looking at; the pipeline does not use them. The script has been run on made-up names in
Postgres 16 and gives the same answers as the old function on all of them, but not on the real tables, hence the first year on its own.

The old cleaning has its quirks (only the first dot of a name is turned into a space, so "A. B. SMITH" becomes `bsmith`; digits are only partly removed),
and they are kept on purpose: every year is then cleaned in the same way.

**The surname index goes on this column**, after the step above. The pipeline narrows the database query to the wanted surnames on the column it reads, so

```sql
CREATE INDEX ... ON census.gb<year> ((regexp_replace(lower(sname_clean_stand), '[^a-z]', '', 'g')));
```

An index on `sname` is not used.

**What stage 1 prints for the census** (only when `census` is in `GBNAMES_SOURCES`), one line per year:
`1881: 26,000,000 people; 97.1% counted; 2.3% parish id 0; 0.60% not counted although they should be ...`

- *counted*: the person has a surname, an attributes row, and a parish that is in that year's boundaries. Only these are in the maps and the counts.
- *parish id 0*: **expected, not a fault.** Some people were counted in the census but not in a parish of Great Britain (soldiers, sailors, British citizens in the colonies and protectorates). They are left out on purpose.
- *not counted although they should be*: a parish id other than 0 that is not in the boundaries for that year, no surname, or no attributes row. A few per cent is normal (the boundary files are a clean-up of the original). Above 5% stage 1 says so; above 20% it stops, because the ids then almost certainly belong to other boundaries (say the 1851 ones for 1911).
- *1921 is the one year whose attributes table is read differently:* its parish id is the column `conparid1901`, not `gid`. The ids originally recorded for 1921 do not link to the standardised parishes, so the 1921 records were assigned to the 1901 parishes by point in polygon. `CENSUS_PARISH_COLUMN` in `config.py` says so; the parish names and counties of the places lists come from the parish tables (`parish` and `regcnty` in `spatial.conpar1851` / `conpar1901`), so every census stage needs those tables.
- Stage 1 also stops, and writes nothing, if people carry a parish id that appears twice in a parish table (a repeated id nobody carries is only noted) or if there are more than 1% more attributes rows than people (a person would count twice).

Stages 2 and 3 do not depend on each other, so they can be submitted together; stage 4 needs both, and stage 5 needs
only stage 1 (so it can run beside stages 2 to 4). When a job fails, read the end of its log in `work/logs/`, fix the
cause and submit it again: stages 3 to 5 keep what they finished, and stage 4 skips finished chunks. For the full run of
stage 5 ask for more time on the command line (`qsub -l h_rt=03:00:00 pipeline/hpc/stage5.sh`) until you have measured it.
