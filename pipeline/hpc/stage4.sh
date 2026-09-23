#!/bin/bash
# Stage 4: build every name's map, as an SGE array job.
#
# Run stage 2 (population surfaces) and stage 3 (point extracts) first - this script only reads
# what they already wrote to disk (work/surfaces/, work/chunks/). It makes NO database queries and
# needs no PG*/GBNAMES_PROFILE environment at all - that is the whole point of splitting the work
# this way: the database is only ever touched once per period (stage 2, stage 3), never once per
# name, and stage 4 can run as a large array job without a database connection per task.
#
#   qsub -t 1-200 pipeline/hpc/stage4.sh
#
# SGE array tasks are 1-indexed; task N processes chunk N-1 (stage 3's chunks are 0-indexed).
# CHUNKS below must be the same number passed to s3_extracts.py --chunks, and the -t range above
# must match it (1-CHUNKS).
#
# h_vmem and h_rt below are STARTING GUESSES, not measured - size them from a real sample run first
# (see pipeline/README.md's "Stage 4" section): run s3_extracts.py --limit with --chunks picked so
# a sample chunk has roughly as many names as a full-run chunk will (a sample split into too many
# small chunks times fast, which is a misleadingly small number to plan the real run's -l h_rt
# from), time a few chunks by hand, then set h_rt generously above the slowest one - not exactly
# equal to it, since a real chunk's names/geometry will vary.

#$ -N gbnames_stage4
#$ -j y
#$ -o work/logs/
#$ -l h_vmem=2G
#$ -l h_rt=04:00:00
#$ -cwd

set -euo pipefail

CHUNKS=200
CHUNK=$((SGE_TASK_ID - 1))

mkdir -p work/logs
python3 -m pipeline.s4_maps --chunk "$CHUNK" --chunks "$CHUNKS"
