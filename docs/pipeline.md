# GBNames pipeline (draft 1, for review)

The plan for turning individual-level records (inside the TRE) into the release described in
[data-contract.md](data-contract.md).

**Status.** Stage 1 (counts and name list) and the map calculation, including the Scotland rule,
are built and tested, first on fake data and now checked against a hand-picked real name on the
HPC. See [pipeline/README.md](../pipeline/README.md) for how to run them. Stages 2, 3, 4 (wiring
the map calculation to the full database and to an HPC batch job), 5 and 6 are still to do.

## Decided so far

- **Order of work.** First the historic (census) maps, then the modern (register) ones, then the
  neighbourhood facts (stage 5), with the website reworked in parallel.
- **Map periods (15).** Census: 1851, 1861, 1881, 1891, 1901, 1911, 1921 (1871 stays out, as
  before, not available for England and Wales). Register: 1997, 2000, 2005, 2010, 2015, 2020, 2025,
  2026.
- **Method.** May change if it is faster, as long as the maps look the same in spirit.
- **Neighbourhood facts (later).** Some sources are being refreshed and one is new: AHAH version 5,
  IMD for England 2025, and a new precarity index. Which versions to use is decided when we get to stage 5.
- **Language.** Python: numpy, scipy, shapely, pyproj and contourpy for the maps, plus a Postgres
  driver in the TRE (`pipeline/requirements.txt`; conda works well for this on the HPC).
- **Threshold, per source.** Census: 30 bearers. This data is over 100 years old and treated as no
  disclosure risk; the floor is only to keep a map meaningful, not for privacy. Register: 100
  bearers, the standard disclosure threshold. (`THRESHOLD` in `config.py`.)
- **Map bandwidth.** The old rule used a per-surname "isonymy class" that cannot be made for new
  names, so the new rule uses the number of bearers only: 8 km at 100 bearers, rising steadily to
  18 km at 100,000, and one bandwidth per name (from its biggest year) for all of its maps. The
  textbook rule of Scott was tried on fake data and always asked for the widest bandwidth, so it was dropped.
- **Population weighting: "a bit relative".** With plain density every name shows the biggest
  cities, whoever bears it. So the name's density is divided by the density of everybody raised to
  a power (`WEIGHT_POWER`): 0 is plain density, 1 is fully relative (the name's share of the local
  population - "10 bearers in a population of 100" outranks "100 bearers in a population of
  10,000"), and the setting is 0.5. Areas with fewer than 50 people per km2 count as 50
  (`WEIGHT_FLOOR`), so a handful of people in an empty area cannot dominate - this pulls against the
  relative measure above and the two need balancing together, not separately. The old rule (divide
  by minus the log of the density) is not kept: as read, it moved density in the same direction as
  plain density, only compressed, rather than correcting for it.
- **Map levels.** Each level is the smallest area that holds a share of the name's (weighted)
  density: 85% for level 1, 65% for level 2 and 40% for level 3 (`LEVEL_MASS`). This replaces the
  old cut-offs, which were divided by a size-dependent constant found by trial and error. Every name
  gets all three levels, small names show as clearly as big ones, a widespread name gets large
  areas and a local name small ones. Compared by eye on fake data: 90/75/50 spreads local names too
  much, 75/50/25 makes widespread names patchy again, so 85/65/40 is the middle - to revisit on real
  data alongside the weighting dial above.
- **1911, 1921 and Scotland.** Neither census has Scotland, and a Scottish name still has plenty of
  bearers in England, so its own count for that year does not fall below the threshold on its own.
  So instead of building a map from that year's (incomplete) data, we reuse the map from 1901 (a
  census that does have Scotland) whenever more than 30% of the name's bearers were there in 1901
  (`SCOTLAND_MAX_SHARE`, `pipeline/rules.py`) - a heavily Scottish name shows the same 1901 map for
  1901, 1911 and 1921. If 1901 itself is too small to build or copy, the year falls back to the
  ordinary threshold check on its own count.
