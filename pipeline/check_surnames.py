"""How the raw census surname (sname), standardised by names.surname_key(), compares with the old cleaned column
(sname_clean_stand, made by the SQL cleaning function of the old project). It changes nothing and writes nothing.

    python3 -m pipeline.check_surnames                        # every census year in run.settings
    python3 -m pipeline.check_surnames --census-years 1881    # only some years

Why: the pipeline standardises the raw surname the same way in every year, but the old cleaning did more. It moved
what is in brackets and what follows " or " out of the name, removed leading initials, and emptied names that were mostly
punctuation, so "J. SMITH", "SMITH (SMYTH)" and "SMITH OR SMYTH" were all "smith". Read as raw text they become
"jsmith", "smithsmyth" and "smithorsmyth". This report counts the people for whom the two ways give a different name, says
which kind of difference it is, and lists the biggest ones, so that it is clear whether the old cleaning needs to be
rebuilt in the pipeline. Years whose table has no cleaned column are skipped (only some years have it).

It makes one pass over each year's census table, counting people per (raw surname, cleaned surname); the rest is Python.
"""
import argparse
import re
from collections import Counter

from . import config, db, sql
from .names import surname_key

DIFFER_LOOK = 0.01         # more than this share of the people under another name is worth a look
EXAMPLES = 12              # how many of the biggest differences to list

_INITIAL = re.compile(r"^\s*[A-Za-z][\s.]")            # "J. SMITH", "J SMITH"
_OR = re.compile(r"\sor\s", re.I)


def kind_of(raw):
    """What sort of raw value this is, for counting: brackets, an " or ", a leading initial, digits, dots, or something else."""
    text = str(raw or "")
    if "(" in text or ")" in text:
        return "brackets"
    if _OR.search(text):
        return "or"
    if _INITIAL.match(text):
        return "initial"
    if any(ch.isdigit() for ch in text):
        return "digits"
    if "." in text:
        return "dots"
    return "other"


def gather(conn, cfg, years):
    """{year: list of (raw surname, cleaned surname, people)}, or None for a year whose table lacks either column."""
    c = cfg["census"]
    found = {}
    for year in years:
        table = sql.census_tables(cfg, year)[0]
        columns = {name.lower() for name, _ in db.fetch(conn, sql.column_types(cfg, table))}
        if c["surname"].lower() in columns and c["surname_clean"].lower() in columns:
            found[year] = [(raw, clean, int(n)) for raw, clean, n in db.fetch(conn, sql.surname_pairs(cfg, year))]
        else:
            found[year] = None
    return found


def summarise(pairs):
    """How the two ways of reading the surname compare for one year. pairs: (raw, cleaned, people)."""
    total = Counter()
    kinds, biggest = Counter(), []
    for raw, clean, people in pairs:
        new, old = surname_key(raw), surname_key(clean)
        total["people"] += people
        if clean is None or not str(clean).strip():
            total["not_cleaned"] += people                  # no cleaned value at all
        if any(not ch.isalpha() for ch in str(clean or "")):
            total["cleaned_with_other_characters"] += people
        if new == old:
            total["same"] += people
            continue
        if not old:
            label = "emptied by the old cleaning"          # the old cleaning made it NULL: junk, initials only, '?' ...
        elif not new:
            label = "empty when read as raw"
        else:
            label = kind_of(raw)
        kinds[label] += people
        total["differ"] += people
        biggest.append((people, raw, clean, label))
    biggest.sort(key=lambda item: -item[0])
    return {"total": total, "kinds": kinds, "biggest": biggest}


def make_report(data):
    """(lines, problems)."""
    lines, problems = [], []
    lines.append("CENSUS SURNAMES: raw sname (names.surname_key) against the old cleaned column")
    lines.append(f"  {'year':<6}{'people':>14}{'the same':>12}{'different':>12}{'no cleaned value':>18}")
    summaries = {}
    for year, pairs in sorted(data.items()):
        if pairs is None:
            lines.append(f"  {year:<6}  no raw and cleaned surname column in this table: skipped")
            continue
        s = summaries[year] = summarise(pairs)
        t = s["total"]
        people = t["people"]
        lines.append(f"  {year:<6}{people:>14,}{(t['same'] / people if people else 0):>12.2%}{(t['differ'] / people if people else 0):>12.2%}"
                     f"{(t['not_cleaned'] / people if people else 0):>18.2%}")
    for year, s in summaries.items():
        t, people = s["total"], s["total"]["people"]
        if not people:
            problems.append(f"{year}: the census table has no rows")
            lines.append(f"  LOOK: {year}: the census table has no rows")
            continue
        lines.append("")
        lines.append(f"{year}: {t['differ']:,} of {people:,} people would be under another name")
        for label, n in s["kinds"].most_common():
            lines.append(f"    {label}: {n:,} people")
        for people_n, raw, clean, label in s["biggest"][:EXAMPLES]:
            lines.append(f"      {people_n:>9,}  {raw!r} -> raw key {surname_key(raw)!r}; cleaned column {clean!r} (key {surname_key(clean)!r})  [{label}]")
        if t["not_cleaned"] / people > 0.5:
            problems.append(f"{year}: the cleaned column is empty for {t['not_cleaned'] / people:.0%} of the people; the cleaning was probably never run on this year")
            lines.append(f"  LOOK: {problems[-1]}")
        elif t["differ"] / people > DIFFER_LOOK:
            problems.append(f"{year}: {t['differ'] / people:.1%} of the people are under a different name when the raw surname is used")
            lines.append(f"  LOOK: {problems[-1]}")
        if t["cleaned_with_other_characters"]:
            lines.append(f"  {year}: {t['cleaned_with_other_characters']:,} people have a cleaned value that still holds a space, hyphen or other non-letter "
                         "(the sample version of the cleaning script does not remove them all; the function does)")
    lines.append("")
    lines.append(f"{len(problems)} thing(s) to look at" + (":" if problems else "; the two ways of reading the surname agree."))
    lines.extend(f"  - {p}" for p in problems)
    return lines, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--census-years", nargs="*", type=int, default=config.RUN["census_years"],
                        help="which census years to check (default GBNAMES_CENSUS_YEARS in run.settings)")
    args = parser.parse_args()
    print(config.describe_run(), flush=True)
    cfg = config.settings()
    conn = db.connect("census")
    data = gather(conn, cfg, sorted(set(args.census_years)))
    conn.close()
    lines, _ = make_report(data)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
