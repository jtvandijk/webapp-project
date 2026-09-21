"""How a surname is turned into the key that names its file (smith.json) and its search entry.

The same rule has to be used by the pipeline (here) and by the website's search box
(site/js/data.js, to be written), otherwise a visitor could type a name that exists but is
looked up under a different key.

The rule: remove accents, lower case, keep the letters a to z only.
    "O'Brien" -> "obrien"    "Smith-Jones" -> "smithjones"    "Müller" -> "muller"
"""
import re
import unicodedata

# Junk values that appear in the registers instead of a surname
PLACEHOLDERS = {"", "xxxx", "nan", "null", "none", "unknown"}

_NOT_A_TO_Z = re.compile(r"[^a-z]+")


def surname_key(raw):
    """The key for a raw surname, or "" when the value is empty or a placeholder."""
    if raw is None:
        return ""
    text = unicodedata.normalize("NFKD", str(raw))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    key = _NOT_A_TO_Z.sub("", text.lower())
    return "" if key in PLACEHOLDERS else key
