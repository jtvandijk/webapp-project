# First run in the TRE: checks before anything is exported

**Status: draft, written before the first real run.** Stage 5 has only run on fake data, so improve this
list as the first real run teaches us what actually goes wrong.

Why it exists: anything wrong in the neighbourhood tables or the facts only shows up after a long run and an
export out of the TRE, and then the whole thing has to be run again. Every step below can be done *before*
anything leaves, and each one catches a different kind of mistake. Steps 1 to 5 are about the neighbourhood
tables, 6 to 8 about the facts.

## 1. On your own computer, before uploading

```
python3 tools/prep_neighbourhood.py         # makes work/neighbourhood/nbhd_*.csv and manifest.json
python3 tools/audit_neighbourhood.py        # a second, independent look at every value; must end "no problems found"
shasum -a 256 work/neighbourhood/*.csv      # the checksums; the same ones are in manifest.json
```

## 2. In the TRE: did the upload arrive intact?

In the folder you uploaded the four CSVs to:

```
sha256sum nbhd_*.csv                        # each must equal the checksum in manifest.json
wc -l nbhd_*.csv                            # one more than the row counts below (the header line)
```

## 3. Load them and count

```
python3 -m pipeline.nbhd_tables ddl --csv-dir <that folder> > make_tables.sql
psql ... -f make_tables.sql                 # creates the four tables and loads the CSVs
```

```sql
SELECT 'oac', count(*) FROM registers_lookup.nbhd_oac UNION ALL
SELECT 'loac', count(*) FROM registers_lookup.nbhd_loac UNION ALL
SELECT 'ahah', count(*) FROM registers_lookup.nbhd_ahah UNION ALL
SELECT 'imd', count(*) FROM registers_lookup.nbhd_imd;
-- expect 235,243 / 26,369 / 43,064 / 42,648

SELECT imd_country, count(*) FROM registers_lookup.nbhd_imd GROUP BY 1;
-- expect England 33,755, Wales 1,917, Scotland 6,976
```

## 4. Do they fit the real register?

```
python3 -m pipeline.nbhd_tables check
```

Per country, the share of register rows that find a row in each table. Expect about 99.9% everywhere and
100% of London rows in LOAC; it stops and names the country and table otherwise. A low share in *one* country
usually means a table was joined on the wrong postcode column for that country (see "Which zones, 2011 or 2021?" in the
README), a low share everywhere means an incomplete load.

## 5. Spot-check some postcodes (the most useful step)

`python3 -m pipeline.nbhd_tables lookup "SW1A 1AA" "EH1 1AD" ...` prints what stage 5 will use for each
postcode. These are the answers it should give for six real postcodes (worked out separately, from the
public February 2026 postcode directory and the tables; they hold for that directory and these table versions):

| Postcode | Country | oa21cd | lsoa21cd | lsoa11cd | UK OAC group | LOAC | AHAH decile | Deprivation (decile, percentile) |
|---|---|---|---|---|---|---|---|---|
| SW1A 1AA | England | E00023938 | E01004736 | E01004736 | 3c | A3 | 10 | IoD2025: 8, 73 |
| M1 1AD | England | E00175827 | E01033658 | E01033658 | 3a | none | 10 | IoD2025: 5, 41 |
| TR18 4AA | England | E00096002 | E01019001 | E01019001 | 8b | none | 3 | IoD2025: 3, 24 |
| CF10 1AA | Wales | W00010121 | W01002019 | W01001941 | 3a | none | 10 | WIMD2025: 6, 56 |
| EH1 1AD | Scotland | S00143153 | S01014710 | S01008674 | 3a | none | 10 | SIMD2020v2: 6, 59 |
| G1 1AB | Scotland | S00159099 | S01017410 | S01010260 | 3a | none | 10 | SIMD2020v2: 6, 51 |

What to look for: the Scottish rows join deprivation on `lsoa11cd` (the 2011 zone) and everything else on the
2021 or 2022 codes, and the Welsh row's 2011 and 2021 LSOA codes differ. If the codes match but a value does
not, a table was not loaded as prepared; if the codes themselves differ, the postcode directory in the TRE is
not the February 2026 one.

To see what the *download* itself says for an area code (the other half of the check), copy a code from the
output above and run this on your own computer:

```
python3 tools/audit_neighbourhood.py --show E00023938 E01004736 S01008674
```

It prints the values straight from the downloads, so a code that the TRE tables map to a different value than
the download does shows up at once.

## 6. A small run of stage 5

