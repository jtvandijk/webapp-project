"""Make a FAKE database with the same shape as the real registers and censuses.

Nothing in it is real: the people, addresses and surnames are all invented, so it can be made and
used anywhere, including a laptop. It exists so that every pipeline stage can be developed and
tested without the TRE.

What it contains (see the FILL_IN block in config.py for the real names):
  register         one row per person at an address: forename, surname, postcode, first, last
  postcode_lookup  postcode -> easting, northing (British National Grid metres) and country code,
                   like the ONS Postcode Directory. Postcodes are written the way the linked
                   registers write them: lower case, no spaces ("ab123cd"). A few postcodes have
                   no grid reference (0 or empty), a few are missing altogether, and a few are in
                   Northern Ireland (to be filtered out: we map Great Britain only). It also has
                   made-up neighbourhood codes (2021 output area, LSOA and MSOA, the 2011 LSOA, and a
                   district), a small share of them blank.
  nbhd_oac, nbhd_loac, nbhd_ahah, nbhd_imd, nbhd_fpc
                   made-up neighbourhood tables for those codes, in exactly the shape of the real ones
                   (tools/prep_neighbourhood.py), with a few areas missing. LOAC is London only, and
                   Scottish deprivation is on the 2011 data zones, like the real thing.
  register.eth     a made-up Ethnicity Estimator code per person (lower case, like the real column),
                   some missing, a few unusable, and no estimate at all for some surnames.
  gb1851 ...       census people, one table per census year, plus gb1851_att with parish and sex
  conpar1851/1901  parish boundaries (centroid x, y), with DIFFERENT id numbers in the two versions
  forename_gender  forename -> M/F, used for the registers

Awkward things are put in on purpose, because the real data has them too: surnames written in
different cases and with punctuation, junk surnames ("XXXX", "nan"), postcodes without
coordinates, census people without a parish, and no Scotland in 1911 or 1921.

The invented geography: about 45 towns with real-ish positions and sizes. Each surname is
"widespread" (follows the population), "regional" (a few home towns) or "local" (one home town),
which gives maps of every kind. The truth about each surname is saved next to the database in
fake_truth.json so tests and previews can choose interesting examples.

    python3 -m pipeline.fake_data                       # the default size, about a minute
    python3 -m pipeline.fake_data --persons 20000 --surnames 800     # a quick small one
"""
import argparse
import json
import sqlite3
import time
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import shape

from . import config
from .names import surname_key

