#!/bin/sh

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# FAST-FAIR (Failure-Atomic ShifT(FAST) and Failure-Atomic In-place Rebalancing(FAIR))
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
cd /app/benchmarks/FAST_FAIR

dos2unix *.sh
./compile_pmdk.sh
./run_pmdk.sh

pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk.trace                > ${CPRD_RESULTS_RACES}/fastfair.races
# pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk-recovery.trace       > ${CPRD_RESULTS_RACES}/fastfair-recovery.races
pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk-mixed.trace          > ${CPRD_RESULTS_RACES}/fastfair-mixed.races
# pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk-mixed-recovery.trace > ${CPRD_RESULTS_RACES}/fastfair-mixed-recovery.races
