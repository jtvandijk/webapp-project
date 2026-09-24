#!/bin/bash
# Stage 3: point extracts - one job, not an array (unlike stage 4). Also touches the database, so
# also goes through qsub, not the login node - see stage2.sh's comment; the query being cheap does
# not change where it should run, only how big a job to ask for.
#
#   qsub pipeline/hpc/stage3.sh
#
# GBNAMES_LIMIT and GBNAMES_CHUNKS in run.settings say how many names and how many chunks: a SAMPLE run sets a limit
# (empty = every name). Keep the names-per-chunk ratio similar between a sample and the real run (see
# pipeline/README.md's "Stage 4" section) so the sample's timings mean something for sizing stage 4's own job.
#
# GBNAMES_SOURCES is register-only for now - see stage2.sh's comment on adding census later. Note: running
# this against work/names.csv from a register-only s1_counts.py run means that list is not yet the
# final one (a name that only clears the threshold via historic census bearers would be missing) -
# fine for a sample/rehearsal run, but re-run stage 1 with both sources once census is ready,
# before treating a full (non-sample) run of this stage as final.
#
# The chunk number MUST be the one stage 4 uses (run.settings has one number for both) - s3_extracts.py writes
# work/chunks/CHUNKS with the number used, and s4_maps.py refuses to run if its own --chunks does
# not match it, rather than silently reading the wrong names for a chunk.
#
# Expects .env and run.settings in the project root - see stage2.sh's comment.
#
# One-off setup, before the FIRST qsub of any of the stage scripts:  mkdir -p work/logs
# (see stage2.sh's comment on why this has to happen before qsub, not inside the script).
#
# Activates the gbnames conda environment explicitly (via ~/.bashrc, since a non-interactive qsub
# shell does not source it automatically, and conda's own init block lives there) - see stage2.sh's
# comment for why.

#$ -N gbnames_stage3
#$ -j y
#$ -o work/logs/
#$ -l h_vmem=2G
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
source .env
source run.settings
set +a
export GBNAMES_PROFILE=tre
export PYTHONUNBUFFERED=1    # print to the log as it happens; otherwise the log can look empty until the job ends

python3 -m pipeline.s3_extracts
