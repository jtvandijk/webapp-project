# GBNames data contract (draft 1)

This document says exactly what the data behind the new GBNames website looks like. It is the
handshake between the two halves of the project:

- **the pipeline** (runs in the TRE / on the HPC) *produces* these files;
- **the website** (runs in a browser) *reads* these files, and nothing else. No database.

If both sides keep to this document, they can be built at the same time and swapped freely.

## The idea in one paragraph

Everything about a surname is worked out **in advance** and saved in **one small file per surname**.
When a visitor searches for "smith", the browser downloads `names/sm/smith.json` and draws the
page from it. There is no server code and no query, so a viral day costs the same as a quiet one:
the files are just handed out (and can be cached by a CDN). Words that are the same for every
surname (what "OAC group 3b" is called, its description, its colour) live in one shared file
instead of being repeated in 25,000 files.

## What is in a release

```
data/
  manifest.json          what this release contains: years, colours, map settings, threshold
  lookups.json           shared words and colours (classification names and descriptions, page text)
  masks/scotland.json    extra outline shown on top of the map for some years
  index/<xx>.json        list of surnames per first-two-letters, used for search suggestions
  names/<xx>/<name>.json ONE FILE PER SURNAME: counts, maps and facts
```

`<xx>` is the first two letters of the surname (`sm`), as in the current KDE folders. This keeps
every folder small. A release is just this folder. It can be validated with
`python3 tools/validate_data.py <folder>`, and uploaded as-is to any web server.

## `names/<xx>/<name>.json`: one surname

An example (numbers made up, shape exactly as the validator expects; `maps` shortened):

```json
{
  "schema": 1,
  "name": "smith",
  "counts": {
    "census":   { "1851": 412876, "1861": 430120 },
    "register": { "1997": 1201455, "2016": 1190433 }
  },
  "maps": {
    "1851": { "type": "FeatureCollection", "features": [
      { "type": "Feature", "properties": { "level": 2 },
        "geometry": { "type": "MultiPolygon", "coordinates": [ ... ] } } ] },
    "2016": { "type": "FeatureCollection", "features": [ ... ] }
  },
  "facts": {
    "forenames": { "census":   { "f": ["mary", "elizabeth"], "m": ["john", "william"] },
                   "register": { "f": ["sarah", "emma"],     "m": ["david", "james"] } },
    "places":    { "census":   [ { "area": "Lancashire", "name": "Liverpool" } ],
                   "register": [ { "area": "Leeds",      "name": "Headingley" } ] },
    "oac":  { "group": "3b" },
    "loac": { "group": "A1" },
    "iuc":  { "group": 4 },
    "eee":  { "group": 3 },
    "imd":  { "mode": 4, "mean": 4.2, "sd": 2.4, "distribution": [0.02, 0.08, 0.11, 0.2, 0.18, 0.14, 0.11, 0.08, 0.05, 0.03] },
    "ahah": { "mode": 6, "distribution": [ ... 10 numbers ... ] },
    "bbs":  { "mode": 7, "distribution": [ ... 10 numbers ... ] }
  }
}
```

Rules:

| Field | Rule |
|---|---|
| `name` | Lowercase letters a to z only. It must equal the file name. This is the search key. |
| `counts` | Number of bearers per year, for **every** year we have, not only the mapped ones. Grouped by source (`census`, `register`). Years are text keys. |
| `maps` | One entry per map period, keyed by the period `id` from the manifest. A period is only present if the name has **at least the threshold** (100) bearers that year. A file with no map at all is not published. **Open (agreed 2026-09-23): a missing period should say why** ("no map because too few bearers that year" vs "no map because the concentration wasn't strong enough to show" vs other reasons) rather than the visitor just seeing that slider position is absent - `rules.Resolution.reason` already has this text internally in the pipeline for every omitted period, it just doesn't reach the published files yet. Needs a field (e.g. a `mapNotes` object alongside `maps`, keyed the same way) and website text for it - not yet designed or built. |
| map shape | Standard GeoJSON, longitude/latitude (EPSG:4326), 4 decimal places, `Polygon` or `MultiPolygon`. Each feature has `properties.level` 1, 2 or 3 (1 = concentrated, 3 = most concentrated). The three levels are bands that do not overlap. |
| `facts` | Every entry is optional. **Missing means no data**; the page then says so. Lists are ordered most common first. |
| `forenames` | Lowercase, at most 10 per sex (`f`, `m`) per source. |
| `places` | At most 10 rows per source, most frequent first. The page shows the first 5. `census` are parishes (`area` = registration county or district), `register` are neighbourhoods (`area` = local authority). |
| `oac`, `loac` | The most common **group** code (`"3b"`, `"A1"`). The supergroup follows from the group, via `lookups.json`. |
| `iuc`, `eee` | The most common group number. |
| `imd`, `ahah`, `bbs` | `mode` = most common decile (1 to 10). `distribution` (optional) = share of bearers in each decile, ten numbers adding up to 1. `mean` and `sd` (optional) = average and spread of the decile. |
| `synthetic` | Only in sample data: `true`. Real releases must not have it (see checks below). |

