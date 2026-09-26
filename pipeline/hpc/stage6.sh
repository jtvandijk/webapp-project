#!/bin/bash
# Stage 6: assemble every name's release file, as an SGE array job (the same shape as stage 4).
#
# Run stage 4 (maps) and stage 5 (facts) first - a chunk whose stage 4 has not finished (no work/maps/chunk_N.done)
# is refused, so this cannot assemble a half-written maps file. Then, once, directly (not through qsub - it is cheap,
# one streaming read of facts.csv/counts.csv and N small writes, the same kind of job as check_parishes.py or
# merge_stats.py):
#
#   python3 -m pipeline.s6_assemble --prepare
#
# Then a trial of ONE chunk under the real limits (no -t: SGE runs it as a single task, and it does chunk 0):
#
#   qsub pipeline/hpc/stage6.sh                              # then  qacct -j <jobid>  for the real time and memory
#
# and only then the whole array (chunk 0 is already done and is skipped):
#
#   qsub -t 1-<GBNAMES_CHUNKS> pipeline/hpc/stage6.sh        e.g.  qsub -t 1-200 pipeline/hpc/stage6.sh
#
# A part range such as -t 1-3 is refused by the array guard below (it would look like a whole run that quietly left
# the other chunks out); the no-argument trial above is the way to try a few. Any chunk can be redone by itself:
# python3 -m pipeline.s6_assemble --chunk N --force. A finished chunk is also redone, without --force, if stage 4 or
# --prepare has been run again since (its inputs are newer than its .done); to start stage 6 from empty:
# bash pipeline/hpc/clean.sh --release.
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
# all (no shapely/pyproj), only JSON reshaping, one name at a time (memory is one name's maps plus the chunk's own
# small slices of facts and counts), so it should be lighter and faster than stage 4's own per-chunk cost. Read the
# trial's numbers from qacct and set these to about twice what it used. For one run only, without editing this file:
#   qsub -l h_rt=02:00:00 -t 1-200 pipeline/hpc/stage6.sh
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

# SGE sets SGE_TASK_ID for an array job (qsub -t ...) and, outside one, to the word "undefined" (unset if the script is
# run by hand). Both of those mean chunk 0, so a plain "qsub pipeline/hpc/stage6.sh" with no -t runs as a quick
# single-chunk trial rather than hitting "unbound variable" under set -u.
# --- task id
TASK_ID="${SGE_TASK_ID:-undefined}"
if [ "$TASK_ID" = "undefined" ]; then TASK_ID=1; fi
CHUNK=$((TASK_ID - 1))
# --- end task id

python3 -m pipeline.s6_assemble --chunk "$CHUNK"
