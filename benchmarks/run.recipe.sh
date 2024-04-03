#!/bin/sh

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# RECIPE (Converting Concurrent DRAM Indexes to Persistent-Memory Indexes)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
cd /app/benchmarks/RECIPE

dos2unix *.sh
./compile.sh
./run.sh

pycprd ${CPRD_RESULTS_TRACES}/pclht.trace          > ${CPRD_RESULTS_RACES}/pclht.races
# pycprd ${CPRD_RESULTS_TRACES}/pclht-recovery.trace > ${CPRD_RESULTS_RACES}/pclht-recovery.races