# name, county, easting, northing, relative size, in Scotland
TOWNS = [
    ("London", "Greater London", 530000, 180000, 9.0, 0), ("Birmingham", "Warwickshire", 407000, 287000, 2.9, 0),
    ("Manchester", "Lancashire", 384000, 398000, 2.8, 0), ("Leeds", "Yorkshire", 430000, 433000, 1.9, 0),
    ("Glasgow", "Lanarkshire", 259000, 665000, 1.8, 1), ("Liverpool", "Lancashire", 335000, 390000, 1.5, 0),
    ("Sheffield", "Yorkshire", 435000, 387000, 1.4, 0), ("Bristol", "Gloucestershire", 359000, 173000, 1.1, 0),
    ("Newcastle", "Northumberland", 425000, 564000, 1.1, 0), ("Edinburgh", "Midlothian", 326000, 673000, 0.9, 1),
    ("Nottingham", "Nottinghamshire", 457000, 340000, 0.9, 0), ("Leicester", "Leicestershire", 458000, 304000, 0.8, 0),
    ("Cardiff", "Glamorgan", 318000, 177000, 0.7, 0), ("Southampton", "Hampshire", 442000, 112000, 0.7, 0),
    ("Portsmouth", "Hampshire", 464000, 101000, 0.6, 0), ("Brighton", "Sussex", 531000, 105000, 0.6, 0),
    ("Plymouth", "Devon", 247000, 54000, 0.5, 0), ("Norwich", "Norfolk", 623000, 308000, 0.5, 0),
    ("Aberdeen", "Aberdeenshire", 394000, 806000, 0.4, 1), ("Swansea", "Glamorgan", 265000, 193000, 0.4, 0),
    ("Hull", "Yorkshire", 509000, 428000, 0.5, 0), ("Stoke", "Staffordshire", 388000, 347000, 0.5, 0),
    ("Coventry", "Warwickshire", 433000, 279000, 0.5, 0), ("Bradford", "Yorkshire", 416000, 433000, 0.6, 0),
    ("Exeter", "Devon", 292000, 92000, 0.4, 0), ("Truro", "Cornwall", 182000, 44000, 0.15, 0),
    ("Inverness", "Inverness-shire", 266000, 845000, 0.15, 1), ("Carlisle", "Cumberland", 340000, 555000, 0.2, 0),
    ("Dundee", "Angus", 340000, 730000, 0.3, 1), ("Cambridge", "Cambridgeshire", 545000, 258000, 0.35, 0),
    ("Oxford", "Oxfordshire", 451000, 206000, 0.4, 0), ("Ipswich", "Suffolk", 616000, 244000, 0.3, 0),
    ("Lincoln", "Lincolnshire", 497000, 371000, 0.2, 0), ("York", "Yorkshire", 460000, 452000, 0.3, 0),
    ("Preston", "Lancashire", 354000, 429000, 0.4, 0), ("Middlesbrough", "Yorkshire", 449000, 520000, 0.4, 0),
    ("Gloucester", "Gloucestershire", 383000, 218000, 0.3, 0), ("Canterbury", "Kent", 615000, 157000, 0.2, 0),
    ("Shrewsbury", "Shropshire", 350000, 312000, 0.15, 0), ("Newport", "Monmouthshire", 331000, 187000, 0.3, 0),
    ("Wrexham", "Denbighshire", 333000, 350000, 0.15, 0), ("Bangor", "Caernarvonshire", 257000, 372000, 0.08, 0),
    ("Penzance", "Cornwall", 147000, 30000, 0.1, 0), ("Perth", "Perthshire", 312000, 723000, 0.1, 1),
    ("Bath", "Somerset", 375000, 165000, 0.3, 0), ("Dorchester", "Dorset", 369000, 90000, 0.15, 0),
    ("Kendal", "Westmorland", 351000, 492000, 0.1, 0),
]
CORNISH = ("Truro", "Penzance", "Plymouth", "Exeter")
WELSH = ("Cardiff", "Swansea", "Newport", "Wrexham", "Bangor")

PREFIXES = ("Ash Bar Cal Dan Eld Fen Gar Hal Ivo Jen Kel Lan Mar Nor Ost Pen Quin Rad Sal Tre "
            "Ulm Ven Wat Yor Zel Bram Corn Dun Elm Fal").split()
MIDDLES = "a e i o u an en er in ol ar or".split()
SUFFIXES = "ton ford well by ham son wick ley worth field man den more dale ridge".split()
SPECIAL = ["O'Brien", "MacDonald", "Smith-Jones", "Müller", "D'Arcy", "McKenzie"]   # to test the key rule

FEMALE = ("mary elizabeth sarah ann jane margaret emma alice catherine susan helen joan eleanor grace "
          "ruth hannah lucy olivia edith florence ada annie emily louisa martha rose clara agnes "
          "ellen harriet lilian doris kathleen sylvia irene betty maureen pauline gwen megan freya").split()
MALE = ("john william george thomas james henry charles robert david peter edward arthur frederick "
        "joseph samuel daniel oliver jack albert walter harry frank ernest alfred herbert percy "
        "sidney leonard stanley norman ronald kenneth roy dennis colin trevor keith barry owen alan").split()

LETTERS = "ABCDEFGHJKLMNPRSTUWXYZ"


def fake_postcode(i):
    """A unique made-up postcode for address number i, in the standardised form (ab123cd)."""
    a, i = LETTERS[i % 22], i // 22
    b, i = LETTERS[i % 22], i // 22
    d1, i = i % 99 + 1, i // 99
    d2, i = i % 9 + 1, i // 9
    return f"{a}{b}{d1}{d2}{LETTERS[i % 22]}A".lower()


