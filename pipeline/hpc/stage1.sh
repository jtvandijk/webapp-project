#!/bin/bash
# Stage 1: count the bearers of every surname in every year, and make the name list (work/counts.csv, work/names.csv).
#
#   qsub pipeline/hpc/stage1.sh
#
# One job, not an array. It touches the database, so it goes through qsub and not the login node (see stage2.sh's
# comment). Which databases it counts comes from run.settings (GBNAMES_SOURCES). It prints how many register rows find
# their postcode in the lookup, and stops if that is clearly wrong.
#
# The memory and time below are GUESSES, not measured: it brings back one row per surname and year, which may be
# millions of rows. After the first run, `qacct -j <jobid>` (or the log) says what it needed; then size them down, since
# the scheduler penalises jobs that ask for much more than they use. One run only for one source: re-run it with both
# sources once the census database is ready, since the list of names depends on both.
#
# Expects .env (database settings) and run.settings (run choices) in the project root - see stage2.sh's comment.
# One-off setup, before the FIRST qsub of any stage script:  mkdir -p work/logs
# Activates the gbnames conda environment explicitly - see stage2.sh's comment for why.

#$ -N gbnames_stage1
#$ -j y
#$ -o work/logs/
#$ -l h_vmem=16G
#$ -l h_rt=02:00:00
#$ -cwd

set -euo pipefail

# ~/.bashrc and conda's own init script are not written to be safe under "set -u" - see stage2.sh's comment.
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

python3 -m pipeline.s1_counts
