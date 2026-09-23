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


def forename_clean(raw):
    """A forename as listed on a name's page: lower case, punctuation and digits removed (so "Anne-Marie"
    becomes "annemarie"), accents kept, and at least two characters - "" when nothing usable is left.
    The same rule as the old pipeline's, which dropped initials and junk in the same way."""
    if raw is None:
        return ""
    text = " ".join(_PUNCTUATION_OR_DIGITS.sub("", str(raw).lower()).split())
    return text if len(text) >= 2 else ""