- **Register layout (TRE).** `registers_linked.lcr_consol2026`: forename, surname, postcode, first,
  last. The postcode is standardised (lower case, no spaces). It has no coordinates, so they come
  from the ONS Postcode Directory (ONSPD, `registers_lookup.onspd_2026_feb`, British National Grid
  metres, joined on `stdpcd`; register and ONSPD are in the same database). Postcodes without a grid
  reference (0) or missing from the file are left out - expected, fine, as long as the remaining
  rows still clear the threshold.
- **Census layout (TRE).** `census.gb1851` with `census.gb1851_att`, and so on; joined to
  `spatial.conpar1851` (1851-1891) or `spatial.conpar1901` (1901-1921) for the parish centroid.
  1921 uses the same parishes as 1911.
- **Great Britain only.** Northern Ireland has no historic data and different neighbourhood data,
  so it is left out, as are the Isle of Man and the Channel Islands (country codes in `extra_where`).
- **Two databases.** The register+ONSPD tables and the census+parish tables are in different
  databases, so there are two separate connections (`pipeline/db.py`, `config.py`'s
  `connections.register` / `connections.census`). Assumed: `spatial.conpar*` lives in the same
  database as `census.*` (they are joined together in one query) - flag if that is wrong. Settings
  come from the environment: `PGHOST`/`PGPORT`/`PGDATABASE`/`PGUSER` for the register database;
  `CENSUS_PGDATABASE` for the census one (falls back to the register's host/port/user if its own
  are not set, so it only needs its own value where it actually differs). `PGPASSWORD` for both,
  or `CENSUS_PGPASSWORD` if the census login differs.

## What goes in

**Linked consumer registers, 1997 to 2026** (`registers_linked.lcr_consol2026`). One row per person at an address:

| forename | surname | postcode | first | last |
|---|---|---|---|---|

The postcode is turned into an x/y coordinate with a postcode lookup table. A person is "at that
address in year Y" when `first <= Y <= last`, so any single year is a simple query.

**Historic censuses, 1851 to 1921.** The same idea: one row per person with a **parish** (linked to
the parish boundaries / centroids), forename and surname. The census also records sex.

**Reference files:** parish boundaries and centroids; the postcode lookup (postcode to coordinates,
output area, LSOA, MSOA); the classification files (OAC, LOAC, IUC, IMD, AHAH, broadband); a
forename-to-gender lookup for the registers; the ONOMAP surname file for the ethnicity estimate;
the Great Britain outline; the 1 km grid.

Both sources answer the same question, "who (surname) was where (x, y) in period P", so one code
path can serve both.

## The stages

```
counts -> name list ---> point extracts -> MAPS (array job) --+
   |                                                          +-> assemble -> validate -> release
   +------> surfaces ----^              FACTS (grouped) -----+
```

| # | Stage | What it does | Cost |
|---|---|---|---|
| 1 | **Counts and name list** | One query per source counts bearers per surname for **every year** at once (join the rows to a list of years, group by surname). Names with at least the threshold in at least one map period make the name list. Output: `counts` (source, year, surname, n). It also reports how many register rows find their postcode in the lookup, and stops if that is clearly wrong. | Minutes to hours. **Run first**: it tells us how many names and map-years there really are. |
| 2 | **Population surfaces** | One density surface of *everybody* per map period (10 km bandwidth), used to make each name's map partly relative to the local population. | 15 small jobs (one per map period). |
| 3 | **Point extracts** | For each map period, pull `(surname, x, y, count)` for the listed names, and split the result into K chunk files by surname (say K = 200). One extract per period, not one query per name. | One query per period. |
| 4 | **Maps** (the heavy step) | An SGE array job with K tasks. Task k reads chunk k of every period and loads the grid and surfaces **once**. For each name and period at or above the threshold: density, weight by population, cut into 3 levels, make outlines, clip to the coast, simplify. Each task writes **one file** (one line per name-period), not thousands of tiny files. | The long one. |
| 5 | **Facts** | Grouped queries over all names at once: top 10 forenames per sex, top 10 places, the most common OAC / LOAC / IUC / AHAH / broadband class, IMD decile with mean and sd, the ethnicity estimate (from the surname list alone, no addresses). | Hours, not days. |
| 6 | **Assemble and validate** | Join 1, 4 and 5 into the per-name files, the index, `manifest.json` and `lookups.json`. Run `tools/validate_data.py`. Pack the release as one archive for output checking. | Minutes. |

