# GBNames pipeline (draft 1, for review)

The plan for turning individual-level records (inside the TRE) into the release described in
[data-contract.md](data-contract.md).

**Status (2026-09-26).** Stages 1 to 5 are built and tested, both sources (register and census), and
have all run for real on the HPC, including the Scotland rule and the settled real-data calibration
(see "Decided so far" below). Stages 1 and 2 have real, full-name-list timings (about 27 and 12
minutes); stages 3 to 5 are measured so far on a 5,000-name sample (about 21, 2-3 minutes per chunk,
and 23 minutes) - the full name list is being run now, see pipeline/hpc/stage3.sh's/stage5.sh's own
comments for the current (estimated) time limits, to be tightened once that run's own numbers are in.
Stage 6 (`s6_assemble.py`, `merge_release.py`, `pipeline/hpc/stage6.sh`, `preview_web.py`) is built and
tested on fake data, deliberately deferring `lookups.json` and `mapNotes` (see its row below) - not yet
run against a real stage 4/5 output.

## Decided so far

- **Order of work.** First the modern (register) maps, then the historic (census) ones - swapped
  from the original plan since the census database is still being prepared - then the neighbourhood
  facts (stage 5), with the website reworked in parallel. `s1_counts.py --sources register` and
  `preview.py` with only register periods work with no working census connection at all.
- **Map periods (15).** Census: 1851, 1861, 1881, 1891, 1901, 1911, 1921 (1871 stays out, as
  before, not available for England and Wales). Register: 1997, 2000, 2005, 2010, 2015, 2020, 2025,
  2026.
- **Method.** May change if it is faster, as long as the maps look the same in spirit.
- **Neighbourhood facts (decided 2026-09-23).** UK OAC 2021/22, London OAC 2021 (London bearers only),
  AHAH v5.1, and deprivation from IoD 2025 (England), WIMD 2025 (Wales) and SIMD 2020v2 (Scotland),
  each ranked within its own country and then treated as comparable (a known simplification: percentile 1 in
  Scotland counts as percentile 1 in England). Dropped: the Internet User Classification and broadband speed.
  Added 2026-09-24: the Financial Precarity Classification (13 groups in 5 clusters, on the same zones as AHAH:
  `lsoa21cd`). Its lookup from area to group is **safeguarded data** (the published names are not): the download and
  its table are never in the repository (`.gitignore` twice, and a test fails if that stops being true), and no
  area-level value from it may appear in code, tests or docs. The raw downloads are turned
  into small lookup tables by `tools/prep_neighbourhood.py`, one per product and keyed on `area_code`, so a new
  version of one product replaces one table. Each table is joined on the postcode-directory column that matches
  its geography (`oa21cd`, `lsoa21cd`; Scottish deprivation on `lsoa11cd`), which is why no conversion between
  2011 and 2021 areas is needed. AHAH runs the other way from deprivation: decile 1 = healthiest, 10 = least healthy.
- **Ethnicity.** The Ethnicity Estimator replaces the old surname-only ONOMAP lookup: the register table
  `registers_derived.lcr_consol_ethest` carries an estimate (`eth`, a code such as `WAO-DE`) per person, worked out
  from forename and surname, and a name's ethnicity is the most common census group among its bearers. A name with
  no census group with at least 5 bearers is shown as `unknown`. The three most common codes (countries) are
  kept in the output but not used yet.
- **Language.** Python: numpy, scipy, shapely, pyproj and contourpy for the maps, plus a Postgres
  driver in the TRE (`pipeline/requirements.txt`; conda works well for this on the HPC).
