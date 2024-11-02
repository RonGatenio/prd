import json
import subprocess
import os
import argparse
import random
import string
import shutil
import time
import threading
from contextlib import contextmanager
from alive_progress import alive_bar
import pycprd
import pycprd.prd_runner
from pycprd.statistics_collector import StatisticsCollector
from pycprd.utils import timeit


def elapse_time_bar():
    return alive_bar(stats=False, monitor=False, refresh_secs=0.01)


def run_command(command, cwd=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    with elapse_time_bar():
        process = subprocess.Popen(command, shell=True, cwd=cwd, stdout=stdout, stderr=stderr)
        stdout, stderr = process.communicate()

    if process.returncode != 0:
        print(f"[!] Error running command: {command} (LE={process.returncode})")


def generate_random_pm_file():
    filename = ''.join(random.choices(string.ascii_lowercase, k=8))
    return f"/tmp/{filename}_pmem_data"


def compile_benchmark(compile_commands, compile_dir, binary, binary_output) -> StatisticsCollector:
    stats = StatisticsCollector('Compile')
    
    if not os.path.exists(binary_output):
        with timeit('Benchmark Compiled') as benchmark_compile_time:
            for command in compile_commands:
                print(f"[*] Compiling with command: {command}")
                run_command(command, cwd=compile_dir)
            shutil.copy2(binary, binary_output)
            print(f"[*] Copied binary to {binary_output}")
            
        stats.add_statistic('Benchmark Duration', 'Compile time [sec]', benchmark_compile_time.total)
    else:
        print(f"[*] Using existing executable: {binary_output}")
    
    return stats


def execute_benchmark(run_command_final, run_dir, trace_file) -> StatisticsCollector:
    stats = StatisticsCollector('Execution')

    print(f"[*] Running with command: {run_command_final}")
    
    with timeit('Benchmark Execution') as benchmark_execution:
        with open(trace_file, 'w') as f:
            run_command(run_command_final, cwd=run_dir, stderr=f)
    
    stats.add_statistic('Benchmark Duration', 'Execution time [sec]', benchmark_execution.total)
    
    return stats


def analyze_prd(trace_file, races_file, code_tours_folder=None) -> StatisticsCollector:
    prd, stats = pycprd.prd_runner.run(trace_file)
    
    races_str, t = pycprd.prd_runner.races_to_str(prd)
    
    with open(races_file, 'w') as f:
        f.write(races_str)
        
    stats.add_statistic('Duration', 'Races Print Evaluation [sec]', t)
    
    if code_tours_folder:
        t = pycprd.prd_runner.races_generate_code_tours(prd, code_tours_folder=code_tours_folder)
        stats.add_statistic('Duration', 'Races to Code Tours [sec]', t)
    
    return stats


def run_benchmark(benchmark_name, config, nkeys=None):
    print(f'[*] Running Benchmark {benchmark_name}')
    stats = StatisticsCollector(f'Benchmark Execution {benchmark_name}')
    
    benchmark_config = config.get(benchmark_name, {})
    if not benchmark_config:
        print(f"[!] Benchmark '{benchmark_name}' not found in configuration.")
        return

    output_dir = benchmark_config["output_dir"]
    os.makedirs(output_dir, exist_ok=True)

    compile_config = benchmark_config["compile"]
    run_config = benchmark_config["run"]
    binary = benchmark_config["binary"]

    compile_dir = compile_config["directory"]
    compile_commands = compile_config["commands"]

    run_dir = run_config["directory"]
    run_command_template = run_config["command"]
    nkeys = run_config["default_args"]["nkeys"] if nkeys is None else nkeys
    nthreads = run_config["default_args"]["nthreads"]

    pm_file = generate_random_pm_file()
    trace_file = os.path.join(output_dir, f"{benchmark_name}_{nkeys}_{nthreads}.trace")
    races_file = os.path.join(output_dir, f"{benchmark_name}_{nkeys}_{nthreads}.races")
    stats_file = os.path.join(output_dir, f"{benchmark_name}_{nkeys}_{nthreads}.stats")
    stats_json_file = os.path.join(output_dir, f"{benchmark_name}_{nkeys}_{nthreads}.stats.json")
    code_tours_folder = os.path.join(output_dir, f"{benchmark_name}_{nkeys}_{nthreads}.tours")
    binary_output = os.path.join(output_dir, f"{benchmark_name}.exe")

    stats.add_statistic('Benchmark Presets', 'Name', benchmark_name)
    stats.add_statistic('Benchmark Output', 'Trace file', trace_file)
    stats.add_statistic('Benchmark Output', 'Races file', races_file)
    stats.add_statistic('Benchmark Output', 'Stats file', stats_file)
    stats.add_statistic('Benchmark Output', 'Stats json', stats_json_file)
    stats.add_statistic('Benchmark Output', 'Code Tours folder', code_tours_folder)
    stats.add_statistic('Benchmark Output', 'Executable', binary_output)

    try:
        # Compile
        s = compile_benchmark(compile_commands, compile_dir, binary, binary_output)
        stats.merge(s)

        # Execute
        stats.add_statistic('Benchmark Presets', 'nkeys', nkeys)
        stats.add_statistic('Benchmark Presets', 'nthreads', nthreads)

        run_args = {
            "pm_file": pm_file,
            "nkeys": nkeys,
            "nthreads": nthreads,
        }
        
        run_command_final = run_command_template.format(**run_args)
        s = execute_benchmark(run_command_final, run_dir, trace_file)
        stats.merge(s)

        # Analyze
        s = analyze_prd(trace_file, races_file, code_tours_folder)
        stats.merge(s)
        
        # Save stats
        with open(stats_file, 'w') as f:
            f.write(stats.to_str())
            
        with open(stats_json_file, 'w') as f:
            f.write(stats.to_json())
            
        print(stats)

    except Exception as e:
        print(f"[!] An error occurred while running the benchmark '{benchmark_name}': {e}")
        raise e

def main():
    parser = argparse.ArgumentParser(description='Benchmark Runner for PRD')
    parser.add_argument('benchmark', type=str, help='The name of the benchmark to run')
    parser.add_argument('--config', type=str, default=os.path.join(os.path.dirname(__file__), 'benchmarks.json'), help='Path to the configuration file')
    parser.add_argument('--nkeys', type=int, default=None, help='nKeys used in benchmark')

    args = parser.parse_args()

    with open(args.config, 'r') as file:
        config = json.load(file)

    run_benchmark(args.benchmark, config, nkeys=args.nkeys)

if __name__ == "__main__":
    main()