```
python3 -m pipeline.s5_facts --limit 500        # or qsub pipeline/hpc/stage5.sh for the 5,000-name sample
```

Read `work/facts/report.txt`. Expect most names to have a reference year of 2026 or 2025; "bearers with a value"
close to 100% for OAC, AHAH, IMD and places (lower for ethnicity, depending on how many people have a code,
and around a tenth for LOAC, which covers London only); and look at any ethnicity codes listed as not recognised. Then look at a few
names you know, kept apart from the rest:
`python3 -m pipeline.s5_facts --names smith macdonald --out-dir work/facts_try` (a Scottish name should
come out with Scottish neighbourhood codes, a London one with London ones).

## 7. One name, worked out by hand

This is the check on the Postgres SQL itself, which the tests cannot run. Pick a name from `facts.csv` and
note its `ref_year`; replace `longley` and `2025` below. Each query should give the same top value as `value`,
and the shares should match `detail`'s `distribution` to about three decimals (a tiny difference is possible if
the name is spelled in several ways, since stage 5 merges spellings).

```sql
-- UK OAC group
SELECT t.oac_group, count(*) AS n
FROM registers_linked.lcr_consol2026 r
JOIN registers_lookup.onspd_2026_feb a ON a.stdpcd = r.postcode
JOIN registers_lookup.nbhd_oac t ON t.area_code = a.oa21cd
WHERE regexp_replace(lower(r.surname), '[^a-z]', '', 'g') = 'longley'
  AND r.first <= 2025 AND r.last >= 2025
  AND a.east1m > 0 AND a.north1m > 0 AND a.ctry25cd IN ('E92000001', 'S92000003', 'W92000004')
GROUP BY 1 ORDER BY 2 DESC;

-- deprivation decile (Scotland on the 2011 zones): the same, with this join instead
--   JOIN registers_lookup.nbhd_imd t ON t.area_code =
--        CASE WHEN a.ctry25cd = 'S92000003' THEN a.lsoa11cd ELSE a.lsoa21cd END
--   and  SELECT t.imd_decile, count(*) ...

-- ethnicity: the census group is the start of the code (WAO-DE -> WAO)
SELECT split_part(upper(trim(r.eth)), '-', 1) AS census_group, count(*) AS n
FROM registers_derived.lcr_consol_ethest r
JOIN registers_lookup.onspd_2026_feb a ON a.stdpcd = r.postcode
WHERE regexp_replace(lower(r.surname), '[^a-z]', '', 'g') = 'longley'
  AND r.first <= 2025 AND r.last >= 2025 AND r.eth IS NOT NULL AND trim(r.eth) <> ''
  AND a.east1m > 0 AND a.north1m > 0 AND a.ctry25cd IN ('E92000001', 'S92000003', 'W92000004')
GROUP BY 1 ORDER BY 2 DESC;

-- female forenames, all years (this is the query with the window function, the riskiest one)
SELECT lower(r.forename) AS forename, count(*) AS n
FROM registers_linked.lcr_consol2026 r
JOIN registers_lookup.onspd_2026_feb a ON a.stdpcd = r.postcode
JOIN registers_lookup.lookup_monica g ON lower(g.name) = lower(r.forename)
WHERE regexp_replace(lower(r.surname), '[^a-z]', '', 'g') = 'longley'
  AND upper(substr(trim(g.gender), 1, 1)) = 'F'
  AND a.east1m > 0 AND a.north1m > 0 AND a.ctry25cd IN ('E92000001', 'S92000003', 'W92000004')
GROUP BY 1 ORDER BY 2 DESC LIMIT 12;
-- compare with the "f" list in facts.csv (forenames with fewer than 3 people are left out there)
```

## 8. Before anything is exported

Everything that leaves the TRE is `facts.csv`. A few checks that need nothing but Python:

```python
import csv, collections
rows = list(csv.DictReader(open("work/facts/facts.csv")))
print(collections.Counter(r["fact"] for r in rows))                                   # rows per fact
low = [r for r in rows if r["n_bearers"] and int(r["n_bearers"]) < 100 and r["value"] != "unknown"]
print("facts based on fewer than 100 bearers (must be 0):", len(low))
print("rows with counts in a list (must be 0):", sum('"n"' in r["detail"] for r in rows if r["fact"] in ("places", "forenames_register")))
```

Then look at a sample of rows in a spreadsheet, and check the report has no surprises. If you want, a proper
checker for `facts.csv` (the disclosure floors, the shape of each `detail`) is a small addition.
