# Disclosure control in the GBNames release

*As configured on 2026-09-26. The numbers are set in one file, `pipeline/config.py`.*

GBNames turns individual-level records (the register, and the historic censuses 1851-1921) into a set of precomputed
surname pages. All of that happens inside the Trusted Research Environment (the DSH); the only thing meant to leave it is the
finished release: one small file per surname. It contains no individual record, address, postcode or point location.

## What a surname page contains

**Counts.** How many bearers the surname has in each year.

**Maps.** One map per year, showing where the surname is concentrated. Each map has three nested shades. Every shade is
the smallest area that holds a set percentage of the surname's smoothed density (roughly 40%, 65% and 85%), so the darkest
shade is the core and the lightest is the wider region. The percentages are calibrated for each surname, because a
surname with hundreds of thousands of bearers and one with a few hundred cannot be drawn with the same cut-offs. The
density is smoothed over many kilometres and partly adjusted for population, so a map shows where a surname is
concentrated, not simply where most people live.

**Facts.** Where the surname's bearers live, described through their neighbourhoods. Each bearer is linked to the small
area they live in, and the page then says which types of neighbourhood the surname is most concentrated in: the general
neighbourhood classification (OAC, and LOAC for London), the financial precarity classification, deprivation and access
to healthy assets (both as deciles), and a name-based ethnicity estimate. For example, *"31% of bearers live in neighbourhoods of
type X, 22% in type Y"* (made-up numbers). It also lists the ten most common neighbourhoods today, the ten most common historic
parishes, and the ten most common forenames for women and for men.

## The disclosure principles

| # | Principle | Rule | Effect |
|---|---|---|---|
| 1 | **Small counts are not kept** | A surname's bearers in one year are not kept if there are fewer than **10** (either source) | A surname with under 10 bearers in every year appears nowhere. In a published surname, a year with under 10 has no number. |
| 2 | **Small surnames get no page** | Fewer than **100** bearers | A surname gets a page only if it has 100 or more bearers in at least one map year, and each map needs 100 or more bearers in that year. Below that: no map, no facts, no search suggestion. |
| 3 | **Small patches are removed from maps** | A separate patch is dropped if it holds fewer than **5** bearers, under 2% of the surname's total, or covers under 25 km² | A handful of people living on their own somewhere are not drawn as a cluster. |
| 4 | **Maps are blurred and never show points** | Bearers are counted in 1 km squares, smoothed over 8 to 18 km (wider for bigger surnames); outlines are simplified to 400 m | Only the outlines of the three shades are released. Nothing points to a street or household. Census bearers are placed at their parish centre. |
| 5 | **Facts need a minimum of 5** | The most common group, and every neighbourhood, parish or forename listed, must reach **5**. Register neighbourhood facts come from the surname's most recent year with enough bearers. Forenames and the historic parishes are pooled over all years, and need at least 5 counts | Otherwise it is left out. A source only gives facts to a surname with 100 or more bearers in that source in some year: register facts need 100 register bearers in a year, the historic parishes and forenames need 100 census bearers in a census year. |
| 6 | **Lists are short and carry no counts** | At most 10 entries per list | Ranked lists only: the number of people behind each entry is not released. |
| 7 | **Safeguarded data stays safeguarded** | The financial precarity classification's area-to-group lookup is never released | Only a surname's most common group and its shares over the 13 groups are released, never which areas belong to which group. |

The historic census (1851-1921) is over 100 years old and carries no disclosure risk; the same rules are applied to it
anyway, so the two sources behave alike.

## To note

The minimum of 5 applies to the most common group and to every listed item, but the shares over the neighbourhood
classifications, deprivation and healthy-assets deciles and ethnicity groups cover *every* group with any bearer, to 3
decimals. For a surname with 100 bearers, a group of 1 to 4 people shows as 1 to 4 percent. Merging groups under 5 into
"other" is possible.
