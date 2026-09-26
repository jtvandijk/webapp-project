#!/bin/bash
# Stage 4: build every name's map, as an SGE array job.
#
# Run stage 2 (population surfaces) and stage 3 (point extracts) first - this script only reads
# what they already wrote to disk (work/surfaces/, work/chunks/). It makes NO database queries and
# needs no PG*/GBNAMES_PROFILE environment at all - that is the whole point of splitting the work
# this way: the database is only ever touched once per period (stage 2, stage 3), never once per
# name, and stage 4 can run as a large array job without a database connection per task.
#
#   qsub -t 1-<GBNAMES_CHUNKS> pipeline/hpc/stage4.sh        e.g.  qsub -t 1-200 pipeline/hpc/stage4.sh
#
# SGE array tasks are 1-indexed; task N processes chunk N-1 (stage 3's chunks are 0-indexed).
# The number of chunks (GBNAMES_CHUNKS in run.settings) is the same one stage 3 used, and the -t range above must be
# 1-that number. The script stops at once if the -t range ends anywhere else (a shorter range would quietly leave the
# last chunks unbuilt), and s4_maps.py checks the number against work/chunks/CHUNKS and refuses to run if they
# disagree, rather than silently reading the wrong names for a chunk.
#
# GBNAMES_SOURCES (run.settings) must be the same one stages 2 and 3 were run with - or this looks for a
# source's surfaces/chunks that do not exist yet and fails.
#
# h_vmem and h_rt below come from the real full run (43,093 names, 200 chunks of about 216 names, both sources): the slowest
# task took about 700 s and none used more than about 230 MB, so 30 minutes and 1G leave a wide margin. For a very
# different size of run, size them again from a sample: run stage 3 with a limit and a chunk number that gives a sample
# chunk about as many names as a full-run chunk will (a sample split into many small chunks times fast, which is a
# misleadingly small number to plan the real run's -l h_rt from), time a few chunks, then set h_rt generously above the
# slowest one - not exactly equal to it, since a real chunk varies. To change it for one run only:
#   qsub -l h_rt=02:00:00 -t 1-200 pipeline/hpc/stage4.sh
#
# No .env/GBNAMES_PROFILE needed here, unlike stage2.sh/stage3.sh - this stage makes no database
# queries at all, only reads what they already wrote to work/surfaces/ and work/chunks/. It still
# needs the gbnames conda/venv environment activated below, same as the other two - that is about
# the Python packages (numpy, scipy, shapely, ...), a separate thing from database credentials.
#
# One-off setup, before the FIRST qsub of any of the stage scripts:  mkdir -p work/logs
# (see stage2.sh's comment on why this has to happen before qsub, not inside the script).

#$ -N gbnames_stage4
#$ -j y
#$ -o work/logs/
#$ -l h_vmem=1G
#$ -l h_rt=00:30:00
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
    echo "The array range ends at $SGE_TASK_LAST but GBNAMES_CHUNKS in run.settings is $GBNAMES_CHUNKS. Submit with: qsub -t 1-$GBNAMES_CHUNKS pipeline/hpc/stage4.sh" >&2
    exit 1
fi
# --- end array guard

# SGE sets SGE_TASK_ID for an array job (qsub -t ...) and, outside one, to the word "undefined" (unset if the script is
# run by hand). Both of those mean chunk 0, so a plain "qsub pipeline/hpc/stage4.sh" with no -t runs as a quick
# single-chunk trial rather than hitting "unbound variable" under set -u.
# --- task id
TASK_ID="${SGE_TASK_ID:-undefined}"
if [ "$TASK_ID" = "undefined" ]; then TASK_ID=1; fi
CHUNK=$((TASK_ID - 1))
# --- end task id

python3 -m pipeline.s4_maps --chunk "$CHUNK"
