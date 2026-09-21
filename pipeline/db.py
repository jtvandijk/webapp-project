"""Connecting to the database and running a query. The only file that knows which database it is."""
from . import config


def connect(profile=None):
    """An open connection for the chosen profile ("fake" = a local SQLite file, "tre" = Postgres)."""
    cfg = config.settings(profile)
    if cfg["backend"] == "sqlite":
        import sqlite3
        from pathlib import Path
        if not Path(cfg["database"]).exists():
            raise SystemExit(f"No fake database at {cfg['database']}.\n"
                             "Make one first:  python3 -m pipeline.fake_data")
        return sqlite3.connect(cfg["database"])

    unfilled = _unfilled(cfg)
    if unfilled:
        raise SystemExit("These settings in pipeline/config.py still say FILL_IN:\n  " + "\n  ".join(unfilled))
    try:
        import psycopg2 as driver
    except ImportError:
        import psycopg as driver          # the newer driver has the same connect() call
    return driver.connect(**cfg["connection"])


def fetch(conn, sql):
    """Run a query and return all rows as a list of tuples."""
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        cursor.close()


def _unfilled(cfg, path=""):
    found = []
    for key, value in cfg.items():
        if isinstance(value, dict):
            found += _unfilled(value, f"{path}{key}.")
        elif isinstance(value, str) and "FILL_IN" in value:
            found.append(f"{path}{key}")
    return found
