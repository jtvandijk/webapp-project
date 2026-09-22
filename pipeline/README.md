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

`--auto-level-mass` replaces `--variants` with one setting per name, from `kde.size_level_mass()` -
a first-draft, exploratory curve (see its docstring) trying to reproduce by eye what real names
seem to need without hand-picking a triple for each one. Each name's own resolved setting (and its
`second_blob_share`, the measure the curve uses to spot a name with more than one comparably strong
region) is labelled under its maps.

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
- `MIN_BLOB_SHARE`: drops a separate concentration that holds less than this share of the name's own
  total (now 2%) - for a handful of people sitting on their own somewhere, not a real concentration.
  Different from `MIN_AREA_KM2` below: at these bandwidths even one person's own smoothed "bump" can
  cover 100+ km2, so an area test alone cannot catch this; only works between concentrations far
  enough apart that the smoothing has already reduced the gap between them to zero (see
  `kde.drop_minor_blobs`'s docstring) - two nearby but visually distinct concentrations are kept or
  dropped together, not compared to each other. Tested on synthetic data only so far.
- `LEVEL_MASS`: the share of a name's density that levels 1, 2 and 3 hold (now 85%, 65%, 40%). `LEVEL_MODE = "peak"` uses `LEVEL_PEAK` instead.
- `SCOTLAND_MAX_SHARE`: when a Scottish name's 1911/1921 map is copied from 1901 instead of built (now more than 30% in Scotland in 1901).
- `SMOOTH_M`, `SIMPLIFY_M`, `MIN_AREA_KM2`: how tidy the outlines are, and how large the files get. `SMOOTH_M` (now
  5000, `preview --smooth 10000` to try) closes gaps/notches narrower than 2x itself - the old pipeline's
  equivalent step (`data-prep/py/fn_prerender.py`) used 10000, twice this, which is a plausible reason its
  outlines read as more solid/concentric than this pipeline's can look at a tight `LEVEL_MASS`. `MIN_AREA_KM2`
  removes tiny specks (`preview --min-area 400` to try); the preview table shows how many separate areas each map has.

`preview.py --min-blob-share 0.05` (etc.) tries a different share without editing `config.py`.

Use `preview.py` after changing any of them.

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
