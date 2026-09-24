# Small lookup files kept from the old site

Names, descriptions and codes that the website will need for its lookups. They are labels, not data about people.

| File | What it is | Note |
|---|---|---|
| `oac21_descriptions.csv`, `loac21_descriptions.csv` | Names, colours and descriptions of the OAC and London OAC supergroups and groups | used by `tools/build_sample_data.py` |
| `eee_labels.csv` | The Ethnicity Estimator codes (for example `WAO-DE`) with a country or group name and a census group | from the old site (`lk_eee_label.csv`). **Known problem:** its census-group column calls the `OXX` codes "Mixed ethnic groups - any other mixed background", but `OXX` is "Other ethnic group" (Algerian, Moroccan, Muslim, ...). `pipeline/config.py` (`ETH_GROUPS`) has the mapping we use; correct this file before it is used for the site |
| `eee_country_codes.csv` | The two-letter country codes and the Ethnicity Estimator code each maps to | from the old site (`lk_onomap_eee.csv`) |

The financial precarity classification's group names and colours are not here yet; they come from
`raw-indicators/fpc/fpc_label_colors.csv` when the site's lookups are built (with two typos to correct: a double space
after `A01:`, and `E12` should read "Underprivileged dependent"). Only its lookup from area to group is safeguarded.
