# GBNames pipeline (draft 1, for review)

The plan for turning individual-level records (inside the TRE) into the release described in
[data-contract.md](data-contract.md). **Nothing here is built yet.** This is the proposal to react to.

## Decided so far

- **Order of work.** First the new maps (stages 1 to 4), then the neighbourhood facts (stage 5),
  with the website reworked in parallel.
- **Map periods (18).** Census: 1851, 1861, 1881, 1891, 1901, 1911 and 1921 (1871 stays out, as
  before, because it is not available for England and Wales). Registers: 2000, 2005, 2010, 2015,
  2020, then every year from 2021 to 2026 (2026 is a part year). The old 1997/1998 maps go.
- **Method.** May change if it is faster, as long as the maps look the same in spirit.
- **Neighbourhood facts (later).** Some sources are being refreshed and one is new: AHAH version 5,
  IMD for England 2025, and a new precarity index. Which versions to use is decided when we get to stage 5.

## What goes in

**Linked consumer registers, 1997 to 2026.** One row per person at an address:

| uprn | forename | surname | first year seen | last year seen |
|---|---|---|---|---|

The address (UPRN) carries its location: an x/y coordinate and a postcode. A person is "at that
address in year Y" when `first <= Y <= last`, so any single year is a simple query.

**Historic censuses, 1851 to 1911 (1921 to add).** The same idea: one row per person with a
**parish** (linked to the parish boundaries / centroids), forename and surname. The census also
records sex.

**Reference files:** parish boundaries and centroids; lookups from an address location to output
area / LSOA / MSOA; the classification files (OAC, LOAC, IUC, IMD, AHAH, broadband); a
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
| 1 | **Counts and name list** | One query per source counts bearers per surname for **every year** at once (join the rows to a list of years, group by surname). Names with at least the threshold in at least one map period make the name list. Output: `counts` (source, year, surname, n). | Minutes to hours. **Run first**: it tells us how many names and map-years there really are. |
| 2 | **Population surfaces** | One density surface of *everybody* per map period (10 km bandwidth, as before), used to weight each surname by how many people live there. | 18 small jobs (one per map period). |
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

The old run made 1.2 million maps over several days. With 18 periods and up to 25,000 names there
are at most 450,000 maps, and fewer once the threshold is applied.

One measurement so far: the density calculation itself (Gaussian smoothing over the whole 1 km
grid of Great Britain) takes 20 to 30 milliseconds per map on one core of a laptop, so it is not
the bottleneck. Turning the result into outlines is not measured yet. If a whole map takes a
cautious 2 seconds, 450,000 maps are about 250 core-hours, a few hours on the 6 machines with
about 24 cores each. At 0.3 seconds it would be about 40 core-hours, under an hour on the full
cluster. Reading the points out of the database may well matter more than either.

**These are estimates.** The first thing to do in the TRE is run one chunk and extrapolate from that.

## Testing without the TRE

I cannot see the data or run anything in the TRE, so:

- I write a small **fake-data generator** that produces a register and a census in exactly the
  shapes above (fake people, addresses, parishes). Every stage can then be run and checked on a laptop.
- The same scripts run unchanged in the TRE. Their output is checked by `validate_data.py`.
- Every stage writes its result to disk, so any stage can be re-run without redoing the ones before it.
- For the map method: compare the new shapes with the ones already on the site for Smith,
  Juszczyk and Sion, by eye and by overlap. That needs the source points, so it happens inside the TRE.

## To settle before the long run

1. **Movers.** A person who moves in year Y can match two rows for Y (last seen at the old address
   = Y, first seen at the new one = Y). Without a person identifier, counts for Y can be slightly
   inflated. Is there a person ID? If not, count distinct (forename, surname, UPRN) per year and accept the small overcount?
2. **Facts: one reference year, or pooled?** The old queries had no year filter, so people with
   many addresses counted several times. A single reference year avoids that (2026 is only a part
   year, so probably the last full year).
3. **Address to neighbourhood.** Facts need an output area / LSOA / MSOA for each UPRN. Which lookup is available in the TRE?
4. **Sex for register forenames.** The old pipeline used a forename-to-gender table (`monica_gender`). Is there an equivalent now?
5. **Parish boundaries for 1921**, and whether 1921 includes Scotland (which would remove the 1911 Scotland workaround).
6. **Years, threshold, method, classification versions, surname keys:** see the last table in the data contract.
7. **Language.** I would write everything after the extract in Python (one language for all stages;
   numpy/scipy for the density, shapely for outlines). Which geospatial packages can Artifactory provide, and would you rather have R?
