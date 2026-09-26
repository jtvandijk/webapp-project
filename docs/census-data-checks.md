# Getting the census tables ready

One-time work, done once the census and parish tables are loaded (or reloaded) in the TRE, before the pipeline is
asked to read them for real. Not part of an ordinary run - [how-to-build-the-dataset.md](how-to-build-the-dataset.md)
is that, and assumes this page is already done. Redo the parts here that apply after a fresh census data load; the
sname_clean_stand step only after a load that used the original backup again (see "status of this data load" below).

## 1. The parish ids: `python3 -m pipeline.check_parishes`

Once the parish tables (`spatial.conpar1851`, `spatial.conpar1901`) are loaded:

```
python3 -m pipeline.check_parishes | tee work/parish_check.txt
python3 -m pipeline.check_parishes --lookup conpar_lookup.csv     # also compare with the old lookup file
```

It reads the two small parish tables and makes one pass over each year's attributes table (about a minute or two per
year, no maps and no names involved), changes nothing, and prints what it found; the lines that start with `LOOK` are
the ones to read. It shows, per year, the range of parish ids the people carry, how many are id 0 (expected), have no
id, or carry an id that is not in the parish table it should use (or is in the *other* table: the sign of the wrong
table or column). For the tables it shows repeated ids, ids shared between the two tables, parishes without a name
(`-`) or county, counties in capitals, centroids that are missing, at 0,0 or not in metres, and whether the id columns
can hold fractional ids such as `200136.3`.

**A problem with a parish table is a `LOOK` only if census people are in the parishes it touches**, and the line says
how many, per year (`1901 4,512,345 (14.1%)`). A stray shape that nobody carries is only noted ("no census person is
in them"). Each year also has a line "N people (x%) cannot be put on a map: id 0 ..., no id ..., id not in the table
..., parish without a usable location ...", so you can see the whole loss in one place. What the parish tables of the
real data hold, from the shapefiles and the old lookup:

- *Shapes that are not parishes.* 34 small shapes (from 0.001 to 1 km², 5.8 km² in all; ids 211512 to 212175 in
  `conpar1851`, 410374 to 411035 in `conpar1901`, the same shapes in both) have an id that is in no lookup, so no name
  and no county. Three of them are cut into two rows with the same id: those are the repeated ids. The ids of 1851 to
  1911 come from the lookup, so nobody should carry them (the check counts); 1921 people were assigned by point in
  polygon and might be in one. **Stage 1 stops on a repeated id only if people carry it** (and says how many);
  otherwise it notes it and goes on.
- *London in the 1901 numbering* (used for 1901, 1911 and 1921) is not a set of parishes but four units (`London 1`,
  `London 2`, `London 3`, `City of London`, 335 km² in all), each with the parish name `-`. Their people are real, and
  on the maps they sit at those four centroids. In the places lists they are shown as one place, **London parishes**
  (`config.UNNAMED_PARISH_LABELS`; change the rule there). Twenty other parishes are also called `-` in the lookup
  (mostly rural, up to 30 km²); they have no label and are left out of the places lists, and the check says how many
  people that is.
- *Fractional ids.* Six Scottish parishes have ids like `200136.3` (and `300136.3` in the 1901 numbering). The
  attributes columns are integers in every year except 1901, so their people carry a whole number and cannot be told
  from the neighbouring parish; the check gives the most people that could be in the wrong parish (about 5,000 of
  32 million in 1901).
- *1911 and 1921 have hardly any id 0.* About 300,000 people in each have no parish id at all (NULL), and almost
  nobody has id 0 (46 people, the Isle of Man). Stage 1 counts the NULL people with the id-0 people of the other years
  (`config.CENSUS_NULL_PARISH_IS_NONE`).

## 2. The census surname column: `sname_clean_stand`

The pipeline reads the census surname from `sname_clean_stand`, the surname as cleaned by the old project (leading
initials, bracketed text and everything after " or " removed, names that are only junk emptied), and then applies
`surname_key()` to it as for the register. The census tables in the TRE are the original backup, which does not have
that column, so it is made there, for every year, by two files in `tools/sql/` (both go in the same folder in the
TRE): `census_sname_clean_stand.sql` (the cleaning, as plain SQL) and `make_sname_clean_stand.sh` (runs it for each
year that lacks the column). It needs `psql` and the census settings of `.env`, and nothing else.

```
cd <project folder>
set -a; source .env; set +a                                 # only the database settings; no GBNAMES_PROFILE needed
bash tools/sql/make_sname_clean_stand.sh --list             # which years have the column: changes nothing. Expect "lacks" for all seven
```

Before the first real run, two things about the size. Each year's step rewrites every person of that table, so
**while it runs the table needs room for a second copy of itself** on the disk (the biggest year is the one to look
at):

```sql
SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) FROM pg_class WHERE relnamespace = 'census'::regnamespace AND relkind = 'r' ORDER BY 1;
```

And do it **before building the other indexes on that table where you can**: if the recid/source indexes are already
there the step still works, but it is slower (every index is updated for every person) and they come out bloated;
then run `REINDEX TABLE census.gb<year>;` afterwards, or drop them before and build them again after. Expect tens of
minutes per year, not seconds.

Then start with one year, read what it prints, and do the rest:

```
bash tools/sql/make_sname_clean_stand.sh 1851
nohup bash tools/sql/make_sname_clean_stand.sh > sname_clean.log 2>&1 &     # the other six, one after the other; follow it with:  tail -f sname_clean.log
```

Each year is one transaction: if it stops (an error, a lost connection) that year is left exactly as it was, and
running the same command again does the years that are still missing (a year that has the column is skipped, never
redone). For each year it prints three small tables, in this order. Read them:

- **the biggest names the cleaning changed** (raw name, number of people, cleaned name): worth a glance, in case that
  year has junk that the old rules do not know;
- **people and people_with_no_cleaned_name**: the people whose name the cleaning empties. They are not counted, and
  stage 1 shows them under "not counted although they should be". Should be a small share;
- **people, with_a_surname, with_a_cleaned_name**: with_a_cleaned_name is with_a_surname minus the emptied names.

When it is done, `--list` says "has sname_clean_stand" for every year. The helper tables it leaves
(`census.sname_1851` and so on, the different names of a year with their cleaning, about a million rows each) are for
looking at; the pipeline does not use them.

The old cleaning has its quirks (only the first dot of a name is turned into a space, so "A. B. SMITH" becomes
`bsmith`; digits are only partly removed), and they are kept on purpose: every year is then cleaned in the same way.

**The surname index goes on this column**, after the step above:

```sql
CREATE INDEX ... ON census.gb<year> ((regexp_replace(lower(sname_clean_stand), '[^a-z]', '', 'g')));
```

An index on `sname` is not used.

## Status of this data load

**2026-09-26.** `check_parishes` ran on the real data: 12 things came up, all explained above, none of them a real
problem (id-0 double-counting turned out to be a bug in the check's own query, not in the data - fixed, see the
commit history of `pipeline/sql.py`). `1911` was added to `config.CENSUS_NULL_PARISH_IS_NONE` after confirming its
"no id" figure (about 300,000) is the same "not in a parish" case as 1921, not a real gap. All seven census years now
have `sname_clean_stand`, and it is indexed, along with `(recid, source)`. `bash tools/sql/make_sname_clean_stand.sh
--list` should say "has sname_clean_stand" for all seven; if a table is ever reloaded from the original backup, that
year loses the column and this page's section 2 needs doing again for it.
