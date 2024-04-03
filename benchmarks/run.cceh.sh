#!/bin/sh

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# CCEH (Cacheline-Concious Extendible Hashing)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
cd /app/benchmarks/CCEH

dos2unix *.sh
./compile.sh
./run_pmdk.sh

pycprd ${CPRD_RESULTS_TRACES}/multi_threaded_cceh.trace          > ${CPRD_RESULTS_RACES}/cceh.races
# pycprd ${CPRD_RESULTS_TRACES}/multi_threaded_cceh-recovery.trace > ${CPRD_RESULTS_RACES}/cceh-recovery.races
