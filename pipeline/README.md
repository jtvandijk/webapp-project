# The GBNames pipeline

The code that turns the registers and censuses into the data behind the website (the format is in
[docs/data-contract.md](../docs/data-contract.md), the plan in [docs/pipeline.md](../docs/pipeline.md)).

## What is here

| File | What it does | Status |
|---|---|---|
| `config.py` | **All settings.** Table and column names, years, threshold, map settings. | done |
| `fake_data.py` | Makes a fake database with the same shape as the real one. | done |
| `s1_counts.py` | Stage 1: bearers per name per year, and the list of names that get a page. | done, tested |
| `kde.py` | The map calculation for one name and year. | done, tested |
| `rules.py` | What happens to each period: built, copied from another year (Scotland), or left out. | done, tested |
| `preview.py` | Draws a page of maps to look at. | done |
| `sql.py`, `db.py`, `names.py` | The queries, the two database connections, the surname rule. | done |
| stages 2 to 6 | Population surfaces, point extracts, the map job on the HPC, facts, assembling the release. | to do |

## Try it on your own computer (fake data)

```
pip install -r pipeline/requirements.txt          # once (a virtual environment is a good idea)
python3 -m pipeline.fake_data                     # a fake database in work/ (a few seconds)
python3 -m pipeline.s1_counts                     # counts and the name list, into work/
python3 -m pipeline.preview                       # then open work/preview.html in a browser
python3 -m unittest discover -s pipeline/tests -t .    # the tests (a few seconds)
```

Run everything from the project folder (the one that contains `pipeline/`, `docs/`, `tools/`).

`python3 -m pipeline.preview --names smith jones --periods 1851 1901 2000 2026` chooses the names
and years. `--variants 0/mass 0.5/mass 1/mass` or `--variants 0.5/mass:0.85,0.65,0.4 0.5/mass:0.75,0.5,0.25`
shows several settings side by side, without editing anything (`<weighting power>/<level mode>[:<level shares>]`). The page is a single file, so it also opens in the TRE, which has no internet.

By default every name gets its own `LEVEL_MASS` from `kde.size_level_mass()` - a curve calibrated by
eye against real names (see its docstring), confirmed on real data 2026-09-23 as a real improvement
over one fixed setting for every name. Each name's own resolved setting (and its `second_blob_share`,
the measure the curve uses to spot a name with a real secondary region) is labelled under its maps.
Pass `--variants` to turn this off and compare specific settings by hand instead, e.g.
`--variants 0/mass 0.5/mass 1/mass` or `--variants 0.5/mass:0.85,0.65,0.4 0.5/mass:0.75,0.5,0.25`
(`<weighting power>/<level mode>[:<level shares>]`).

What is fetched from the database is cached in `work/cache/`, since comparing KDE settings re-draws
the same data without re-fetching it - a real database query dominates the runtime (minutes), the
drawing itself does not (tens of seconds even for many maps, though many names x many periods x
many `--variants` adds up, since each variant redraws every one). The per-name part of the cache
only grows: adding a name to `--names` fetches just that name, not the others again. `--refresh-cache`
forces a full re-fetch after the underlying data has actually changed (a new register or census
load), since nothing here notices that on its own.

## Running it in the TRE

The register+ONSPD tables and the census+parish tables are in **two different databases**, so
there are two connections (`config.py`'s `connections.register` / `connections.census`; Postgres
cannot join across databases in one query, so this isn't just a config nicety, `db.py` genuinely
opens two).

1. Check the parish table name in `config.py`'s `"tre"` block (`spatial.conpar…`) - it is a guess
   from the old scripts, assumed to be in the same database as `census.*`. The register
   (`registers_linked.lcr_consol2026`) and ONSPD (`registers_lookup.onspd_2026_feb`, `stdpcd`,
   `east1m`, `north1m`, `ctry25cd`) are confirmed - note the 2026 ONSPD renamed the usual
   `oseast1m`/`osnrth1m`/`ctry` to `east1m`/`north1m`/`ctry25cd`.
2. Install a Postgres driver (see `requirements.txt`): try `pip install psycopg2` first (or
   `conda install psycopg2`, which is often simpler on an HPC), then `pip install "psycopg[binary]"`,
   then `pip install pg8000` (pure Python, no compiler needed at all) — stop at the first that
   installs. `db.py` uses whichever one is there.
3. Set the connection variables for each database - fully separate, nothing shared between them
   (see `config.PG_ENV_SUFFIX`): `PGHOST_LCR`, `PGPORT_LCR`, `PGDATABASE_LCR`, `PGUSER_LCR` for the
   register (LCR = linked consumer register), and `PGHOST_ICEM`, `PGPORT_ICEM`, `PGDATABASE_ICEM`,
   `PGUSER_ICEM` for the census (I-CeM) - e.g. source a small env file with these in it. Export
   `PGPASSWORD_LCR` and `PGPASSWORD_ICEM` separately, then `export GBNAMES_PROFILE=tre`. Passwords
   are never written into any file (note: pg8000 only reads `PGPASSWORD_*`, not `~/.pgpass`).
