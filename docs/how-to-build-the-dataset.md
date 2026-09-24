# How to build the dataset

A working guide: what each step does, the commands in order, where every setting lives, how to look at a few
names before running everything, and how to follow a job. It describes what is there now. For *why* things are as
they are, see [pipeline.md](pipeline.md); for the file format the website reads, [data-contract.md](data-contract.md).

Everything runs from the project folder (the one that contains `pipeline/`, `work/` and `.env`).

## 1. Every session in the TRE

```
conda activate gbnames
cd <project folder>
set -a; source .env; set +a          # database settings, incl. passwords: PGHOST_LCR, PGHOST_ICEM, ...
export GBNAMES_PROFILE=tre           # without this the code uses the FAKE database
```

The qsub scripts do the same thing themselves, so this is only for commands you type.

## 2. The steps

| # | Step | What it does | Reads | Writes (in `work/`) | How it runs | Measured |
|---|---|---|---|---|---|---|
| 0 | Neighbourhood tables | Turn the downloads in `raw-indicators/` into five lookup tables and load them into the database | downloads (on your laptop) | `neighbourhood/*.csv` | laptop: `python3 tools/prep_neighbourhood.py`, then in the TRE `nbhd_tables ddl` + psql | done once, redo when a table changes |
| 1 | Counts | Bearers of every surname in every year; the list of names that get a page | register, census | `counts.csv`, `names.csv` | typed directly (no qsub script yet) | run once per data load |
| 2 | Surfaces | One smoothed density of *everybody* per map period, for weighting the maps | register, census | `surfaces/<period>.npy` | `qsub pipeline/hpc/stage2.sh` | minutes |
| 3 | Extracts | One query per period pulls where every listed name's bearers are; split into chunks by name | register, census | `chunks/<period>/<n>.csv`, `chunks/CHUNKS` | `qsub pipeline/hpc/stage3.sh` | about 5 min, 5,000 names, register |
| 4 | Maps | The map of every name and period, no database access; an array job, one task per chunk | steps 2 and 3 | `maps/chunk_<n>.jsonl`, `stats/chunk_<n>.csv` | `qsub -t 1-<CHUNKS> pipeline/hpc/stage4.sh`, then `python3 -m pipeline.merge_stats` | about 5 min, 40 chunks, register |
| 5 | Facts | Neighbourhood classifications, top neighbourhoods, ethnicity, forenames, and from the census historic forenames and parishes | step 1, register, census, the tables of step 0 | `facts/facts.csv`, `facts/report.txt` | `qsub pipeline/hpc/stage5.sh` | 8 names about 50 s; 5,000 names: see the log |
| 6 | Assemble | Join maps and facts into the release, check it | steps 4 and 5 | not built yet | | |

"Register" and "census" are two different databases; a step only opens the ones its `SOURCES` setting names.
Until the census database is ready every step is register-only.

The order matters: 1, then 2 and 3, then 4; 5 needs only 1 (and the tables). A finished step can be re-run
without redoing the ones before it.

## 3. Where every setting lives

This is the part that is spread out. Nothing is hidden, but you have to know where to look.

