#!/bin/bash
# Stage 2: population surfaces - one small job, not an array (unlike stage 4).
#
# This touches the database (one query per period), so it should run on a compute node via qsub,
# not on the login node - the same reasoning as stage 3 and stage 4, and the convention the old
# SGE scripts already used (compute nodes have direct Postgres access; the login node is for
# editing and submitting, not for real work).
#
#   qsub pipeline/hpc/stage2.sh
#
# SOURCES below is register-only for now, since the census database is not ready - this is safe to
# run this way: stage 2 writes one file per period (work/surfaces/<period>.npy), so running it
# again later with SOURCES="census" only adds the census periods' files, it does not touch or
# require redoing the register ones already there.
#
# Expects a .env file in the project root with PGHOST_LCR etc (see pipeline/README.md's "Running
# it in the TRE") - `set -a` below means every variable .env sets is exported automatically, so it
# works whether or not the file itself says "export".
#
# One-off setup, before the FIRST qsub of any of these three scripts:  mkdir -p work/logs
# -o below needs that directory to already exist when SGE sets up output redirection, which
# happens before this script's own body runs - a "mkdir -p work/logs" inside the script itself
# is too late to help, which is why it is not here.
#
# A submitted qsub job starts a fresh, non-interactive shell - it does NOT have your login shell's
# activated conda environment (gbnames), which is why plain "python3" here would not find numpy
# even though it works fine when you run it directly, and bash does not auto-source ~/.bashrc for
# a non-interactive shell either, which is why conda itself was not even on PATH - so ~/.bashrc
# (wherever conda's own init block lives) is sourced explicitly below before activating gbnames.

#$ -N gbnames_stage2
#$ -j y
#$ -o work/logs/
#$ -l h_vmem=2G
#$ -l h_rt=00:30:00
#$ -cwd

set -euo pipefail

# ~/.bashrc and conda's own init script are not written to be safe under "set -u" (they reference
# variables that are normally fine left unset, e.g. $PS1 for an interactive prompt) - relaxed just
# around sourcing them, restored straight after for the rest of this script.
set +euo pipefail
source ~/.bashrc
conda activate gbnames
set -euo pipefail

SOURCES="register"     # "register census" once the census database is ready

set -a
source .env
set +a
export GBNAMES_PROFILE=tre

python3 -m pipeline.s2_surfaces --sources $SOURCES