## `manifest.json`: what this release contains

Everything that used to be typed into the code as a list of years now lives here, in one place.

- `release`: version, date, and `synthetic` (true for sample data).
- `threshold`: the minimum number of bearers for a map (100).
- `sources`: `census` and `register`, with the label, what is being counted, and the years covered
  (`coverage`), which page text uses ("over the period 1997-2016").
- `periods`: **the list of map/slider positions**, in order. Each has an `id` (the year as text),
  its `source`, and optionally a `mask` (draw an extra outline) and a `note` shown to the visitor.
- `levels`: label and colour for map levels 1 to 3.
- `masks`: extra outlines. Currently Scotland for 1911, because those census records are not available.
- `basemap`: map centre, zoom limits and the background tile servers.
- `examples`: surnames suggested on the welcome screen.

## `lookups.json`: shared words and colours

- `cards`: titles and explanatory text for every box on the page (so text can be edited without touching code).
- `oac`, `loac`: `supergroups` and `groups`, each with name, colour, description.
- `iuc`, `eee`: name and colour per group number.
- `scales`: colours (and text) for the 10-step decile bars (`imd`, `ahah`, `bbs`).

## `index/<xx>.json`: search suggestions

A sorted list of every surname that has a file, per first two letters, e.g. `index/sm.json` is
`["smith", "smithers", ...]`. The search box loads the right one after two letters are typed and
suggests matches. It only lists names that have a map, so it does **not** reveal which other
names exist below the threshold.

## What the website does with it

1. First visit: load `manifest.json` and `lookups.json` (small, identical for everybody, cached).
2. Search: turn the typed name into the key (lowercase a to z), load `names/<xx>/<name>.json`.
3. File found: draw the slider from the `periods` that the name has a map for, and the boxes from `facts`.
4. File not found (404): show one message: "no map or statistics for this name: either we found no
   records, or it has fewer than 100 bearers (we do not show these, to protect privacy)".

One request per search. Today a search is about 22 database queries plus up to 9 map files one after the other.

## Checks that run before a release is accepted

`tools/validate_data.py` refuses a release when:

- any **map exists for a year with fewer bearers than the threshold** (the disclosure guard);
- a map is not longitude/latitude inside Great Britain (catches un-projected or swapped coordinates);
- a code (OAC group, IUC group, ...) is not in `lookups.json`;
- a file is in the wrong folder, or the name does not match the file name;
- the `synthetic` flag disagrees with the manifest (sample data can never pass as real, or the reverse);
- the `index` does not list exactly the files that exist.

Tested: on a copy of the sample data I broke six of these on purpose (a map below the threshold,
un-projected coordinates, an unknown code, a file in the wrong folder, a wrong `synthetic` flag, an
index that did not match) and the validator caught every one.

## How to add a year or a new classification

- **A new year** (1921, 2026): add one line to `periods` in the manifest, extend `sources.*.coverage`,
  and have the pipeline write that year into `counts` and `maps`. No website code changes.
- **A new version of a classification** (say a new OAC): replace the `oac` block in `lookups.json`
  and write the new group codes into the files. No website code changes.
- **Changing the meaning of a field** (not just adding an optional one) means `schema` becomes 2.

## Sample data and size

`python3 tools/build_sample_data.py` builds a working sample in `site/data/`. The map shapes are the
real ones from the KDE files stored locally (smith, juszczyk and sion; the sion file is an identical copy of the juszczyk file). **Everything else in it is
made up** (counts, forenames, places, classifications) and flagged `synthetic`.

Measured on that sample:

| Surname | Map periods | File size | Compressed (what is sent over the network) |
|---|---|---|---|
| smith (a very large, widespread name) | 9 | 359 KB | about 102 KB |
| juszczyk (a small name, one map) | 1 | 10 KB | about 3 KB |

The total for a full release depends on how many name-years pass the threshold. We will know that
after the counting step of the pipeline.

## Choices I made that you may want to overrule

1. **One file per surname**, not separate "facts" and "maps" files. One request, simplest to publish
   and to output-check. Cost: someone who only wants the facts still downloads the maps.
   (Easy to split later if it matters.)