LONDON = 0                     # the index of London in TOWNS: the only place LOAC covers
ETH_CODES = ("wbr wbr wbr wbr wbr wbr wir wao wao-pl wao-de baf baf-ng bca ain apk abd acn aao-ir oxx-dz").split()
LOAC_GROUPS = "A1 A2 A3 B1 B2 C1 C2 D1 D2 D3 E1 E2 F1 F2 G1 G2".split()
FPC_GROUPS = "A01 A02 B03 B04 B05 C06 C07 C08 D09 D10 E11 E12 E13".split()       # only the shape of the real codes; the values are invented
IMD_COUNTRIES = {"E": ("England", "IoD2025"), "W": ("Wales", "WIMD2025"), "S": ("Scotland", "SIMD2020v2")}


def make_areas(rng, town, country):
    """Made-up neighbourhood codes for every address, shaped like the ONS Postcode Directory's: 2021
    output area, LSOA and MSOA, the 2011 LSOA, and a district. Each town has 6 output areas, 3 LSOAs and
    2 MSOAs. Most 2011 LSOAs are the same as in 2021 and some were re-drawn (a different code); Scotland's
    2011 data zones are all different from its 2022 ones. About 1.5% of addresses have no codes at all,
    half written as empty text and half as missing."""
    n = town.size
    oa = rng.integers(0, 6, n)
    blank = rng.random(n) < 0.015
    out = {key: [] for key in ("oa", "lsoa", "lsoa_2011", "msoa", "district")}
    for i in range(n):
        if blank[i]:
            for key in out:
                out[key].append(None if i % 2 else "")
            continue
        p, t, o = country[i][0], int(town[i]), int(oa[i])
        lsoa = o // 2
        redrawn = p == "S" or lsoa == 2
        out["oa"].append(f"{p}00{t:03d}{o:03d}")
        out["lsoa"].append(f"{p}01{t:03d}{lsoa:03d}")
        out["lsoa_2011"].append(f"{p}01{t:03d}{lsoa + 100 if redrawn else lsoa:03d}")
        out["msoa"].append(f"{p}02{t:03d}{lsoa // 2:03d}")
        district = "E09" if t == LONDON else {"E": "E06", "W": "W06", "S": "S12"}.get(p, "N09")
        out["district"].append(f"{district}{t:03d}000")
    return out


