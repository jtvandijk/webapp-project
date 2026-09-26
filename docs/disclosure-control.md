# Disclosure control in the GBNames release

*As configured on 2026-09-26. Every number below is set in one file, `pipeline/config.py`; if one changes, this page should too.*

GBNames turns individual-level records (the register, and the historic censuses 1851-1921) into precomputed surname maps
and facts. All of that happens inside the Trusted Research Environment (TRE). The only thing meant to leave it is the
finished **release folder**: one small file per surname holding counts, map outlines and a few summary facts. It contains
no individual record, no address or postcode, and no point locations.

## The measures in one table

| # | Measure | Rule | What it means in practice |
|---|---|---|---|
| 1 | **Small counts are never kept** | A surname's bearers in one year, in either source, are not kept if there are fewer than **10** (`COUNT_FLOOR`) | A surname with under 10 bearers in every year appears nowhere in the release. For a surname that is published, a year with under 10 bearers simply has no number. |
| 2 | **Small surnames get no page** | Fewer than **100** bearers (`THRESHOLD`, both sources) | A surname gets a page only if, in at least one of the 15 map years, it has 100 or more bearers. Each map needs 100 or more bearers *in that year*. No map, no facts and no search suggestion for anything below. |
| 3 | **Small patches are removed from maps** | A separate patch on a map is dropped if it holds fewer than **5** bearers (`MIN_BLOB_BEARERS`), less than 2% of the surname's total (`MIN_BLOB_SHARE`), or covers under 25 km² (`MIN_AREA_KM2`) | A handful of people living on their own somewhere are not drawn as a "cluster". |
| 4 | **Maps are blurred, never points** | Bearers are counted in 1 km squares and smoothed over an 8 to 18 km radius (wider for bigger surnames); outlines are simplified to 400 m and written to about 100 m (3 decimals) | Only the outlines of three density bands are released. Nothing can be traced to a street or a household. Census bearers are placed at their parish centre, not an address. |
| 5 | **Facts need at least 5 people** | The most common group or decile must have at least **5** bearers, and every neighbourhood, parish or forename listed needs at least **5** people (`FACT_MIN_IN_CATEGORY`) | Otherwise the fact is left out. Register facts are also only made for a surname with 100 or more register bearers in some year. Ethnicity says "unknown" when no group reaches 5. |
| 6 | **Lists are short and carry no counts** | 10 forenames per sex, 10 neighbourhoods, 10 parishes (`FORENAMES_TOP`, `PLACES_TOP`) | Ranked lists only: the number of people behind each entry is not released. |
| 7 | **The safeguarded classification stays safeguarded** | The Financial Precarity Classification's area-to-group lookup is safeguarded data and is never released | Only a surname's most common group (one of 13) and the shares per group are released, never which areas belong to which group. |
| 8 | **Only aggregates leave** | The pipeline runs in the TRE; only the release folder is intended to leave | The search index lists only surnames that have a page, so it does not reveal which other names exist. |

The historic census (1851-1921) is over 100 years old and is treated as carrying no disclosure risk. The same rules are
applied to it anyway, so the two sources behave alike and the maps are not thin or noisy.

## How each measure is enforced, and checked

| Stage | What it does for disclosure control |
|---|---|
| 1. Counts | Applies the floor of 10 before anything else is written, and makes the list of surnames with 100 or more bearers in some map year. |
| 4. Maps | For each surname and year: builds a map only from 100 or more bearers, otherwise leaves it out. Removes small patches (measure 3). |
| 5. Facts | Applies the minimum of 5 (measure 5) and keeps the lists short (measure 6). |
| 6. Assemble | Writes a file only for a surname that has at least one map, and facts only for surnames that have a file. |
| Validator (`tools/validate_data.py`) | Checks the finished files independently of the pipeline: no map for a year whose count is under 100 (for a copied map, the count of the year it was copied from), no facts for a surname without a file, the search index lists exactly the published names, coordinates are plausible. It was tested by deliberately breaking files, and every break was caught. |

The pipeline also has an automated test suite (over 340 tests), including checks that a rule really does stop what it is
meant to stop when the rule is deliberately broken.

One rule worth knowing: in 1911 and 1921 the census does not cover Scotland, so a mostly Scottish surname shows its 1901
map for those years. That only happens if the 1901 map itself had 100 or more bearers, and the validator checks the 1901
count.

## What is not covered, or still to be decided

Listed so that nobody has to find them:

1. **Shares over all groups.** The rule of 5 applies to the headline group and to every listed item, but the shares for
   the neighbourhood classifications, the deprivation deciles and the ethnicity groups run over *every* group with any
   bearer, to 3 decimals. For a surname with 100 bearers, a group with 1 to 4 bearers appears as 1 to 4 percent, and
   since a surname's bearers per year are published, the count behind it can usually be worked out. Suppressing or merging
   groups under 5 is possible and is a decision for the group.
2. **The minimum of 5 for map patches is a starting judgement, not a validated value.** A patch that just survives
   represents about 5 people, drawn as a blurred area at least 8 km across, never as points.
3. **Counts are exact, not rounded.** A published surname shows its exact bearer count for every year with 10 or more,
   including years below 100 that have no map.
4. **The validator does not re-check the floor of 10 or the minimum of 5.** Those are enforced when the numbers are
   calculated, and again only through the tests.
5. **This page covers what the pipeline itself enforces.** The TRE's own output checking is separate and still applies.
6. **Numbers from the real run** (how many surnames get a page, how many maps and facts were left out by each rule) are
   not in this page yet; they can be added once the validation of the full release is finished.