2. **Plain GeoJSON** for map shapes. Easy to inspect, and Leaflet or MapLibre read it directly.
   A more compact encoding could halve the size if needed.
3. **Codes in the surname files, words in `lookups.json`.** Descriptions can be corrected without regenerating 25,000 files.
4. **Missing means no data**, instead of placeholder values such as `["No data", "No data"]`.
5. **Named fields** instead of the old positional array (`stats[6]`), which broke silently when the order changed.
6. **Not-found is a single message.** The old site could say "we hold records for this name but too few";
   doing that statically would need a public list of every name we hold, including small ones.
7. **Top 10 stored, 5 shown**, so the page can show more later without a new run.
8. **Decile distributions** are new (the old database held them, the old page never showed them).

## What the pipeline has to produce, and what still has to be decided

How the old pipeline did each item (from the code in `data-prep/`), and what needs a decision
before the long run starts.

| Item | How it was done before | Decided (2026-09-23) / still to decide |
|---|---|---|
| `counts` | Census: all residents per name per year (1911 without Scotland). Registers: people with `first_im <= year <= last_im`. | Which years; do register counts stay "adults (estimated)". |
| `maps` | Kernel density on a 1 km grid, bandwidth 8 to 18 km depending on name size and spread, weighted by population, cut into 3 levels, outlines smoothed and clipped to the coast. | Decided: 15 periods and the method (see [pipeline.md](pipeline.md)); the threshold is 100 bearers, both sources. Open: how widespread names should look on real data; `LEVEL_MASS` (the level cut-offs) and `MIN_BLOB_SHARE` will end up varying per name rather than being one constant (see pipeline.md), which is why the settings actually used for a given name's map need recording somewhere - **agreed (2026-09-23): a separate, internal-only settings log written by Stage 4 (per name/period: resolved bandwidth, weighting power, level mode+shares, blob-share threshold, pipeline version), not part of these public files** - keeps this contract's payload lean and the PVC-style numbers out of anything a visitor's browser downloads, while still letting us answer "why does this map look like this" later. Not yet built. Also open: a missing period should say why on the website (see the `maps` row above) - the reason already exists internally, it just isn't published yet. |
| `forenames` | Top 10 per sex. Census pooled over 1851 to 1911. Registers: no year filter, so pooled. | **Pooled** over all years (all census years; all register years), so a name with no 2026 records still has forenames. Historic and contemporary stay two separate lists. Gender for the registers from `registers_lookup.lookup_monica` (unchanged; may change). |
| `places` | Top 10 parishes (1851 or 1901 boundaries); top 10 2011 MSOAs (at least 3 people). | MSOA 2021 (Scotland: intermediate zone) and district come from the postcode directory (`msoa21cd`, `lad25cd`); names are attached after the TRE, so they can change without a new run. **Contemporary list: reference year** (latest year with 100+ bearers), like the other contemporary neighbourhood facts. **Parishes: pooled over all census years as the old code did** (group by county, parish id and name, top 10, id 0 left out), but not its 1911 join mistake (it joined 1911 records to the 1901 table); 1921 uses the 1901 boundaries, to confirm once uploaded. |
| `oac`, `loac` | Most common group among register addresses (2021 versions). | **UK OAC 2021/22** and **London OAC 2021** (London bearers only), most common group in the latest year with 100+ bearers. Prepared by `tools/prep_neighbourhood.py`. |
| `iuc` | Most common group. | **Dropped.** |
| `imd` | Most common decile, plus mean and sd (England/Wales 2019, Scotland 2020). | **England 2025, Wales 2025, Scotland 2020v2.** Each country is ranked on its own, then treated as comparable (a known simplification). Decile 1 = most deprived. The "GBNames deprivation score" is the mean and sd of the percentile. |
| `ahah` | Most common decile (version 3). | **Version 5.1.** Decile 1 = **healthiest**, 10 = least healthy: the opposite way round from `imd`, and the legend must say so. |
| `precarity` (new) | Does not exist yet. | Waiting for the file from a colleague. It will be added to this contract as a further optional fact. |
| `bbs` | Most common broadband class (from a lookup file that appears to be 2017). | **Dropped.** |
| `eee` | Looked up from the surname itself (ONOMAP), no address data. | **Replaced by the Ethnicity Estimator** (modal census group, top three countries). Source: `registers_derived.lcr_consol_ethest`, the register with a person-level `eth` (worked out from forename and surname). The most common `eth` per surname in the reference year; a surname with no usable class is shown as `Unknown` (the page says there are too few data points). The old surname-only ONOMAP lookup is no longer used. What `eth` holds (census groups or country-level codes) is still to confirm. |
