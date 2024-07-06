#!/bin/sh

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# memcached-pmem (high performance multithreaded event-based key/value cache store intended to be used in a distributed system)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
cd /app/benchmarks/memcached-pmem

dos2unix *.sh
time ./compile.sh
time ./run.sh

echo [*] memcached-pmem: Runing pyprd fast
pycprd ${CPRD_RESULTS_TRACES}/memcached.trace > ${CPRD_RESULTS_RACES}/memcached.fast.races
cat ${CPRD_RESULTS_RACES}/memcached.fast.races | head -n 63