Stages 1 to 5 touch individual-level records, so they run in the TRE. Only the finished, checked
release folder leaves it.

### What changes compared with the old pipeline

| Old | New |
|---|---|
| About 1.2 million jobs, each starting `psql`, then R (reloading the grids), then Python (loading geopandas and a shapefile) | K array tasks, each loading things once and looping over its names |
| One database query per name per year, and per name per fact table | One extract per period; facts computed for all names in one pass |
| Maps for all 26 years, of which 9 were shown | Maps only for the periods listed in the manifest |
| Results stored in a database, then read back and re-drawn | Results written straight into the final per-name files |
| Each stage started by hand from shell and R scripts with database host and user names (and, in some R files, passwords) written into the code | Stages take their settings from one config file; every stage can be re-run on its own |

### Sizing (a guess, to be replaced by a measurement)

The old run made 1.2 million maps over several days. With 15 periods and up to 25,000 names there
are at most 375,000 maps, fewer once the threshold is applied, and fewer again once the Scotland
rule reuses a map instead of building one.

Measured on fake data, on one core of a laptop: a map takes a median of 60 to 80 milliseconds and
at most about 120, including smoothing, weighting, outlines, clipping to the coast and simplifying. The slowest
are widespread names with many separate areas. At 0.1 seconds a map, 375,000 maps are about 10
core-hours, which is minutes on the cluster; even ten times slower it is under an hour. Real names
have more complicated shapes than fake ones, and reading the points out of the database will
probably matter more than the maps themselves.

**These are estimates.** The first thing to do in the TRE is run one chunk and extrapolate from that.

## Testing without the TRE

I cannot see the data or run anything in the TRE, so:

- I write a small **fake-data generator** that produces a register and a census in exactly the
  shapes above (fake people, postcodes, parishes). Every stage can then be run and checked on a laptop.
- The same scripts run unchanged in the TRE. Their output is checked by `validate_data.py`.
- Every stage writes its result to disk, so any stage can be re-run without redoing the ones before it.
- For the map method: compare the new shapes with the ones already on the site for Smith,
  Juszczyk and Sion, by eye and by overlap. That needs the source points, so it happens inside the TRE.

## To settle before the long run

1. **The parish table name.** `spatial.conpar{boundaries}` in the `tre` block is a guess from the
   old scripts; the register and ONSPD table names are confirmed.
2. **The look of the maps on real data.** The settings were chosen on fake data; the first test is about
   50 real names. Run `python3 -m pipeline.preview --names ...` and compare with `--variants`, for
   example `0.5/mass:0.85,0.65,0.4 0.5/mass:0.75,0.5,0.25`. If there are too many small spots: on fake data
   `--min-area 400` (instead of 25) cut the number of separate areas by about a third but only removed
   tiny specks, because the remaining spots are real-sized blobs. To remove those, lower the level
   shares (`LEVEL_MASS`) or raise `WEIGHT_POWER`; if that is not enough, a rule that drops areas small
   compared with the name's biggest one could be added.
3. **Facts: one reference year, or pooled?** The old queries had no year filter, so people with
   many addresses counted several times. A single reference year avoids that (2026 is only a part
   year, so probably the last full year).
4. **Address to neighbourhood.** Facts need an output area / LSOA / MSOA for each postcode. Which lookup is available in the TRE?
5. **Sex for register forenames.** The old pipeline used a forename-to-gender table (`monica_gender`). Is there an equivalent now?
6. **Surname keys.** The rule is: remove accents, keep the letters a to z (`O'Brien` becomes `obrien`). Does the census `sname_clean_stand` follow the same convention?
7. **Counts that are not published.** Counts below 10 (`COUNT_FLOOR`) are dropped. That number was my choice; is it the right floor?
8. **Classification versions and the new precarity index**, when we get to stage 5.
