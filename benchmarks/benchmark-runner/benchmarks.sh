#!/bin/bash

python3 benchmark_runner.py FAST_FAIR --nkeys 10
python3 benchmark_runner.py CCEH --nkeys 10
python3 benchmark_runner.py RECIPE --nkeys 10
python3 benchmark_runner.py MEMCACHED --nkeys 10

python3 benchmark_runner.py FAST_FAIR --nkeys 100
python3 benchmark_runner.py CCEH --nkeys 100
python3 benchmark_runner.py RECIPE --nkeys 100
python3 benchmark_runner.py MEMCACHED --nkeys 100

python3 benchmark_runner.py FAST_FAIR --nkeys 1000
python3 benchmark_runner.py CCEH --nkeys 1000
python3 benchmark_runner.py RECIPE --nkeys 1000
python3 benchmark_runner.py MEMCACHED --nkeys 1000

python3 benchmark_runner.py FAST_FAIR --nkeys 10000
python3 benchmark_runner.py CCEH --nkeys 10000
python3 benchmark_runner.py RECIPE --nkeys 10000
python3 benchmark_runner.py MEMCACHED --nkeys 10000

python3 benchmark_runner.py FAST_FAIR --nkeys 100000
python3 benchmark_runner.py CCEH --nkeys 100000
python3 benchmark_runner.py RECIPE --nkeys 100000
python3 benchmark_runner.py MEMCACHED --nkeys 100000
