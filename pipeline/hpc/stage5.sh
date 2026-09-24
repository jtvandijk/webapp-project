#!/bin/bash
# Stage 5: the facts about each name - one job, not an array (unlike stage 4).
#
# It is a few dozen database queries, each answered by the database, plus light Python to fold what
# comes back and work out the facts, so there is nothing to spread over many machines. It touches the
# database, so it goes through qsub and not the login node - the same reasoning as stages 2 and 3
# (see stage2.sh's comment).
#
#   qsub pipeline/hpc/stage5.sh
#
# Which names, sources and facts it works out comes from run.settings: GBNAMES_LIMIT is for a SAMPLE run (the first N
# names of work/names.csv, the same N as a stage 3 sample uses; empty = every name), GBNAMES_FACTS is empty for every
# fact of the chosen sources or a list such as "oac imd" (say, after loading a new table, or to redo one that failed),
# and GBNAMES_SOURCES is register-only for now, since the census database is not ready: the historic facts
# (forenames, parishes) need it.
#
# Before this: stage 1 (work/counts.csv and work/names.csv), and the neighbourhood tables loaded in
# the TRE - check them first with  python3 -m pipeline.nbhd_tables check
#
# The memory and time below: 5,000 names took about 20 minutes, most of it the ethnicity query (its table has no
# index on the surname, so each query scans it). The full name list is not measured yet:
#  * memory: the biggest thing held is the neighbourhood query for the newest year, one row per name
#    and neighbourhood, which on the full name list may be millions of rows. 16G is generous for a
#    sample; the run prints how many rows each query returned, so scale from that for the full run.
#  * time: every query scans the register, so it depends on the database, not on this node. The run prints how long
#    each took, and its total at the end. For the full list ask for more for that one run, without editing this file:
#      qsub -l h_rt=03:00:00 pipeline/hpc/stage5.sh
# A finished query is saved under work/facts/extract/ and reused, so if the job is killed (too little
# memory or time), submitting it again carries on where it stopped instead of starting over.
#
# Expects .env (database settings) and run.settings (run choices) in the project root - see stage2.sh's comment.
#
# One-off setup, before the FIRST qsub of any of the stage scripts:  mkdir -p work/logs
# (see stage2.sh's comment on why this has to happen before qsub, not inside the script).
#
# Activates the gbnames conda environment explicitly (via ~/.bashrc, since a non-interactive qsub
# shell does not source it automatically) - see stage2.sh's comment for why.

#$ -N gbnames_stage5
#$ -j y
#$ -o work/logs/
#$ -l h_vmem=16G
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
source .env
source run.settings
set +a
export GBNAMES_PROFILE=tre
export PYTHONUNBUFFERED=1    # print to the log as it happens; otherwise the log can look empty until the job ends

python3 -m pipeline.s5_facts
