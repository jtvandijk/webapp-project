# Small input files for the sample data and lookups

Names, descriptions and codes used by `tools/build_sample_data.py` and `tools/build_lookups.py`, mostly kept from the old site, plus a few real map shapes for the sample. Labels and published outlines, not data about people.

| File | What it is | Note |
|---|---|---|
| `oac21_descriptions.csv`, `loac21_descriptions.csv` | Names, colours and descriptions of the OAC and London OAC supergroups and groups | used by `tools/build_sample_data.py` |
| `eee_labels.csv` | The Ethnicity Estimator codes (for example `WAO-DE`) with a country or group name and a census group | from the old site (`lk_eee_label.csv`). Not used by the site. **Known problem:** its census-group column calls the `OXX` codes "Mixed ethnic groups - any other mixed background", but `OXX` is "Other ethnic group" (Algerian, Moroccan, Muslim, ...). `pipeline/config.py` (`ETH_GROUPS`) has the mapping we use |
| `eee_country_codes.csv` | The two-letter country codes and the Ethnicity Estimator code each maps to | from the old site (`lk_onomap_eee.csv`) |
| `kde/smith.json`, `macdonald.json`, `sion.json` | Two real map periods each (trimmed FeatureCollections, keyed by period id), extracted from the real exported release | used by `tools/build_sample_data.py` for real-shaped sample maps - public, disclosure-cleared pipeline output, not raw data (confirmed with the user 2026-10-07) |
| `scotland_mask.json` | The Scotland outline in the exact shape `site/data/masks/scotland.json` needs, copied from the real release's own `masks/scotland.json` | used by `tools/build_sample_data.py`; same provenance note as `kde/` above |

The financial precarity classification's group names and colours are not here: `tools/build_lookups.py` takes the colours from
`raw-indicators/fpc/fpc_label_colors.csv` (git-ignored) and the corrected names from `pipeline/reference/group_names.json` (the file has a
double space after `A01:`, `E12` reads "Underprivilege dependent" and `E13` "Aging"). Only its lookup from area to group is safeguarded.