| Setting | Where | Notes |
|---|---|---|
| Which databases and tables, column names, years, thresholds, all map and fact rules | `pipeline/config.py` | one file: edit this, not the code |
| Database host, user, password | `.env` (`_LCR` = register, `_ICEM` = census) | read by every script and every qsub script |
| Which sources (`register`, `census`) | `SOURCES=` **inside** each of `stage2.sh`, `stage3.sh`, `stage4.sh`, `stage5.sh`; or `--sources` when typing | must be the same in all four |
| Number of chunks | `CHUNKS=` **inside** `stage3.sh` and `stage4.sh`, **and** `-t 1-<CHUNKS>` on the `qsub` command for stage 4 | three places that must agree; stage 4 refuses to run if it does not match `work/chunks/CHUNKS` |
| How many names (a sample) | `LIMIT=` inside `stage3.sh` (now 500) and `stage5.sh` (now 5000); `--limit` when typing | empty = all names. Use the same number in 3 and 5 for a sample |
| Which facts | `FACTS=` inside `stage5.sh`; `--facts` when typing | empty = all facts of the sources |
| Memory and time requested | `#$ -l h_vmem=...` and `#$ -l h_rt=...` **inside** each qsub script | values in the repository: stages 2 and 3: 2G, 30 min; stage 4: 2G, 4 h; stage 5: 16G, 4 h. The TRE copies of stages 4 and 5 have been lowered to 1 h by hand, so the repository and the TRE differ. The scheduler penalises jobs that ask for much more than they use |
| Output folder | `--out-dir` (steps 2 to 5); defaults are in the table in section 6 | |

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
- **The log looks empty?** Python buffers its output when it is not a terminal, so a log can stay empty for a long time
  while the job is fine. `stage5.sh` switches this off; the other stage scripts do not yet.
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
| A new register or census load | 1, then 2, 3, 4 and 5 (`--refresh`); check the postcode match rate step 1 prints |
| The list of names (thresholds in `config.py`) | 1, then 3, 4, 5 |
| The grid (`GRID`) | 2, 3 and 4 |
| The smoothing of the population (`POPULATION_BANDWIDTH_M`) | 2, then 4 |
| How a map is drawn (bandwidth, weighting, levels, smoothing, blob rules) | 4 again (`--force`, or `clean.sh --stage34`) |
| A new version of a neighbourhood table | 0 (load it), then 5 with `--facts <that fact> --refresh` |
| A rule for the facts (`FACT_MIN_IN_CATEGORY`, list lengths) | 5 with `--compute-only` |

## 8. What to put in the TRE when code changes

The TRE has no git, so files go across one at a time. Only these are needed there:

- `pipeline/*.py` and `pipeline/hpc/*.sh` (not `tests/`, not `reference/`, not `fake_data.py` unless you use it there);
- `pipeline/reference/*.geojson` (the coastline used for the maps; it does not change);
- the neighbourhood tables (`work/neighbourhood/nbhd_*.csv`) when they change.

Not needed: `docs/`, `tools/` (they run on your laptop), `site/`, `gbnames/`, `data-prep/`, `raw-indicators/`.
After a change, the list of files that differ is `git diff --name-only <last commit you copied from> HEAD -- pipeline`.
Replace files only when no job of yours is queued (a queued job starts with whatever is there).

## 9. What is not standardised yet

An honest list, so nothing surprises you. None of it is broken; it is where the project grew unevenly.

1. **Run choices are typed in four places.** `SOURCES` sits inside each of four scripts, `CHUNKS` in two scripts plus
   the `qsub -t` range, `LIMIT` in two scripts with different values (500 and 5000). Changing one and forgetting
   another gives a confusing failure (stage 4 does stop with a clear message if `CHUNKS` disagrees).
2. **Memory and time are inside each script**, so changing them means editing the script in the TRE, and the TRE copies
   can then differ from the repository (they do now: stages 4 and 5 are 1 h in the TRE, 4 h in the repository).
3. **Step 1 has no qsub script**; it is typed directly.
4. **Only `stage5.sh` prints unbuffered**, so the other logs can look empty while running.
5. **No single command builds everything**; each stage is submitted by hand, in order.
6. `preview.py` names its folders `preview_maps` and `cache`, stage 5 uses `preview_facts` and `facts`; consistent enough,
   but the maps cache is not under the previews it belongs to.

A tidy fix that keeps everything working: put the run choices (`GBNAMES_SOURCES`, `GBNAMES_CHUNKS`, `GBNAMES_LIMIT`,
`GBNAMES_FACTS`) in `.env`, which every script already reads, so there is one place to change; add a `stage1.sh`; make
every script print unbuffered; and add one small `submit_all.sh` that submits stages 2 to 5 in order, each waiting for the
one before it. The natural moment is before the HPC folder is wiped and everything is uploaded again.
