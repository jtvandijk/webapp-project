#!/usr/bin/env bash
# Makes the column sname_clean_stand in the census tables that lack it (census.gb1851 ... census.gb1921), by running
# census_sname_clean_stand.sql once for each year. A year that already has the column is skipped, so it is safe to run
# again after a stop. It connects with the census settings of .env (PGHOST_ICEM, PGDATABASE_ICEM, PGUSER_ICEM,
# PGPASSWORD_ICEM, and PGPORT_ICEM if there is one), and needs psql.
#
#   set -a; source .env; set +a                              # the database settings
#   bash tools/sql/make_sname_clean_stand.sh --list          # which years have the column and which do not; changes nothing
#   bash tools/sql/make_sname_clean_stand.sh 1921            # one year (or several: 1921 1911)
#   bash tools/sql/make_sname_clean_stand.sh                 # every census year that lacks the column, one after the other
#
# Each year is one transaction: if it stops (an error, or you press Ctrl-C) that year is left exactly as it was. The
# script prints what the cleaning changed for each year: read it. Afterwards each table is vacuumed.
set -eu

ALL_YEARS="1851 1861 1881 1891 1901 1911 1921"
here="$(cd "$(dirname "$0")" && pwd)"
template="$here/census_sname_clean_stand.sql"

list_only=0
years=""
for arg in "$@"; do
    case "$arg" in
        --list) list_only=1 ;;
        [0-9][0-9][0-9][0-9])
            case " $ALL_YEARS " in
                *" $arg "*) years="$years $arg" ;;
                *) echo "$arg is not a census year we have ($ALL_YEARS)"; exit 1 ;;
            esac ;;
        *) echo "usage: bash make_sname_clean_stand.sh [--list] [year ...]"; exit 1 ;;
    esac
done
[ -n "$years" ] || years="$ALL_YEARS"

: "${PGHOST_ICEM:?PGHOST_ICEM is not set: run   set -a; source .env; set +a   first}"
: "${PGDATABASE_ICEM:?PGDATABASE_ICEM is not set: run   set -a; source .env; set +a   first}"
: "${PGUSER_ICEM:?PGUSER_ICEM is not set: run   set -a; source .env; set +a   first}"
export PGHOST="$PGHOST_ICEM" PGDATABASE="$PGDATABASE_ICEM" PGUSER="$PGUSER_ICEM"
if [ -n "${PGPORT_ICEM:-}" ]; then export PGPORT="$PGPORT_ICEM"; fi
if [ -n "${PGPASSWORD_ICEM:-}" ]; then export PGPASSWORD="$PGPASSWORD_ICEM"; fi

psql -X -At -c "SELECT 1" > /dev/null || { echo "cannot connect to the census database (psql said the above)"; exit 1; }

ask() { psql -X -At -v ON_ERROR_STOP=1 -c "$1"; }
has_table()  { [ "$(ask "SELECT to_regclass('census.gb$1') IS NOT NULL")" = "t" ]; }
has_column() { [ "$(ask "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'census' AND table_name = 'gb$1' AND column_name = 'sname_clean_stand'")" = "1" ]; }

for year in $years; do
    if ! has_table "$year"; then
        echo "$year: census.gb$year does not exist - skipped"
    elif has_column "$year"; then
        echo "$year: has sname_clean_stand"
    elif [ "$list_only" = 1 ]; then
        echo "$year: lacks sname_clean_stand"
    else
        echo "$year: making sname_clean_stand, started $(date +%H:%M) ..."
        sed "s/1921/$year/g" "$template" | PGOPTIONS="-c client_min_messages=warning" psql -X -q -1 -v ON_ERROR_STOP=1 -f -
        psql -X -q -v ON_ERROR_STOP=1 -c "VACUUM ANALYZE census.gb$year"
        echo "$year: done, $(date +%H:%M)"
    fi
done
