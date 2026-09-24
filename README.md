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
| [docs/how-to-build-the-dataset.md](docs/how-to-build-the-dataset.md) | The steps in order, every setting and where it lives, how to preview a few names, how to follow a job. |
| [docs/first-run-checks.md](docs/first-run-checks.md) | What to check on the first real run in the TRE, before anything is exported. |

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
year in which it has at least 100 bearers, and nothing at all is shown below that. This repository holds
code, not data - the two folders that could hold real or realistic-looking extracts (`data-prep/`,
`work/`) are both git-ignored, and so is `raw-indicators/` (downloads of neighbourhood classifications, see
below: mostly public, but not ours to redistribute, and one of them, the financial precarity lookup from area to
group, is **safeguarded data that must never be published**).

### Neighbourhood classifications

What the site says about the neighbourhoods a surname's bearers live in comes from published classifications,
each looked up through a bearer's postcode using the ONS Postcode Directory (ONSPD). The downloads are kept
in `raw-indicators/`; [`tools/prep_neighbourhood.py`](tools/prep_neighbourhood.py) turns them into five small
lookup tables in `work/neighbourhood/`, and the `manifest.json` next to them records each table's geography,
the direction of its scale and a checksum. The table below is the same information.

| Product | Version | Areas | Joined on this ONSPD column | Direction of the scale |
|---|---|---|---|---|
| UK OAC | 2021/22 | output areas: 2021 (England, Wales), **2022 (Scotland)** | `oa21cd` | groups, no order |
| London OAC | 2021 | output areas 2021, London only | `oa21cd` | groups, no order |
| AHAH (healthy neighbourhoods) | v5.1 | LSOAs 2021 (England, Wales), **data zones 2022 (Scotland)** | `lsoa21cd` | rank and decile **1 = healthiest, 10 = least healthy** |
| Deprivation | England IoD 2025, Wales WIMD 2025, Scotland SIMD 2020v2 | LSOAs **2021** (England, Wales), data zones **2011 (Scotland)** | `lsoa21cd` (England, Wales), **`lsoa11cd` (Scotland)** | rank, decile and percentile **1 = most deprived** |
| Financial precarity, Zi and Singleton (**the lookup from area to group is safeguarded: never in this repository**) | published paper | LSOAs 2021 (England, Wales), **data zones 2022 (Scotland)**, the same zones as AHAH | `lsoa21cd` | 13 groups inside 5 clusters, no order claimed |

**Which zones, 2011 or 2021?** There is no conversion between them. ONSPD carries both the 2011 and the 2021
(Scotland: 2022) code for every postcode, and each classification is joined on the column that matches the
zones it was published for. The one place the two mix is Scotland: its deprivation index (SIMD 2020v2) is on
the 2011 data zones, while AHAH and OAC use the 2022 ones. Joining on the wrong column does not fail loudly: in
England about 6% of postcodes are in a zone whose code changed between 2011 and 2021, and they would quietly
find no value (and a handful would pick up a different zone's value). `python3 -m pipeline.nbhd_tables check`
reports the share per country, and would show it.

**The scales run opposite ways.** AHAH decile 1 is the *healthiest* neighbourhood; the deprivation decile 1 is the
*most deprived*. Anything that draws or words either scale has to say which end is which.

**What is published and what we worked out.** Kept exactly as published: the OAC and LOAC groups, the AHAH rank
and percentile, and every deprivation rank. Worked out here, from the published ranks: the AHAH decile (v5.1
publishes none), the Scottish deprivation decile (SIMD publishes ranks only) and, for all three countries,
the deprivation percentile, as `ceil(10 or 100 x rank / number of areas in the country)`. Where a decile is
published (England, Wales) ours matches it: exactly for all 33,755 English areas, and for 1,913 of 1,917 Welsh ones
(the other four sit on a boundary and differ by one decile). The AHAH score is rounded to three decimals. Northern
Ireland is not covered.

**Deprivation is ranked within each country and then treated as comparable.** A Scottish neighbourhood at
percentile 1 counts as the same as an English one at percentile 1. They are not strictly comparable (three
different indices), but this is the agreed simple comparison. The "GBNames deprivation score" is the mean and
spread of this percentile among a surname's bearers, and the modal deprivation decile is its most common decile.

**Checking it.** [`tools/audit_neighbourhood.py`](tools/audit_neighbourhood.py) re-reads the downloads with
separate code and compares every value with the tables (`--show CODE` prints what the downloads say for an area).
In the TRE, `python3 -m pipeline.nbhd_tables check` and `lookup <postcode>` test the loaded tables against the real
register; [docs/first-run-checks.md](docs/first-run-checks.md) lists the steps, with expected answers for six real postcodes.