def _share(rank, n, parts):
    """Which of `parts` equal slices of a ranking of n a rank falls in (the same rule as tools/prep_neighbourhood.py)."""
    return -(-rank * parts // n)


def make_nbhd_tables(rng, areas):
    """The four neighbourhood tables, with the columns of config.NBHD_TABLE_COLUMNS, for the areas that
    appear in `areas`. The classes follow the town somewhat, so a surname's neighbourhood type follows its
    home towns, and about 1% of areas are missing from each table."""
    codes = {key: sorted({c for c in values if c and c[0] in "EWS"}) for key, values in areas.items()}
    keep = lambda cs: [c for c in cs if rng.random() > 0.01]
    tables = {"oac": [], "loac": [], "ahah": [], "imd": [], "fpc": []}

    for c in keep(codes["oa"]):
        t, o = int(c[3:6]), int(c[6:9])
        supergroup = (t * 3 + o) % 8 + 1 if rng.random() < 0.7 else int(rng.integers(1, 9))
        group = f"{supergroup}{'abc'[(o if rng.random() < 0.7 else int(rng.integers(0, 3))) % 3]}"
        tables["oac"].append((c, str(supergroup), group, f"{group}{int(rng.integers(1, 4))}"))
    for c in [c for c in codes["oa"] if c[0] == "E" and int(c[3:6]) == LONDON]:      # only 6, so none are dropped
        group = LOAC_GROUPS[(int(c[6:9]) * 5 + int(rng.integers(0, 3))) % len(LOAC_GROUPS)]
        tables["loac"].append((c, group[0], group))

    lsoa = keep(codes["lsoa"])                       # AHAH is one ranking of Great Britain: 1 = healthiest
    score = np.array([int(c[3:6]) * 0.2 + rng.random() * 10 for c in lsoa])
    rank = np.empty(len(lsoa), int)
    rank[np.argsort(score)] = np.arange(1, len(lsoa) + 1)
    for c, sc, r in zip(lsoa, score, rank):
        tables["ahah"].append((c, round(float(sc), 3), int(r), int(_share(r, len(lsoa), 100)),
                               int(_share(r, len(lsoa), 10))))

    for letter, (country, source) in IMD_COUNTRIES.items():          # deprivation: ranked within each country, 1 = most deprived
        own = keep([c for c in (codes["lsoa_2011"] if letter == "S" else codes["lsoa"]) if c[0] == letter])
        score = np.array([-int(c[3:6]) * 0.2 + rng.random() * 10 for c in own])
        rank = np.empty(len(own), int)
        rank[np.argsort(-score)] = np.arange(1, len(own) + 1)
        for c, r in zip(own, rank):
            tables["imd"].append((c, country, source, int(r), len(own), int(_share(r, len(own), 100)),
                                  int(_share(r, len(own), 10))))

    for c in keep(codes["lsoa"]):                    # last, so the draws for the tables above are as they were
        t, o = int(c[3:6]), int(c[6:9])
        group = FPC_GROUPS[(t * 2 + o + (0 if rng.random() < 0.7 else int(rng.integers(0, 13)))) % len(FPC_GROUPS)]
        tables["fpc"].append((c, group[0], group))
    return tables


def make_eth(rng, surname_of_person, n_surnames):
    """A made-up Ethnicity Estimator code for every person: mostly their surname's usual code, some
    missing, and a few that are not in the code list. Some surnames never get an estimate."""
    codes = np.array(ETH_CODES)
    usual = rng.choice(codes, size=n_surnames)
    usual[np.arange(n_surnames) % 23 == 0] = ""
    person = np.where(rng.random(surname_of_person.size) < 0.88, usual[surname_of_person],
                      rng.choice(codes, size=surname_of_person.size))
    person[usual[surname_of_person] == ""] = ""
    person[(rng.random(person.size) < 0.03) & (person != "")] = ""
    person[(rng.random(person.size) < 0.002) & (person != "")] = "waos-k"        # not a real code
    loud = (rng.random(person.size) < 0.05) & (person != "")                     # a few written in capitals
    person[loud] = np.char.upper(person[loud])
    return np.where(person == "", None, person)


CENSUS_SIZE = {1851: .55, 1861: .60, 1881: .75, 1891: .85, 1901: .95, 1911: 1.0, 1921: 1.05}


def load_outline():
    doc = json.loads((config.REFERENCE / "gb_outline.geojson").read_text())
    outline = shape(doc["features"][0]["geometry"])
    shapely.prepare(outline)
    return outline


def land_points(rng, outline, cx, cy, sigma):
    """Points scattered around (cx, cy), redrawn while they fall in the sea."""
    x = cx + rng.normal(0, sigma)
    y = cy + rng.normal(0, sigma)
    for _ in range(15):
        sea = ~shapely.contains_xy(outline, x, y)
        if not sea.any():
            break
        x[sea] = cx[sea] + rng.normal(0, sigma[sea])
        y[sea] = cy[sea] + rng.normal(0, sigma[sea])
    return x, y


class Pool:
    """A set of places (addresses or parishes), grouped by town so we can pick one in a given town."""

    def __init__(self, rng, outline, towns, size, weights, min_per_town):
        t = len(towns)
        town_of = np.concatenate([np.repeat(np.arange(t), min_per_town),
                                  rng.choice(t, size=size - t * min_per_town, p=weights)])
        rural = rng.random(town_of.size) < 0.30
        sigma = np.where(rural, 25000.0, 5000.0)
        tx = np.array([tw[2] for tw in towns], float)[town_of]
        ty = np.array([tw[3] for tw in towns], float)[town_of]
        self.x, self.y = land_points(rng, outline, tx, ty, sigma)
        self.town = town_of
        self.order = np.argsort(town_of, kind="stable")
        self.count = np.bincount(town_of, minlength=t)
        self.start = np.concatenate([[0], np.cumsum(self.count)[:-1]])

    def pick(self, rng, towns):
        """One random member of each of the given towns."""
        return self.order[self.start[towns] + (rng.random(towns.size) * self.count[towns]).astype(int)]


def make_surnames(rng, n):
    combos = [p + m + s for p in PREFIXES for m in MIDDLES for s in SUFFIXES]
    names = [c for c in rng.permutation(combos)[: n - len(SPECIAL)]]
    for rank, special in zip((12, 25, 40, 60, 80, 100), SPECIAL):
        names.insert(min(rank, len(names)), special)
    return np.array(names[:n]), np.array([surname_key(x) for x in names[:n]])


def surname_geography(rng, n, town_w, names_of_towns):
    """For each surname: its kind, how strongly it clings to its home towns, and up to 3 home towns."""
    t = len(town_w)
    kind = np.full(n, "local", dtype=object)
    kind[:8] = "widespread"
    kind[8:][rng.random(n - 8) < 0.35] = "regional"
    conc = np.zeros(n)
    home = np.zeros((n, 3), int)
    scottish = [i for i, tw in enumerate(TOWNS) if tw[5]]
    cornish = [i for i, tw in enumerate(TOWNS) if tw[0] in CORNISH]
    pull = np.sqrt(town_w) / np.sqrt(town_w).sum()
    for s in range(n):
        if kind[s] == "widespread":
            continue
        roll = rng.random()
        if kind[s] == "regional":
            chosen = rng.choice(t, size=3, replace=False, p=pull)
            conc[s] = rng.uniform(0.45, 0.70)
        else:
            first = rng.choice(scottish) if roll < 0.20 else rng.choice(cornish) if roll < 0.28 \
                else rng.choice(t, p=pull)
            chosen = np.array([first, first, first])
            conc[s] = rng.uniform(0.60, 0.92)
        home[s] = chosen
    return kind, conc, home


def draw_towns(rng, s_idx, conc, home, national, strength=1.0):
    n = s_idx.size
    at_home = rng.random(n) < conc[s_idx] * strength
    return np.where(at_home, home[s_idx, rng.integers(0, 3, n)], rng.choice(national.size, size=n, p=national))


def generate(persons=250000, surnames=5000, seed=1, path=None, quiet=False):
    started = time.time()
    say = (lambda *a: None) if quiet else print
    rng = np.random.default_rng(seed)
    outline = load_outline()
    town_w = np.array([t[4] for t in TOWNS], float)
    national = town_w / town_w.sum()
    hist_national = town_w ** 0.7 / (town_w ** 0.7).sum()
    scottish_town = np.array([t[5] for t in TOWNS], bool)
    off_land = [t[0] for t in TOWNS if not shapely.contains_xy(outline, t[2], t[3])]
    if off_land:
        say("note: these fake town centres fall in the sea, their people are moved inland:", off_land)

    # places
    addresses = Pool(rng, outline, TOWNS, max(int(persons * 0.7), 40 * len(TOWNS)), national, 40)
    parishes = Pool(rng, outline, TOWNS, 2000, hist_national, 10)

    # surnames
    names, keys = make_surnames(rng, surnames)
    p_surname = np.arange(1, surnames + 1, dtype=float) ** -0.75
    p_surname /= p_surname.sum()
    kind, conc, home = surname_geography(rng, surnames, town_w, TOWNS)

    # people and their addresses over time
    s = rng.choice(surnames, size=persons, p=p_surname)
    entry = np.where(rng.random(persons) < 0.45, 1997, rng.integers(1997, 2027, persons))
    exit_ = np.minimum(entry + rng.geometric(1 / 16, persons) - 1, 2026)
    town = draw_towns(rng, s, conc, home, national)
    current = entry.copy()
    active = np.ones(persons, bool)
    who, where, first_seen, last_seen = [], [], [], []
    while active.any():
        idx = np.flatnonzero(active)
        first = current[idx]
        last = np.minimum(first + rng.geometric(1 / 7, idx.size) - 1, exit_[idx])
        who.append(idx)
        where.append(addresses.pick(rng, town[idx]))
        first_seen.append(first)
        last_seen.append(last)
        overlap = (rng.random(idx.size) < 0.10) & (last > first)     # seen at old and new address in the move year
        following = last + np.where(overlap, 0, 1)
        goes_on = following <= exit_[idx]
        active[idx[~goes_on]] = False
        current[idx[goes_on]] = following[goes_on]
        moved = goes_on & (rng.random(idx.size) < 0.35)
        if moved.any():
            town[idx[moved]] = draw_towns(rng, s[idx[moved]], conc, home, national, strength=0.5)
    who, where = np.concatenate(who), np.concatenate(where)
    first_seen, last_seen = np.concatenate(first_seen), np.concatenate(last_seen)

    female = rng.random(persons) < 0.5
    zipf = 1 / np.arange(1, 41) ** 0.9
    zipf /= zipf.sum()
    fem, mal = np.array(FEMALE), np.array(MALE)
    forename = np.where(female, fem[rng.choice(40, persons, p=zipf)], mal[rng.choice(40, persons, p=zipf)])

    # register rows: surnames written in mixed styles, plus a little junk
    n_rows = who.size
    style = rng.integers(0, 3, n_rows)
    row_name = names[s[who]]
    row_surname = np.where(style == 0, row_name, np.where(style == 1, np.char.upper(row_name), np.char.lower(row_name)))
    postcode = np.array([fake_postcode(i) for i in range(addresses.x.size)])
    rows = list(zip(forename[who].tolist(), row_surname.tolist(), postcode[where].tolist(),
                    first_seen.tolist(), last_seen.tolist()))
    person_eth = make_eth(np.random.default_rng([seed, 7]), s, surnames)      # its own random stream, so nothing above changes
    eth = person_eth[who].tolist()
    n_junk = int(n_rows * 0.003)
    junk_addr = rng.integers(0, addresses.x.size, n_junk)
    junk_first = rng.integers(1997, 2027, n_junk)
    rows += list(zip(rng.choice(mal, n_junk).tolist(), rng.choice(["XXXX", "nan", ""], n_junk).tolist(),
                     postcode[junk_addr].tolist(), junk_first.tolist(),
                     np.minimum(junk_first + rng.integers(0, 6, n_junk), 2026).tolist()))
    rows = [row + (e,) for row, e in zip(rows, eth + [None] * n_junk)]
    no_xy = rng.random(addresses.x.size) < 0.01            # in the lookup, but without a grid reference
    absent = rng.random(addresses.x.size) < 0.005          # not in the lookup at all
    town_name = np.array([t[0] for t in TOWNS])[addresses.town]
    country = np.where(scottish_town[addresses.town], "S92000003",
                       np.where(np.isin(town_name, WELSH), "W92000004", "E92000001"))
    country[rng.random(addresses.x.size) < 0.005] = "N92000002"      # Northern Ireland: to be filtered out
    areas = make_areas(np.random.default_rng([seed, 5]), addresses.town, country)
    address_rows = [(postcode[i], (0.0 if i % 2 else None) if no_xy[i] else round(float(addresses.x[i]), 1),
                     (0.0 if i % 2 else None) if no_xy[i] else round(float(addresses.y[i]), 1), country[i],
                     areas["oa"][i], areas["lsoa"][i], areas["lsoa_2011"][i], areas["msoa"][i], areas["district"][i])
                    for i in range(addresses.x.size) if not absent[i]]
    say(f"register: {len(rows):,} rows for {persons:,} people, {len(address_rows):,} postcodes in the lookup")

    # database
    path = Path(path or config.settings("fake")["database"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE register (forename TEXT, surname TEXT, postcode TEXT, first INTEGER, last INTEGER, eth TEXT);
        CREATE TABLE postcode_lookup (postcode TEXT, easting REAL, northing REAL, ctry TEXT,
                                      oa21cd TEXT, lsoa21cd TEXT, lsoa11cd TEXT, msoa21cd TEXT, lad25cd TEXT);
        CREATE TABLE forename_gender (forename TEXT, gender TEXT);
        CREATE TABLE conpar1851 (conparid INTEGER, x REAL, y REAL, parish TEXT, regcnty TEXT);
        CREATE TABLE conpar1901 (conparid INTEGER, x REAL, y REAL, parish TEXT, regcnty TEXT);
    """)
    db.executemany("INSERT INTO register VALUES (?,?,?,?,?,?)", rows)
    db.executemany("INSERT INTO postcode_lookup VALUES (?,?,?,?,?,?,?,?,?)", address_rows)
    nbhd = make_nbhd_tables(np.random.default_rng([seed, 6]), areas)
    for key, table_rows in nbhd.items():
        columns = config.NBHD_TABLE_COLUMNS[key]
        db.execute(f"CREATE TABLE nbhd_{key} (" + ", ".join(
            f"{name} {kind}" + (" PRIMARY KEY" if name == "area_code" else "") for name, kind in columns) + ")")
        db.executemany(f"INSERT INTO nbhd_{key} VALUES ({','.join('?' * len(columns))})", table_rows)
    db.executemany("INSERT INTO forename_gender VALUES (?,?)",
                   [(n, "F") for n in FEMALE] + [(n, "M") for n in MALE])
    county = [TOWNS[t][1] for t in parishes.town]
    for boundaries, offset in ((1851, 0), (1901, 5000)):      # different numbering on purpose
        db.executemany(f"INSERT INTO conpar{boundaries} VALUES (?,?,?,?,?)",
                       [(offset + i + 1, round(float(parishes.x[i]), 1), round(float(parishes.y[i]), 1),
                         f"Parish {i + 1:04d}", county[i]) for i in range(parishes.x.size)])

    # censuses
    for year in config.CENSUS_YEARS:
        n = int(persons * CENSUS_SIZE[year])
        cs = rng.choice(surnames, size=n, p=p_surname)
        ctown = draw_towns(rng, cs, np.where(kind == "widespread", 0.0, np.minimum(conc + 0.15, 0.97)),
                           home, hist_national)
        if year in config.SCOTLAND_MISSING_YEARS:              # no Scotland in 1911 or 1921
            keep = ~scottish_town[ctown]
            cs, ctown = cs[keep], ctown[keep]
            n = cs.size
        parish = parishes.pick(rng, ctown)
        gid = parish + 1 + (5000 if config.CENSUS_PARISH_BOUNDARIES[year] == 1901 else 0)
        gid[rng.random(n) < 0.005] = 0                         # a few people without a parish
        cfem = rng.random(n) < 0.5
        cname = np.where(cfem, fem[rng.choice(40, n, p=zipf)], mal[rng.choice(40, n, p=zipf)])
        db.execute(f"CREATE TABLE gb{year} (recid INTEGER, source TEXT, sname_clean_stand TEXT, pname TEXT)")
        db.execute(f"CREATE TABLE gb{year}_att (recid INTEGER, source TEXT, gid INTEGER, sex TEXT)")
        recid = np.arange(1, n + 1).tolist()
        db.executemany(f"INSERT INTO gb{year} VALUES (?,?,?,?)",
                       zip(recid, ["c"] * n, keys[cs].tolist(), cname.tolist()))
        db.executemany(f"INSERT INTO gb{year}_att VALUES (?,?,?,?)",
                       zip(recid, ["c"] * n, gid.tolist(), np.where(cfem, "F", "M").tolist()))
        db.execute(f"CREATE INDEX ix_att{year} ON gb{year}_att (recid, source)")
        say(f"census {year}: {n:,} people")
    db.executescript("""
        CREATE INDEX ix_register_postcode ON register (postcode);
        CREATE INDEX ix_lookup_postcode ON postcode_lookup (postcode);
        CREATE INDEX ix_conpar1851 ON conpar1851 (conparid);
        CREATE INDEX ix_conpar1901 ON conpar1901 (conparid);
    """)
    db.commit()
    db.close()

    truth = {k: {"rank": int(r), "kind": kind[r], "name": str(names[r]),
                 "home": sorted({TOWNS[h][0] for h in home[r]}) if kind[r] != "widespread" else []}
             for r, k in enumerate(keys)}
    path.with_name("fake_truth.json").write_text(json.dumps(truth))
    say(f"wrote {path} ({path.stat().st_size / 1e6:.0f} MB) in {time.time() - started:.0f} s")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--persons", type=int, default=250000)
    parser.add_argument("--surnames", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", help="where to write the database (default: the path in config.py)")
    args = parser.parse_args()
    generate(args.persons, args.surnames, args.seed, args.out)
