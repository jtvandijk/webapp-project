# GBNames

GBNames shows the geography of British surnames: where a name was concentrated in the census years
1851-1921 and in more recent years, plus who tends to bear it (top forenames, top neighbourhoods,
and how it relates to neighbourhood classifications, deprivation, broadband speed and more). The
live site is at [apps.geods.ac.uk/gbnames](https://apps.geods.ac.uk/gbnames/), part of UCL's
Consumer Data Research Centre (CDRC).

## Status: rebuild in progress, on this branch (`dev`)

The site as currently live (source in [`gbnames/`](gbnames/), a Django app backed by Postgres) is
being replaced from scratch, for two reasons:

- **The data needs updating.** New consumer registers (to 2026), the 1921 census, and refreshed
  neighbourhood classifications.
- **The current site does not cope with a traffic spike.** It went down after going viral on social
  media, most likely a Postgres bottleneck - a single name search runs roughly 20 database queries.

The plan (see [docs/pipeline.md](docs/pipeline.md)) is to precompute everything a visitor could ask
for into small static files, so the public site becomes a plain file server with no database and no
per-request computation - unaffected by the kind of load that took the old site down.

`gbnames/` (the currently live Django app) stays in the repository for reference until the rebuild
replaces it; nothing in the rebuild depends on it.

## Where to start reading

| Read this | For |
|---|---|
| [docs/data-contract.md](docs/data-contract.md) | The file format the rebuild produces, and that the future website reads: one JSON file per surname. |
| [docs/pipeline.md](docs/pipeline.md) | The plan for turning individual-level records into that release: stages, decisions made, what is still open. |
| [pipeline/README.md](pipeline/README.md) | How to run the pipeline - on fake data locally, or for real in the TRE. |

## Repository layout

| Path | What it is |
|---|---|
| `pipeline/` | The code that turns censuses and consumer registers into the public release: counting, the map calculation, disclosure rules. Runs partly inside a TRE (Trusted Research Environment), since the source data is individual-level. |
| `docs/` | The data format and the pipeline plan (above). |
| `tools/` | A sample-data generator and a validator for the future website's release format, and `prep_neighbourhood.py`, which turns the downloaded neighbourhood classifications into the lookup tables that go into the TRE. |
| `site/` | An early prototype of the static website (paused; not the current focus). |
| `gbnames/` | The currently live Django app (source of apps.geods.ac.uk/gbnames). Being replaced. |
| `data-prep/` | The old, one-off pipeline code this rebuild replaces, kept locally for reference. **Not tracked in git** (see `.gitignore`) - it is several GB and includes working data extracts. |
| `raw-indicators/` | The downloaded neighbourhood classifications (OAC, LOAC, AHAH, IMD), the input to `tools/prep_neighbourhood.py`. **Not tracked in git.** |
| `work/` | Everything `pipeline/` writes when run locally: fake databases, counts, preview pages. **Not tracked in git.** |

## The data

Historic census microdata (England, Scotland, Wales; 1851-1911 so far, 1921 being added) comes from
the ESRC [I-CeM project](https://www1.essex.ac.uk/history/research/icem/) - population-wide names
and addresses, under a secure data use agreement, geo-referenced to historical parishes (see
[Higgs and Schürer 2014](https://beta.ukdataservice.ac.uk/datacatalogue/studies/study?id=7481) for
background). Names and addresses cannot be released from a census until it is 100 years old; for
1997 onwards, linked consumer registers are used instead (see
[Lansley, Li and Longley 2019](https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/rssa.12476)).

This is individual-level data. It is never published as such: a surname's map is only built for a
year in which it has at least 30 (historic) or 100 (modern) bearers, and nothing at all is shown
below that. This repository holds code, not data - the two folders that could hold real or
realistic-looking extracts (`data-prep/`, `work/`) are both git-ignored.