4. `python3 -m pipeline.s1_counts` (add `--sources register` or `--sources census` to test one
   database before the other is ready - `preview.py` does this automatically, based on which
   sources its `--periods` need). If a table or column name is wrong, Postgres says which. The
   stage prints how many register rows find their postcode in the lookup (it stops below 80%, which
   means the postcodes are written differently in the two tables) and stops if the lookup has a
   postcode twice, since everybody there would count twice.

The coordinates in the lookup must be British National Grid metres (easting, northing). If the
lookup holds latitude and longitude instead, tell me and I will add the conversion.

## Things that are easy to change (all in `config.py`)

- `THRESHOLD`: minimum bearers for a map, per source (both 100 - a 30-bearer census map looked too
  thin/noisy on real data to be worth showing, so it no longer has a separate, lower floor).
- `MAP_YEARS`: which years get a map. The website follows automatically.
- `BANDWIDTH_MIN_M`, `BANDWIDTH_MAX_M`, `BANDWIDTH_N`: how widely each bearer is spread on the map.
- `WEIGHT_POWER`: how much the local population is taken into account (0 = plain density, 1 = fully relative, now 0.5).
  Careful: raising this does not just suppress big cities, it also makes any *sparse* area relatively
  louder - including a handful of scattered individuals sitting in the countryside, which can make a
  name look more spread out, not less.
- `WEIGHT_CEILING` (now 8000 people/km2) and `POPULATION_BANDWIDTH_M` (now 15000, widened from
  10000): fix a ring or "C" shape that showed up around big, very dense cities instead of a filled
  area - confirmed and fixed on real data 2026-09-23. A big name's own bandwidth can be much wider
  than the population surface's, so an extremely dense exact city centre kept a sharp local peak the
  name's own, more smoothed-out surface did not, and dividing by it created a dip exactly there.
  `preview --weight-ceiling`/`--population-bandwidth` to try other values.
- `MIN_BLOB_SHARE`: drops a separate concentration that holds less than this share of the name's own
  total (now 2%) - for a handful of people sitting on their own somewhere, not a real concentration.
  Different from `MIN_AREA_KM2` below: at these bandwidths even one person's own smoothed "bump" can
  cover 100+ km2, so an area test alone cannot catch this; only works between concentrations far
  enough apart that the smoothing has already reduced the gap between them to zero (see
  `kde.drop_minor_blobs`'s docstring) - two nearby but visually distinct concentrations are kept or
  dropped together, not compared to each other. Cannot help a name with too few total bearers for a
  real cluster and 1-2 coincidental individuals to differ enough in *relative* share (`MIN_BLOB_BEARERS`
  below is for that). Note: for most of this session `preview.py` called this with a bug that meant
  it was never actually applied at all (fixed 2026-09-23, see git history) - re-check any earlier
  "min-blob-share doesn't help" conclusion now that it is actually running.
- `MIN_BLOB_BEARERS`: also drops a blob with fewer than this many actual (unweighted) bearers,
  whatever share of the total that is (now 5, `kde.drop_tiny_blobs()`) - complements `MIN_BLOB_SHARE`
  rather than replacing it: this is the one that can help a small name, since "1-2 people" is "1-2
  people" regardless of the name's total, unlike a percentage. Untested on real data yet.
- `LEVEL_MASS`: the share of a name's density that levels 1, 2 and 3 hold for the smallest names
  (85%, 65%, 40%) - see `kde.size_level_mass()`, which varies this per name by default (confirmed on
  real data 2026-09-23); `LEVEL_MODE = "peak"` uses `LEVEL_PEAK` instead.
- `SCOTLAND_MAX_SHARE`: when a Scottish name's 1911/1921 map is copied from 1901 instead of built (now more than 30% in Scotland in 1901).
- `SMOOTH_M`, `SIMPLIFY_M`, `MIN_AREA_KM2`: how tidy the outlines are, and how large the files get. `SMOOTH_M` (now
  10000, matching the old pipeline's equivalent step in `data-prep/py/fn_prerender.py` - confirmed on real data
  to read as more solid/concentric than the previous 5000) closes gaps/notches narrower than 2x itself.
  `MIN_AREA_KM2` removes tiny specks (`preview --min-area 400` to try); the preview table shows how many
  separate areas each map has.

`preview.py --min-blob-share 0.05`/`--min-blob-bearers 8` (etc.) try a different value without
editing `config.py`.

Use `preview.py` after changing any of them.

## How a map is actually put together

One name, one year, start to finish (`kde.py`, numbered as in its module docstring):

1. **Grid.** Every bearer that year is placed on a 1 km grid over Great Britain.
2. **Smooth.** Each bearer's single grid cell is spread out into a soft "bump" (a Gaussian kernel) -
   this is the KDE (kernel density estimate) part. How wide the bump is (the *bandwidth*) grows with
   the name's size, from 8 km at 100 bearers to 18 km at 100,000+ (`size_bandwidth`) - a bigger name
   uses a bit more spread, so its map reads as the more nationally-significant story it usually is,
   rather than a tight dot. One bandwidth per name, from its biggest year, so the map looks the same
   width across every year's slider position.
3. **Weigh.** The smoothed name density is divided by the local population's own density (also
   smoothed, `POPULATION_BANDWIDTH_M`), raised to `WEIGHT_POWER` (0.5: "a bit relative"). Without
   this, every name's biggest patch would just be wherever the most people of *any* name live -
   London, mostly. `WEIGHT_FLOOR`/`WEIGHT_CEILING` stop a very sparse or very dense pixel from
   dominating the division at either end - the ceiling specifically stops an extremely dense exact
   city centre creating a dip (a ring or "C" shape) relative to its own surrounding suburbs.
