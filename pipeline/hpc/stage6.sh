#!/bin/bash
# Stage 6: assemble every name's release file, as an SGE array job (the same shape as stage 4).
#
# Run stage 4 (maps) and stage 5 (facts) first, then, once, directly (not through qsub - it is cheap,
# one read of facts.csv/counts.csv and N small writes, the same kind of job as check_parishes.py or
# merge_stats.py):
#
#   python3 -m pipeline.s6_assemble --prepare
#
# Only then submit the array job:
#
#   qsub -t 1-<GBNAMES_CHUNKS> pipeline/hpc/stage6.sh        e.g.  qsub -t 1-200 pipeline/hpc/stage6.sh
#
# This makes NO database queries and needs no PG*/GBNAMES_PROFILE environment at all - like stage 4, it
# only reads what earlier stages already wrote to disk (work/maps/, and --prepare's own
# work/facts/chunks/, work/counts/chunks/).
#
# SGE array tasks are 1-indexed; task N processes chunk N-1 (the same convention as stage 4). The
# number of chunks (GBNAMES_CHUNKS in run.settings) must be the same one stage 3/4 and --prepare used,
# and the -t range above must be 1-that number - the array guard below stops at once otherwise, and
# s6_assemble.py itself refuses to run a chunk against a --prepare split made for a different number.
#
# Once every chunk is done: python3 -m pipeline.merge_release
#
# h_vmem and h_rt below are an initial guess, not yet measured: this stage does no KDE computation at
# all (no shapely/pyproj), only JSON reshaping, so it should be lighter and faster than stage 4's own
# per-chunk cost, not heavier - time a few chunks first for a very different size of run, the same way
# stage 4's own comment describes.
#
# One-off setup, before the FIRST qsub of any of the stage scripts:  mkdir -p work/logs
# (see stage2.sh's comment on why this has to happen before qsub, not inside the script).

#$ -N gbnames_stage6
#$ -j y
#$ -o work/logs/
#$ -l h_vmem=2G
#$ -l h_rt=01:00:00
#$ -cwd

set -euo pipefail

# ~/.bashrc and conda's own init script are not written to be safe under "set -u" - see stage2.sh's
# comment. Relaxed just around sourcing them, restored straight after.
set +euo pipefail
source ~/.bashrc
conda activate gbnames
set -euo pipefail

set -a
source run.settings          # no .env: this stage makes no database queries
set +a
export PYTHONUNBUFFERED=1    # print to the log as it happens; otherwise the log can look empty until the job ends

# --- array guard: the -t range must end at GBNAMES_CHUNKS (SGE sets SGE_TASK_LAST to "undefined" outside an array job)
if [ -n "${SGE_TASK_LAST:-}" ] && [ "$SGE_TASK_LAST" != "undefined" ] && [ "$SGE_TASK_LAST" != "$GBNAMES_CHUNKS" ]; then
    echo "The array range ends at $SGE_TASK_LAST but GBNAMES_CHUNKS in run.settings is $GBNAMES_CHUNKS. Submit with: qsub -t 1-$GBNAMES_CHUNKS pipeline/hpc/stage6.sh" >&2
    exit 1
fi
# --- end array guard

# SGE only sets SGE_TASK_ID for an array job (qsub -t ...) - defaults to 1 (chunk 0) so a plain
# "qsub pipeline/hpc/stage6.sh" with no -t still runs, as a quick single-chunk sanity check, rather
# than hitting "unbound variable" under set -u.
CHUNK=$((${SGE_TASK_ID:-1} - 1))

python3 -m pipeline.s6_assemble --chunk "$CHUNK"
