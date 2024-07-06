#!/bin/sh

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# FAST-FAIR (Failure-Atomic ShifT(FAST) and Failure-Atomic In-place Rebalancing(FAIR))
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
cd /app/benchmarks/FAST_FAIR

dos2unix *.sh
time ./compile_pmdk.sh
time ./run_pmdk.sh

cat ${CPRD_RESULTS_TRACES}/fast-fair-pmdk.trace | tail -n 3
# echo [*] FAST-FAIR: Runing pyprd fast
# pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk.trace --fast       > ${CPRD_RESULTS_RACES}/fastfair.fast.races
# cat ${CPRD_RESULTS_RACES}/fastfair.fast.races | head -n 63

# echo [*] FAST-FAIR: Runing pyprd
# pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk.trace                  > ${CPRD_RESULTS_RACES}/fastfair.races
# cat ${CPRD_RESULTS_RACES}/fastfair.races | head -n 63

# pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk.trace --mock-pdg       > ${CPRD_RESULTS_RACES}/fastfair.mockpdg.races
# pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk-recovery.trace       > ${CPRD_RESULTS_RACES}/fastfair-recovery.races

# echo [*] FAST-FAIR mixed: Runing pyprd fast
# # pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk-mixed.trace            > ${CPRD_RESULTS_RACES}/fastfair-mixed.races
# pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk-mixed.trace --fast > ${CPRD_RESULTS_RACES}/fastfair-mixed.fast.races
# cat ${CPRD_RESULTS_RACES}/fastfair-mixed.fast.races | head -n 63
# # pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk-mixed.trace --mock-pdg > ${CPRD_RESULTS_RACES}/fastfair-mixed.mockpdg.races
# # pycprd ${CPRD_RESULTS_TRACES}/fast-fair-pmdk-mixed-recovery.trace > ${CPRD_RESULTS_RACES}/fastfair-mixed-recovery.races
