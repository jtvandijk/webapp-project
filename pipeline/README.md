# The GBNames pipeline

The code that turns the registers and censuses into the data behind the website (the format is in
[docs/data-contract.md](../docs/data-contract.md), the plan in [docs/pipeline.md](../docs/pipeline.md)).

## What is here

| File | What it does | Status |
|---|---|---|
| `config.py` | **All settings.** Database and table names, years, threshold, map settings. | done |
| `fake_data.py` | Makes a fake database with the same shape as the real one. | done |
| `s1_counts.py` | Stage 1: bearers per name per year, and the list of names that get a page. | done, tested |
| `kde.py` | The map calculation for one name and year. | done, tested |
| `rules.py` | Which maps are left out (fewer than 100 bearers; Scottish names in 1911). | done, tested |
| `preview.py` | Draws a page of maps to look at. | done |
| `sql.py`, `db.py`, `names.py` | The queries, the connection, the surname rule. | done |
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

## Running it in the TRE

1. Open `config.py` and fill in the `"tre"` block (search for `FILL_IN`): the connection details. The
   register (`registers_linked.lcr_consol2026`) is filled in. The ONSPD names (`registers_lookup.onspd_2023_feb`,
   `stdpcd`, `oseast1m`, `osnrth1m`, `ctry`) are guesses from the old scripts, and so is the parish table
   `spatial.conpar…`: check them, and use the newest ONSPD you have.
2. `export GBNAMES_PROFILE=tre` (and give Postgres the password the usual way, `~/.pgpass` or `PGPASSWORD`;
   it is never written in the code).
3. `python3 -m pipeline.s1_counts`. If a table or column name is wrong, Postgres says which. The stage
   prints how many register rows find their postcode in the lookup (it stops below 80%, which means the
   postcodes are written differently in the two tables) and stops if the lookup has a postcode twice,
   since everybody there would count twice.

The coordinates in the lookup must be British National Grid metres (easting, northing). If the
lookup holds latitude and longitude instead, tell me and I will add the conversion.

## Things that are easy to change (all in `config.py`)

- `THRESHOLD`: minimum bearers for a map (100 rows).
- `MAP_YEARS`: which years get a map. The website follows automatically.
- `BANDWIDTH_MIN_M`, `BANDWIDTH_MAX_M`, `BANDWIDTH_N`: how widely each bearer is spread on the map.
- `WEIGHT_POWER`: how much the local population is taken into account (0 = plain density, 1 = fully relative, now 0.5).
- `LEVEL_MASS`: the share of a name's density that levels 1, 2 and 3 hold (now 85%, 65%, 40%). `LEVEL_MODE = "peak"` uses `LEVEL_PEAK` instead.
- `SCOTLAND_MAX_SHARE`: when a Scottish name loses its 1911 map (now more than 25% in Scotland in 1901).
- `SMOOTH_M`, `SIMPLIFY_M`, `MIN_AREA_KM2`: how tidy the outlines are, and how large the files get. `MIN_AREA_KM2` removes
  tiny specks (`preview --min-area 400` to try); the preview table shows how many separate areas each map has.

Use `preview.py` after changing any of them.

## How we know it works

- `tests/test_stage1.py` builds a small fake database and checks that the counting SQL gives exactly
  the same answer as a second, independent calculation in Python. That check already found one
  mistake (small counts were dropped before spelling variants were merged).
- `tests/test_kde.py` checks the maps: three levels, in the right place, no overlap, on land, inside
  the data contract, small names still show, the weighting dial does what it says and each level
  holds the share of density it claims. `tests/test_rules.py` checks the Scotland rule. A stress test on 40 random names found a geometry
  fault that a single simple blob does not show.
- The fake database contains the awkward cases the real data has: surnames in different cases and
  with punctuation, junk surnames, addresses without coordinates, two sets of parish numbers, and no
  Scotland in 1911.
