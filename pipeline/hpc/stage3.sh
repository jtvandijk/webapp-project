#!/bin/bash
# Stage 3: point extracts - one job, not an array (unlike stage 4). Also touches the database, so
# also goes through qsub, not the login node - see stage2.sh's comment; the query being cheap does
# not change where it should run, only how big a job to ask for.
#
#   qsub pipeline/hpc/stage3.sh
#
# LIMIT/CHUNKS below are for a SAMPLE run - remove --limit (or set LIMIT="") and set CHUNKS to the
# real value (e.g. 200) once you are ready for the full name list. Keep the names-per-chunk ratio
# similar between a sample and the real run (see pipeline/README.md's "Stage 4" section) so the
# sample's timings mean something for sizing stage 4's own job.
#
# SOURCES is register-only for now - see stage2.sh's comment on adding census later. Note: running
# this against work/names.csv from a register-only s1_counts.py run means that list is not yet the
# final one (a name that only clears the threshold via historic census bearers would be missing) -
# fine for a sample/rehearsal run, but re-run s1_counts.py with both sources once census is ready,
# before treating a full (non-sample) run of this stage as final.

#$ -N gbnames_stage3
#$ -j y
#$ -o work/logs/
#$ -l h_vmem=2G
#$ -l h_rt=00:30:00
#$ -cwd

set -euo pipefail

SOURCES="register"
LIMIT="500"     # e.g. "500" for a sample run, or "" for the full name list
CHUNKS=4        # match this to the real run's --chunks when doing a full run, not a sample's

mkdir -p work/logs
python3 -m pipeline.s3_extracts --sources $SOURCES --chunks "$CHUNKS" ${LIMIT:+--limit "$LIMIT"}
