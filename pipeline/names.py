"""How a surname is turned into the key that names its file (smith.json) and its search entry.

The same rule has to be used by the pipeline (here) and by the website's search box
(site/js/data.js, to be written), otherwise a visitor could type a name that exists but is
looked up under a different key.

The rule: remove accents, lower case, keep the letters a to z only.
    "O'Brien" -> "obrien"    "Smith-Jones" -> "smithjones"    "Müller" -> "muller"
"""
import hashlib
import re
import unicodedata

# Junk values that appear in the registers instead of a surname
PLACEHOLDERS = {"", "xxxx", "nan", "null", "none", "unknown"}

_NOT_A_TO_Z = re.compile(r"[^a-z]+")
_PUNCTUATION_OR_DIGITS = re.compile(r"[^\w\s]|[\d_]")


def surname_key(raw):
    """The key for a raw surname, or "" when the value is empty or a placeholder."""
    if raw is None:
        return ""
    text = unicodedata.normalize("NFKD", str(raw))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    key = _NOT_A_TO_Z.sub("", text.lower())
    return "" if key in PLACEHOLDERS else key


def chunk_of(key, chunks):
    """Which of `chunks` map-building chunks an (already standardised) surname key belongs to -
    a pure function of the key and the chunk count, stable across runs, processes and machines
    (unlike Python's own str hash(), randomised per process), so stage 3 (point extracts) and
    stage 4 (map building) always agree on where a name's data lives without a shared manifest
    file, and re-running stage 3 with more names added does not reshuffle any existing one."""
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % chunks


def name_key(text):
    """A county or parish name as a grouping key: lower case, single spaces - so that ABERDEEN and Aberdeen, or a
    double space, never split one place into two."""
    return " ".join(str(text or "").lower().split())


_SMALL_WORDS = {"and", "of", "on", "upon", "in", "the", "with", "by", "near", "next", "le", "de", "la"}
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


def place_name(raw):
    """A county or parish name as it is shown on a page. Spaces are tidied. A name in ALL CAPITALS (the Scottish
    counties in the 1901 parish table: ABERDEEN, ROSS AND CROMARTY) becomes ordinary capitals: Aberdeen, Ross and
    Cromarty, St Mary's, O'Neil. Any other name is left exactly as it is: str.title() would turn "Middlesex (exclusive
    of London Districts)" into "(Exclusive Of London Districts)" and "St Mary's" into "St Mary'S"."""
    text = " ".join(str(raw or "").split())
    if not text or text != text.upper():
        return text
    first = next(_WORD.finditer(text), None)

    def fix(match):
        word = match.group(0)
        if "'" in word:
            head, tail = word.split("'", 1)
            return head.capitalize() + "'" + (tail.capitalize() if len(head) == 1 else tail.lower())
        if word.lower() in _SMALL_WORDS and match.start() != first.start():
            return word.lower()
        return word.capitalize()

    return _WORD.sub(fix, text)


def has_letters(text):
    """False for "", "-" and other names that are only a placeholder."""
    return any(ch.isalpha() for ch in str(text or ""))


def place_label(county, parish, unnamed=()):
    """(county, parish) as a place is shown in a list, or None if there is no name to show. A parish with a real name is
    shown under it (place_name tidies the capitals). A parish whose name is only a placeholder ("-") is shown under the
    name that `unnamed` gives its county - a list of (county pattern, county to show, parish to show), the pattern
    matched against name_key(county) - or, when no pattern fits, left out (None)."""
    if has_letters(parish):
        return place_name(county), place_name(parish)
    key = name_key(county)
    for pattern, county_label, parish_label in unnamed:
        if re.match(pattern, key):
            return county_label, parish_label
    return None


def forename_clean(raw):
    """A forename as listed on a name's page: lower case, punctuation and digits removed (so "Anne-Marie"
    becomes "annemarie"), accents kept, and at least two characters - "" when nothing usable is left.
    The same rule as the old pipeline's, which dropped initials and junk in the same way."""
    if raw is None:
        return ""
    text = " ".join(_PUNCTUATION_OR_DIGITS.sub("", str(raw).lower()).split())
    return text if len(text) >= 2 else ""
