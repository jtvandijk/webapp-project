#!/bin/bash
# Deletes stage 3 + stage 4 output for a clean start (e.g. before switching --chunks/--limit) - a
# plain bash script, not a qsub job (deleting files needs no compute node): run directly, from
# anywhere:
#
#   bash pipeline/hpc/clean.sh              # stage 3 + 4 only, asks about stage 1 + 2 too
#   bash pipeline/hpc/clean.sh --stage34    # stage 3 + 4 only, does not ask about stage 1 + 2
#   bash pipeline/hpc/clean.sh --all        # stage 1 + 2 + 3 + 4, no question asked
#   bash pipeline/hpc/clean.sh --facts      # stage 5 only (work/facts: the saved queries and the facts)
#   bash pipeline/hpc/clean.sh --release    # stage 6 only (work/release, and its per-chunk slices of counts and facts)
#
# Real incident this exists to help avoid (2026-09-23): a partial manual cleanup between two runs
# emptied work/stats/ but left work/maps/'s .done/.jsonl files behind from an earlier, differently
# sized run - the next run's --chunks did not match those old .done markers' partitioning, and
# (before s4_maps.py was fixed to catch this itself) that silently kept stale output computed under
# the wrong partitioning for those chunks. s4_maps.py no longer trusts a mismatched .done marker on
# its own, but starting from a genuinely empty state before a real resize is still the simplest way
# to avoid relying on that safety net at all.
#
# Stage 1 (work/counts.csv, work/names.csv) and stage 2 (work/surfaces/) both come from real
# database queries, not just recomputation from local files - wiping them is a separate, more
# deliberate decision than clearing stage 3/4's derived output, so by default this ASKS rather than
# doing it silently (pass --all or --stage34 to skip the question either way).
#
# Leaves work/logs/ alone regardless - SGE job output, shared across stages 2/3/4, you said you
# manage this yourself already.

set -euo pipefail
cd "$(dirname "$0")/../.."      # repo root, wherever this script is actually run from
WORK="work"

ask_stage12=1
clean_stage12=0
only_facts=0
only_release=0
for arg in "$@"; do
    case "$arg" in
        --all)     clean_stage12=1; ask_stage12=0 ;;
        --stage34) clean_stage12=0; ask_stage12=0 ;;
        --facts)   only_facts=1 ;;
        --release) only_release=1 ;;
        *) echo "Unknown option: $arg (expected --all, --stage34, --facts or --release)"; exit 1 ;;
    esac
done

show_sizes() {
    for path in "$@"; do
        if [ -e "$path" ]; then
            du -sh "$path"
        else
            printf '0\t%s (not present)\n' "$path"
        fi
    done
}

if [ "$only_facts" -eq 1 ]; then
    # Stage 5 trusts a saved query while the NAMES it was made for are unchanged; it cannot notice that
    # the database, or a neighbourhood table, has changed since (s5_facts.py --refresh does the same job).
    echo "Stage 5 output under $WORK/ (saved queries in facts/extract, and the facts):"
    show_sizes "$WORK/facts"
    read -r -p "Delete the above? [y/N] " reply
    if [[ "$reply" =~ ^[Yy] ]]; then
        rm -rf "$WORK/facts"
        echo "Deleted: $WORK/facts"
    else
        echo "Left in place."
    fi
    exit 0
fi

if [ "$only_release" -eq 1 ]; then
    # Stage 6 only reads stage 4's maps and stage 5's facts (and stage 1's counts); it never changes them, so this
    # is safe at any time and they stay. The two chunks folders are stage 6's own slices of counts.csv and facts.csv
    # (not the files they were cut from). s6_assemble.py --force redoes finished chunks without deleting anything.
    echo "Stage 6 output under $WORK/ (the assembled name files, the facts table, the slices):"
    show_sizes "$WORK/release" "$WORK/facts/chunks" "$WORK/counts/chunks"
    read -r -p "Delete the above? [y/N] " reply
    if [[ "$reply" =~ ^[Yy] ]]; then
        rm -rf "$WORK/release" "$WORK/facts/chunks" "$WORK/counts/chunks"
        rmdir "$WORK/counts" 2>/dev/null || true       # only if now empty
        echo "Deleted: $WORK/release, $WORK/facts/chunks, $WORK/counts/chunks"
    else
        echo "Left in place."
    fi
    exit 0
fi

echo "Stage 3 + stage 4 output under $WORK/:"
show_sizes "$WORK/chunks" "$WORK/maps" "$WORK/stats" "$WORK/stats.csv"
read -r -p "Delete the above? [y/N] " reply
if [[ "$reply" =~ ^[Yy] ]]; then
    rm -rf "$WORK/chunks" "$WORK/maps" "$WORK/stats" "$WORK/stats.csv"
    echo "Deleted: $WORK/chunks, $WORK/maps, $WORK/stats, $WORK/stats.csv"
else
    echo "Left in place - stopping here, not asking about stage 1 + 2 either."
    exit 0
fi

if [ "$ask_stage12" -eq 1 ]; then
    echo
    echo "Stage 1 + stage 2 output (from real database queries, not just derived files):"
    show_sizes "$WORK/counts.csv" "$WORK/names.csv" "$WORK/surfaces"
    read -r -p "Also delete this? [y/N] " reply
    [[ "$reply" =~ ^[Yy] ]] && clean_stage12=1
fi

if [ "$clean_stage12" -eq 1 ]; then
    rm -rf "$WORK/counts.csv" "$WORK/names.csv" "$WORK/surfaces"
    echo "Deleted: $WORK/counts.csv, $WORK/names.csv, $WORK/surfaces"
else
    echo "Left stage 1 + stage 2 output in place."
fi
