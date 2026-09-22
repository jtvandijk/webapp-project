# GBNames pipeline (draft 1, for review)

The plan for turning individual-level records (inside the TRE) into the release described in
[data-contract.md](data-contract.md).

**Status.** Stage 1 (counts and name list) and the map calculation, including the Scotland rule,
are built and tested, first on fake data and now checked against a hand-picked real name on the
HPC. See [pipeline/README.md](../pipeline/README.md) for how to run them. Stages 2, 3, 4 (wiring
the map calculation to the full database and to an HPC batch job), 5 and 6 are still to do.

## Decided so far

- **Order of work.** First the modern (register) maps, then the historic (census) ones - swapped
  from the original plan since the census database is still being prepared - then the neighbourhood
  facts (stage 5), with the website reworked in parallel. `s1_counts.py --sources register` and
  `preview.py` with only register periods work with no working census connection at all.
- **Map periods (15).** Census: 1851, 1861, 1881, 1891, 1901, 1911, 1921 (1871 stays out, as
  before, not available for England and Wales). Register: 1997, 2000, 2005, 2010, 2015, 2020, 2025,
  2026.
- **Method.** May change if it is faster, as long as the maps look the same in spirit.
- **Neighbourhood facts (later).** Some sources are being refreshed and one is new: AHAH version 5,
  IMD for England 2025, and a new precarity index. Which versions to use is decided when we get to stage 5.
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
2. **The look of the maps on real data - in progress.** `LEVEL_MASS` tried at 0.70/0.50/0.30 (down
   from the 0.85/0.65/0.40 default) on smith, longley, vandijk, macdonald, obrien, cheshire, davies,
   jones: jones/davies excellent; cheshire/obrien still too wide (see the map levels bullet above -
   probably a concentration/shape issue, not fixable by a tighter constant alone); macdonald good
   (Scotland concentrated) with London still showing at the outer level only, which may just be
   correct (a real, smaller concentration); smith developed small holes at the tighter setting
   (plausible cause: a real dip between two nearby elevated areas, or the population-weighting step
   suppressing a dense urban core, exposed once the value threshold rose - not confirmed which).
   **Van Dijk (~150 bearers) specifically:** `MIN_BLOB_SHARE` does not help even at 0.10 - the
   "separate areas" count in `preview.py`'s table barely moves between 0.02 and 0.05 (~40 throughout),
   which is the signature of a share-based check being structurally powerless here, either because
   the whole surface is already one connected blob nationally (individual bearers' smoothed bumps
   never reach exact zero between them at this bandwidth), or because 150 total bearers is too few
   for real clusters and individual noise to differ enough in *relative share* to be separable at
   all. A much tighter `LEVEL_MASS` (0.30/0.20/0.10) *does* reduce it (down to 25-32), since it is a
   value threshold, not a connectivity one - but the surviving blobs become quite small, which is
   probably why the old pipeline manually inflated small names' visual size ("blow up smaller names
   ... otherwise you can't really see them" - user's recollection, mechanism not recorded). Proposed
   (not yet built): a separate, final visibility buffer on the tidied polygon, scaled by name size -
   deliberately kept apart from bandwidth, since widening bandwidth to the same end would also let
   individual noise bumps reach further and merge, working against this very problem.

   **Full calibration round, 8 names x 4 `LEVEL_MASS` settings (2026-09-23).** By eye, against
   85/60/30, 75/50/25, 50/25/10 and 20/10/5: the right setting tracks bearer count, not concentration
   - as bearers fall from Smith (500k) to Cheshire (2k) the sweet spot moves steadily tighter - but
   it is an **inverted U, not a straight line**: Smith never improves with tightening (good at
   85/60/30, worse at every tighter setting - it likely has more than one comparably strong region,
   and tightening carves a gap between them rather than isolating one), and Van Dijk (~150 bearers)
   never lands on "good" at any setting either - the user's own read, that the untightened,
   "speckled" original may just be the honest answer at that scale, is taken seriously here, not
   treated as a gap to keep closing: at so few bearers a real cluster and a few coincidentally close
   individuals may not be separable by any threshold. Longley and Cheshire share the same bearer
   count (2k) but want visibly different settings (Longley looser, Cheshire tighter) - a residual
   that bearer count alone cannot explain, left unresolved.

   `kde.size_level_mass(n, second_share)` (new) is a first-draft curve through this data -
   log-interpolated per level (not one triple scaled by a factor, since the good settings did not
   keep a fixed shape at every size), loosest at both ends, tightest around Cheshire/Longley's size,
   with `second_blob_share` (new, `kde.second_blob_share()`) overriding towards the loose end for a
   Smith-like name. `preview.py --auto-level-mass` uses it instead of `--variants`. Explicitly not a
   fitted regression - eight names with hand-picked, categorical verdicts is enough to see a shape,
   not enough to trust exact numbers - to be tested against more names and refined, not treated as
   settled.
3. **Facts: one reference year, or pooled?** The old queries had no year filter, so people with
   many addresses counted several times. A single reference year avoids that (2026 is only a part
   year, so probably the last full year).
4. **Address to neighbourhood.** Facts need an output area / LSOA / MSOA for each postcode. Which lookup is available in the TRE?
5. **Sex for register forenames.** The old pipeline used a forename-to-gender table (`monica_gender`). Is there an equivalent now?
6. **Surname keys.** The rule is: remove accents, keep the letters a to z (`O'Brien` becomes `obrien`). Does the census `sname_clean_stand` follow the same convention?
7. **Counts that are not published.** Counts below 10 (`COUNT_FLOOR`) are dropped. That number was my choice; is it the right floor?
8. **Classification versions and the new precarity index**, when we get to stage 5.
