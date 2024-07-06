#!/bin/sh

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# CCEH (Cacheline-Concious Extendible Hashing)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
cd /app/benchmarks/CCEH

dos2unix *.sh
time ./compile.sh
time ./run_pmdk.sh

echo [*] CCEH: Runing pyprd fast
pycprd ${CPRD_RESULTS_TRACES}/multi_threaded_cceh.trace --fast > ${CPRD_RESULTS_RACES}/cceh.fast.races
cat ${CPRD_RESULTS_RACES}/cceh.fast.races | head -n 63

echo [*] CCEH: Runing pyprd
pycprd ${CPRD_RESULTS_TRACES}/multi_threaded_cceh.trace            > ${CPRD_RESULTS_RACES}/cceh.races
cat ${CPRD_RESULTS_RACES}/cceh.races | head -n 63

# pycprd ${CPRD_RESULTS_TRACES}/multi_threaded_cceh.trace --mock-pdg > ${CPRD_RESULTS_RACES}/cceh.mockpdg.races
# pycprd ${CPRD_RESULTS_TRACES}/multi_threaded_cceh-recovery.trace > ${CPRD_RESULTS_RACES}/cceh-recovery.races
