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
# LIMIT below is for a SAMPLE run: the first N names of work/names.csv, the same N as a stage 3
# sample uses. Set it to "" for the full name list. FACTS is empty for every fact, or a list such as
# "oac imd" (say, after loading a new table, or to redo one that failed).
#
# Before this: stage 1 (work/counts.csv and work/names.csv), and the neighbourhood tables loaded in
# the TRE - check them first with  python3 -m pipeline.nbhd_tables check
#
# The memory and time below are GUESSES, not measured:
#  * memory: the biggest thing held is the neighbourhood query for the newest year, one row per name
#    and neighbourhood, which on the full name list may be millions of rows. 16G is generous for a
#    sample; the run prints how many rows each query returned, so scale from that for the full run.
#  * time: every query scans the register, so it depends on the database, not on this node.
#    The run prints how long each took.
# A finished query is saved under work/facts/extract/ and reused, so if the job is killed (too little
# memory or time), submitting it again carries on where it stopped instead of starting over.
#
# Expects a .env file in the project root with PGHOST_LCR etc - see stage2.sh's comment.
#
# One-off setup, before the FIRST qsub of any of these scripts:  mkdir -p work/logs
# (see stage2.sh's comment on why this has to happen before qsub, not inside the script).
#
# Activates the gbnames conda environment explicitly (via ~/.bashrc, since a non-interactive qsub
# shell does not source it automatically) - see stage2.sh's comment for why.

#$ -N gbnames_stage5
#$ -j y
#$ -o work/logs/
#$ -l h_vmem=16G
#$ -l h_rt=04:00:00
#$ -cwd

set -euo pipefail

# ~/.bashrc and conda's own init script are not written to be safe under "set -u" - see stage2.sh's
# comment. Relaxed just around sourcing them, restored straight after.
set +euo pipefail
source ~/.bashrc
conda activate gbnames
set -euo pipefail

LIMIT="5000"    # e.g. "5000" for a sample run, or "" for the full name list
FACTS=""        # "" for every fact, or e.g. "oac imd"

set -a
source .env
set +a
export GBNAMES_PROFILE=tre

python3 -m pipeline.s5_facts ${LIMIT:+--limit "$LIMIT"} ${FACTS:+--facts $FACTS}