4. **Drop noise.** A separate, disconnected patch is zeroed out if it holds too little of the name's
   own total density (`MIN_BLOB_SHARE`, a *relative* test - fine for a name with plenty of total
   bearers) or too few actual bearers outright (`MIN_BLOB_BEARERS`, an *absolute* test - the one that
   can still help a name with very few bearers overall, where "1-2 people on their own" is never a
   small enough *share* of the total for the relative test to catch).
5. **Cut levels.** Three nested outlines are drawn: each one is the smallest area that contains a
   given share of what's left of the name's density (`LEVEL_MASS`, "mass" mode) or a fixed fraction
   of the peak value (`LEVEL_PEAK`, "peak" mode). **This share is not the same for every name** -
   `kde.size_level_mass()` picks it per name (see the plain-terms section below for why).
6. **Tidy.** Small gaps and notches are closed (`SMOOTH_M`), tiny specks removed (`MIN_AREA_KM2`),
   and the outline clipped to the coastline and simplified (`SIMPLIFY_M`) for a smaller file.
7. **Band.** The three nested areas become three non-overlapping bands (each level minus the one inside it).
8. **Write.** The bands become GeoJSON, in longitude/latitude, 4 decimal places.

The whole thing (population surfaces aside, which are shared across every name in a period) takes
tens of milliseconds per map - the database query dominates the real runtime, not this calculation.

## In plain terms (for anyone who isn't going to read the code)

The shaded areas on a name's map are **not** simply "everywhere someone with this name lives", and
they are **not** simply "how many people with this name live in each area" either (that would need
a bar chart, not a map). They are closer to: *"given how common this name is here compared with how
many people live here at all, how confident are we that this is a real, meaningful concentration of
the name, rather than just wherever people in general happen to live?"*

Three things make that possible, and all three matter for how to read a map:

- **It is smoothed, not exact.** A person's location is spread out into a soft area, not marked as a
  precise point - both because a single point tells you nothing reliable about the wider area, and
  because it keeps individual people from ever being pinpointed. A rarer, more locally-rooted name
  gets a tighter spread than a very common one, which gets spread a little wider, so each map reads
  at roughly the scale that name's own story actually plays out at.
- **It is weighted by population, not raw counts.** A name that just has a lot of bearers everywhere
  big cities exist would otherwise light up London, Birmingham and Manchester every single time,
  because that is simply where most people of *any* name live. The map instead asks whether the name
  is *more* common somewhere than the local population alone would explain - so a name genuinely tied
  to a particular place stands out there, rather than every name's map converging on the same few
  big dots.
- **The three shaded bands are "percentage volume contours" - but the percentage is not fixed.** Each
  band is drawn as "the smallest area that holds this much of the name's own concentration" (the
  darkest band being the tightest, most concentrated share). Two different names' darkest bands are
  **not** necessarily the same percentage of anything comparable to each other - the percentage used
  is chosen per name (bigger, more nationally-spread names and very small names both tend to need a
  looser setting than names in between; see `kde.size_level_mass()`), specifically so that each map
  looks like a sensible, readable picture of *that* name, rather than forcing every name through one
  identical rule regardless of whether it happens to produce a good-looking result for it. So: read
  the shading as "more concentrated the darker it gets", not as a number you could compare precisely
  between two different names' maps.

One honest limitation, not yet resolved: names with very few bearers nationally (a few hundred or
fewer) sometimes cannot be reduced to one clean, confident-looking shape at all - there just isn't
enough data to tell a real small cluster apart from a couple of people who happen to live near each
other. Rather than force a falsely tidy-looking map in that case, the map is allowed to show a bit of
that genuine uncertainty as several smaller, scattered areas - which is a more honest picture than
hiding it, even though it looks less immediately clean than a name with plenty of bearers gets.

## How we know it works

- `tests/test_stage1.py` builds a small fake database and checks that the counting SQL gives exactly
  the same answer as a second, independent calculation in Python. That check already found one
  mistake (small counts were dropped before spelling variants were merged).
- `tests/test_kde.py` checks the maps: three levels, in the right place, no overlap, on land, inside
  the data contract, small names still show, the weighting dial does what it says and each level
  holds the share of density it claims. `tests/test_rules.py` checks the threshold and the Scotland
  rule, including that a copied map is only built once and matches its reference exactly. A stress
  test on 40 random names found a geometry fault that a single simple blob does not show.
- The fake database contains the awkward cases the real data has: surnames in different cases and
  with punctuation, junk surnames, postcodes without coordinates, two sets of parish numbers, and no
  Scotland in 1911 or 1921.
