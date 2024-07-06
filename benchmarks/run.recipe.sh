#!/bin/sh

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# RECIPE (Converting Concurrent DRAM Indexes to Persistent-Memory Indexes)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
cd /app/benchmarks/RECIPE

dos2unix *.sh
time ./compile.sh
time ./run.sh

echo [*] P-CLHT: Runing pyprd fast
pycprd ${CPRD_RESULTS_TRACES}/pclht.trace --fast > ${CPRD_RESULTS_RACES}/pclht.fast.races
cat ${CPRD_RESULTS_RACES}/pclht.fast.races | head -n 63

echo [*] P-CLHT: Runing pyprd
pycprd ${CPRD_RESULTS_TRACES}/pclht.trace            > ${CPRD_RESULTS_RACES}/pclht.races
cat ${CPRD_RESULTS_RACES}/pclht.races | head -n 63

# pycprd ${CPRD_RESULTS_TRACES}/pclht.trace --mock-pdg > ${CPRD_RESULTS_RACES}/pclht.mockpdg.races
# pycprd ${CPRD_RESULTS_TRACES}/pclht-recovery.trace > ${CPRD_RESULTS_RACES}/pclht-recovery.races
