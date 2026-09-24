"""Where the pipeline writes things that you look at, so that a new run never overwrites an old one."""
import re
from pathlib import Path


def next_number(folder, stem, suffix):
    """One more than the highest N among folder/<stem>N<suffix> (1 if there are none yet). Creates the folder.
    So the first run writes preview1.html, the next preview2.html, and a file you moved or renamed does not matter."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"{re.escape(stem)}(\d+){re.escape(suffix)}")
    return 1 + max((int(m.group(1)) for p in folder.iterdir() if (m := pattern.fullmatch(p.name))), default=0)
