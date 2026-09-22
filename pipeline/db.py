"""Connecting to the database and running a query. The only file that knows which database it is.

The TRE has two databases: "register" (also serves ONSPD) and "census". Every call names which one
it wants; there is no default, since silently using the wrong one would be a confusing bug rather
than a clear error. The fake ("sqlite") profile only has one file, so it ignores which one is asked for.

Postgres drivers, tried in this order, whichever is actually installed is used automatically:
  1. psycopg2       needs PostgreSQL's client dev headers and a C compiler where it is installed
  2. psycopg (v3)   the same, or install as  psycopg[binary]  for a self-contained wheel instead
  3. pg8000         pure Python, no system libraries or compiler needed at all, but slower, and it
                    does not read ~/.pgpass (PGPASSWORD is read explicitly below, so that still works)
See pipeline/requirements.txt for the exact commands to try.
"""
import os

from . import config


def connect(group, profile=None):
    """An open connection to one database ("register" or "census") for the chosen profile
    ("fake" = a local SQLite file, ignores `group`; "tre" = Postgres). Only checks the settings this
    group actually needs - connecting to "register" never requires the census settings to be filled
    in, and the other way round."""
    cfg = config.settings(profile)
    if cfg["backend"] == "sqlite":
        import sqlite3
        from pathlib import Path
        if not Path(cfg["database"]).exists():
            raise SystemExit(f"No fake database at {cfg['database']}.\n"
                             "Make one first:  python3 -m pipeline.fake_data")
        return sqlite3.connect(cfg["database"])

    missing = _missing(cfg, group)
    if missing:
        raise SystemExit("These settings in pipeline/config.py still say FILL_IN:\n  " + "\n  ".join(missing))
    return _connect_postgres(cfg["connections"][group], group)


def _missing(cfg, group):
    """Which settings for one group (its connection, and its table/column names) are not filled in."""
    return _unfilled(cfg["connections"][group], f"connections.{group}.") + _unfilled(cfg[group], f"{group}.")


def _connect_postgres(connection, group):
    """Try each Postgres driver in turn, since only one of them may actually be installable."""
    try:
        import psycopg2 as driver          # noqa: same keyword arguments as psycopg (v3), below
        kwargs = dict(connection)
    except ImportError:
        try:
            import psycopg as driver       # psycopg (v3)
            kwargs = dict(connection)
        except ImportError:
            try:
                import pg8000 as driver    # pure Python; uses "database" instead of "dbname"
                kwargs = {**connection, "database": connection["dbname"]}
                del kwargs["dbname"]
            except ImportError:
                raise SystemExit(
                    "No Postgres driver is installed. Try, one at a time, and stop at the first that works:\n"
                    "  pip install psycopg2\n"
                    "  pip install \"psycopg[binary]\"\n"
                    "  pip install pg8000\n"
                    "The first two need PostgreSQL's client headers and a C compiler on this machine "
                    "(check with: pg_config --version); pg8000 is pure Python and needs neither.")

    # <GROUP>_PGPASSWORD overrides PGPASSWORD, for a census database with a different login.
    # Read explicitly rather than left to the driver: pg8000 does not use ~/.pgpass.
    password = os.environ.get(f"{group.upper()}_PGPASSWORD") or os.environ.get("PGPASSWORD")
    if password:
        kwargs["password"] = password
    return driver.connect(**kwargs)


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
        elif value is None:                    # e.g. an unset PGHOST/CENSUS_PGDATABASE/PGUSER
            found.append(f"{path}{key}")
    return found