- **Threshold, per source, both 100 (changed from census 30 on 2026-09-23).** Census data is over
  100 years old and treated as no disclosure risk, so its floor is only to keep a map meaningful,
  not for privacy - it was tried at 30 and looked too thin/noisy on real data to be worth showing,
  so it was raised to match register rather than kept as a separate, lower "meaningful" floor.
  Register's 100 is the standard disclosure threshold. (`THRESHOLD` in `config.py`.) This is the
  floor for a map (and for a period counting towards a name's page); a name's other years still
  show their raw count once it has a page at all.
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

  **Found on real data:** weighting can make a "too spread out" complaint *worse*, not better -
  dividing by local population boosts sparse areas relatively more, and a handful of individuals
  scattered in the countryside usually sit in exactly those sparse areas. Weighting answers "should
  every name show London", not "is this scattered individual worth showing" - those are different
  questions, and only the first is what `WEIGHT_POWER` was built for. `MIN_BLOB_SHARE` below is for
  the second.
- **Dropping minor blobs (new, 2026-09-23).** A separate concentration is dropped if it holds less
  than `MIN_BLOB_SHARE` (2%, a first guess) of the name's own total density (`kde.drop_minor_blobs`).
  `MIN_AREA_KM2` (below) cannot do this job: at these bandwidths even one person's own smoothed
  "bump" covers 100+ km2, so a handful of people passes an area test easily; what actually marks
  them as not worth showing is how little of the name's own total they represent, which this checks
  instead. It can only separate concentrations far enough apart that the smoothing already reduces
  the surface to zero between them (roughly, several times the bandwidth) - two concentrations
  closer than that are kept or dropped as one, not compared to each other. Tested on synthetic data
  (found and fixed two wrong assumptions along the way: scipy's default connectivity does not treat
  diagonal neighbours as joined, and mass share after smoothing is not the same number as a raw
  bearer-count ratio) - not yet checked against real names.
- **Map levels.** Each level is the smallest area that holds a share of the name's (weighted)
  density: 85% for level 1, 65% for level 2 and 40% for level 3 (`LEVEL_MASS`), the fake-data
  starting point - **found on real data (2026-09-23) to need to vary per name**, like bandwidth
  already does, not stay one constant. Unlike bandwidth, though, what predicts the right tightness
  does not look like bearer count: Cheshire needs almost as much area as Davies to reach the same
  share of its own total despite far fewer bearers, because Davies is more geographically
  concentrated - a difference in *shape*, not size. `kde.concentration()` (new, exploratory,
  `preview.py`'s "concentration" column) is a first attempt at measuring that shape directly - the
  "mass" cut-off value at which half a name's density is reached, cheap (reuses the sort
  `level_cutoffs()` already does) and not sensitive to a name having several separate regional
  cores the way a single weighted centroid/spread measure would be. Not yet used for anything,
  and not yet checked whether it actually predicts the right `LEVEL_MASS` - the next thing to try.
  Small names may also need tightening for an unrelated reason: see Van Dijk below.
- **Settled (2026-09-23), after several rounds of real-data calibration (~30 names) and one
  significant correction along the way.** `LEVEL_MASS` now varies per name by default
  (`kde.size_level_mass()`, `preview.py` uses it unless `--variants` is given), tightest for names
  in the low thousands to tens of thousands of bearers, loosest at both ends; `second_blob_share`
  loosens a name with a real secondary region. The bigger finding: a "C" shape/ring around big,
  dense cities (worse the denser the city) was showing up independent of `LEVEL_MASS`, caused by a
  big name's own bandwidth being wider than the fixed population-smoothing bandwidth, so an
  extremely dense exact city centre kept a sharp local peak that the name's own surface did not,
  and dividing by it created a dip exactly there. Fixed with `WEIGHT_CEILING` (8000 people/km2, caps
  what the division uses) and a wider `POPULATION_BANDWIDTH_M` (15,000, was 10,000) together, plus a
  wider `SMOOTH_M` (10,000, matching `data-prep`'s old equivalent step, was 5,000) for how solid the
  outlines read. One correction made along the way: an earlier round tightened Smith's tightest
  level in response to a "circles" complaint, which turned out to be the same ring artefact
  misdiagnosed - tightening a name's tightest level exposes that kind of artefact rather than fixing
  it, so that change was reverted once `WEIGHT_CEILING` existed to fix the real cause instead.
  Confirmed on a real ~30-name test round: real, plausible regional patterning, the ring/hole
  artefacts gone, small names honestly still uncertain (Van Dijk, Lansley) rather than forced into a
  falsely confident shape - the full history of wrong guesses and corrections along the way is in
  git commit messages, not repeated here.
- **1911, 1921 and Scotland.** Neither census has Scotland, and a Scottish name still has plenty of
  bearers in England, so its own count for that year does not fall below the threshold on its own.
  So instead of building a map from that year's (incomplete) data, we reuse the map from 1901 (a
  census that does have Scotland) whenever more than 30% of the name's bearers were there in 1901
  (`SCOTLAND_MAX_SHARE`, `pipeline/rules.py`) - a heavily Scottish name shows the same 1901 map for
  1901, 1911 and 1921. If 1901 itself is too small to build or copy, the year falls back to the
  ordinary threshold check on its own count.
  **The other half (decided 2026-09-26, after seeing Smith and Macdonald on the real data):** a map that
  IS built for 1911 or 1921 (the name is not Scottish enough to copy 1901's) has no Scottish people in
  it, so Scotland looks empty and the name looks as if it had vanished from there. The website draws the
  **Scotland mask** (a blanked-out Scotland, "no data") on those maps, and only on those: a copied map is
  1901's, which does have Scotland, and gets no mask (it gets the note that it shows 1901). Stage 6 has to
  tell the website which is which: see `copyOf` in the data contract.
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
- **Two databases, confirmed working.** The register+ONSPD tables and the census+parish tables are
  in different databases, so there are two separate, fully independent connections (`pipeline/db.py`,
  `config.py`'s `connections.register` / `connections.census`; confirmed `spatial.conpar*` is in the
  same database as `census.*`, as they are joined together in one query). Settings come from the
  environment, one full set per database, nothing shared or falling back between them
  (`config.PG_ENV_SUFFIX`): `PGHOST_LCR`/`PGPORT_LCR`/`PGDATABASE_LCR`/`PGUSER_LCR`/`PGPASSWORD_LCR`
  for the register (LCR = linked consumer register), and the same with `_ICEM` for the census
  (I-CeM). `s1_counts.py --sources register` or `--sources census` (both directions, tested) and a
  `preview.py --periods` restricted to one source's years let you test one database at a time,
  which matters in practice: the TRE has no git pull/push, every fix is copied in by hand, and the
  census database was still being prepared when register testing started.

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
| 1 | **Counts and name list** (`s1_counts.py`, done) | One query per source counts bearers per surname for **every year** at once (join the rows to a list of years, group by surname). Names with at least the threshold in at least one map period make the name list. Output: `counts` (source, year, surname, n). It also reports how many register rows find their postcode in the lookup, and stops if that is clearly wrong. For the census it reports, per year, how the people divide up (counted; parish id 0, which is expected: soldiers, sailors, people abroad; not counted although they should be) and stops if a person appears twice or the parish ids do not fit the boundaries. | Minutes to hours. **Run first**: it tells us how many names and map-years there really are. |
| 2 | **Population surfaces** (`s2_surfaces.py`, done) | One density surface of *everybody* per map period (`POPULATION_BANDWIDTH_M`, now 15 km), used to make each name's map partly relative to the local population. One query per period. | 15 small jobs (one per map period). |
| 3 | **Point extracts** (`s3_extracts.py`, done) | For each map period, one query pulls `(surname, x, y, count)` for every listed name at once, aggregated (spelling variants merged) and split into K chunk files by name (`names.chunk_of()`, a pure function of the name - no chunk assignment is written down anywhere for stage 4 to look up). One query per period, not one per name. | One query per period. |
| 4 | **Maps** (the heavy step, `s4_maps.py` + `pipeline/hpc/stage4.sh`, done) | An SGE array job with K tasks. Task k reads chunk k of every period and loads the grid and surfaces **once** - no database access at all. For each name and period at or above the threshold: density, weight by population, cut into a per-name `LEVEL_MASS` (`kde.size_level_mass()`), make outlines, clip to the coast, simplify. Each task writes **two files** (one line per name-period each): a GeoJSON-carrying one for a "build" period (a "substitute" period only names which period to copy, resolved later, not duplicated here) and a stats one (bearers, bandwidth, resolved levels, concentration/second-blob measures, shape) kept separate from the GeoJSON so the website never downloads it. A `.done` marker per chunk makes re-submitting after a partial failure safe. | The long one - not yet measured on real data (do a sample run first, see pipeline/README.md). |
| 5 | **Facts** (`s5_facts.py`, register side done) | For every name, in its reference year: the most common OAC, LOAC, AHAH and deprivation values, the deprivation score, the top neighbourhoods and the ethnicity estimate; forenames pooled over all years. One query per fact and reference year, saved to disk, then computed in Python, so changing a rule never needs the database again. Writes `facts.csv` (see "Stage 5 output" below). | Hours, not days (not measured yet: do a sample run). |
| 6 | **Assemble and validate** (`s6_assemble.py` + `merge_release.py` + `pipeline/hpc/stage6.sh`, an array job like stage 4, no database) | Join 1, 4 and 5 into the per-name files (counts and maps) and, as one table `facts.csv`, the facts (not folded into 380,000 files, decided 2026-09-26; `--facts-in-names` if wanted); the search index; `manifest.json` straight from `config.py`; the real `masks/scotland.json` (reprojected from `pipeline/reference/scotland_outline.geojson`). Resolves each "substitute" period into a copy of its reference's geometry, with `copyOf` (data-contract.md). Run `tools/validate_data.py`. **Deferred (2026-09-26, confirmed with the user): `lookups.json`** (classification names, colours, page text - human-authored, not derivable from the data) **and publishing *why* a period has no map** (`mapNotes`) - both still marked "not yet built" in data-contract.md; `preview_web.py` shows raw codes and a plain facts table until then. | Minutes; no database access, so it can run right after stages 4 and 5. |

Stages 1 to 5 touch individual-level records, so they run in the TRE. Only the finished, checked
release folder leaves it.

### Stage 5 output

(What to check on a first real run, before anything is exported: [first-run-checks.md](first-run-checks.md).)

`work/facts/facts.csv`, one row per name and fact: `surname, fact, version, ref_year, n_bearers, value, detail`.
`version` says which release of the classification the value is from (so a new version can sit next to an old
one), `detail` is JSON, and a name simply has no row for a fact it has no value for ("missing means no data").
`ref_year` and `n_bearers` (the bearers who have a value for it) are empty for forenames, which are pooled.

| `fact` | `value` | `detail` | Joined on |
|---|---|---|---|
| `oac` | most common group, e.g. `3b` | `distribution`: share of bearers per group | `oa21cd` |
| `loac` | most common group, e.g. `A1` | `distribution` | `oa21cd`, London bearers only |
| `ahah` | most common decile (1 = healthiest, 10 = least healthy) | `distribution`: ten shares, decile 1 first | `lsoa21cd` |
| `imd` | most common decile (1 = most deprived) | `distribution`: ten shares | `lsoa21cd` (England, Wales), `lsoa11cd` (Scotland) |
| `imd_score` | mean deprivation percentile (the "GBNames deprivation score") | `sd` | as `imd` |
| `fpc` | most common group, one of 13 (inside 5 clusters); safeguarded data | `distribution`: share per group | `lsoa21cd` |
| `places` | empty | `places`: up to 10 of `{msoa, district}`, most common first, each with at least 5 people | `msoa21cd`, `lad25cd` |
| `ethnicity` | most common census group code (`WBR`, `WAO`, ...) or `unknown` | `distribution` over groups, `codes`: the three most common codes | `eth` in the estimate table |
| `forenames_register` | empty | `f` and `m`: up to 10 forenames each, most common first, each with at least 5 people | pooled over all register years |
| `forenames_census` | empty | the same, and `years`: which census years were pooled | pooled over the census years 1851 to 1921; the sex is in the census |
| `parishes` | empty | `parishes`: up to 10 of `{county, parish}`, most common first, each with at least 5 people, and `years` | pooled over the census years; a parish is counted by county and name, so a parish that the 1851 and 1901 boundaries number differently is one |

**`value` and `detail`.** `value` is the headline, the one thing the site shows for the fact: the most common group,
decile or census group, or (for `imd_score`) the mean. `detail` is everything else, as JSON: the shares of bearers in
each group or decile (`distribution`), the spread (`sd`, for the score), the three most common ethnicity codes
(`codes`), or, for `places` and `forenames_register`, the lists themselves (which have no single headline, so their
`value` is empty). `n_bearers` is how many bearers the value rests on. Which of these a fact has is in the table.

**When a fact is reported.** The 100-bearer floor applies to the name as a whole, through the reference year. A fact
is then only written when the category it reports (the most common group or decile, or census group) has at least
5 bearers (`FACT_MIN_IN_CATEGORY`); `imd_score` needs 5 bearers with a value; and a neighbourhood, a parish or a forename is
listed with at least 5 people. One number for everything. (The historic census is over 100 years old and needs no
disclosure floor; it uses the same number to keep the two sources alike.) So a name can have LOAC from a few London
bearers, and `n_bearers` says how few. It is a disclosure floor, not a statistical one.

A tie for the most common value is broken at random, seeded by name and fact (so a re-run gives the same
answer), and `detail` then has `"tie": true`. No counts are written for places or forenames, only their order.
Shares are to three decimals (`SHARE_DECIMALS`); use two if the output checkers want less. The rules and their
numbers are in `config.py`, section 6.

Known small approximations: forenames are counted per register row (one person at several addresses counts
more than once, as before), and the database keeps each spelling variant's 25 most common forenames before the
variants are merged, which can only change a near-tie at the edge of the top ten. The postcode-directory codes
are 2021 for England and Wales and 2022 for Scotland (`msoa21cd` holds Scottish intermediate zones), so
`places` mixes MSOAs and intermediate zones.

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

**These are estimates.** The first thing to do in the TRE is a sample run (`s3_extracts.py --limit`,
`s4_maps.py` on a couple of its chunks - see pipeline/README.md's "Stage 4" section) and extrapolate
the real per-chunk time from that, not this fake-data figure, before sizing the full array job's
`-l h_rt`.

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
2. **Settled (2026-09-23): a reference year, not pooled.** Contemporary facts are worked out in each name's
   latest register year with 100+ bearers, so people who moved are not counted at every old address and a name
   with no 2026 records still has facts. Forenames are the exception and are pooled over all years.
3. **Settled: address to neighbourhood.** The ONS Postcode Directory (`registers_lookup.onspd_2026_feb`) carries every
   code needed (`oa21cd`, `lsoa21cd`, `lsoa11cd`, `msoa21cd`, `lad25cd`; confirmed in the TRE copy). Checked
   against the public February 2026 directory on a laptop: 99.9% or more of live postcodes find a row in every table.
4. **Settled: sex for register forenames.** `registers_lookup.lookup_monica` is identical to the old
   `monica_gender` and is used for now (its columns are assumed to be `name` and `gender`; it may change).
5. **Surname keys: settled.** The rule is: remove accents, keep the letters a to z (`O'Brien` becomes `obrien`). For the census it is applied to `sname_clean_stand`, the old project's cleaned surname, in every year (the TRE's backup of the census does not have the column, so `tools/sql/make_sname_clean_stand.sh` makes it there, for every year).
6. **Counts that are not published.** Counts below 10 (`COUNT_FLOOR`) are dropped. That number was my choice; is it the right floor?
7. **Classification versions: settled** (see "Decided so far"), including the financial precarity classification.
   Confirmed 2026-09-24: a per-surname most common group may be published, and so may the classification's names;
   only the lookup from area to group is safeguarded.
