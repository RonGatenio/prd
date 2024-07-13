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
from pycprd.utils import timeit


def elapse_time_bar():
    return alive_bar(stats=False, monitor=False, refresh_secs=0.01)


def run_command(command, cwd=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    with elapse_time_bar():
        process = subprocess.Popen(command, shell=True, cwd=cwd, stdout=stdout, stderr=stderr)
        stdout, stderr = process.communicate()

    if process.returncode != 0:
        print(f"[!] Error running command: {command}\n{stderr.decode()}")


def generate_random_pm_file():
    filename = ''.join(random.choices(string.ascii_lowercase, k=8))
    return f"/tmp/{filename}_pmem_data"


def compile_benchmark(compile_commands, compile_dir, binary, binary_output):
    if not os.path.exists(binary_output):
        with timeit('Benchmark Compiled') as benchmark_compile_time:
            for command in compile_commands:
                print(f"[*] Compiling with command: {command}")
                run_command(command, cwd=compile_dir)
            shutil.copy2(binary, binary_output)
            print(f"[*] Copied binary to {binary_output}")
            
        return {
            'benchmark_compile_time': benchmark_compile_time.total
        }
    else:
        print(f"[*] Using existing executable: {binary_output}")
        return {}


def execute_benchmark(run_command_final, run_dir, trace_file):
    print(f"[*] Running with command: {run_command_final}")
    
    with timeit('Benchmark Execution') as benchmark_execution:
        with open(trace_file, 'w') as f:
            run_command(run_command_final, cwd=run_dir, stderr=f)
    
    return {
        'benchmark_execution_time': benchmark_execution.total
    }


def analyze_prd(trace_file, races_file):
    prd, execution_stats = pycprd.prd_runner.run(trace_file)
    
    s, t = pycprd.prd_runner.races_to_str(prd)
    
    with open(races_file, 'w') as f:
        f.write(s)
    
    stats = {
        'total_race': len(prd.races.races_by_rw_pcs),
        'inter_races': len(prd.races.races_pcs_by_tstate['inter']),
        'intra_races': len(prd.races.races_pcs_by_tstate['intra']),
        'total_race_by_event': len(prd.races.races),
        'races_to_str_evaluation_time': t,
    }
    
    stats.update(execution_stats)
    
    return stats
    
    # TODO: create this func:
    # prd_results, prd_timings = pyprd_runner.run_prd_analysis(trace_file)
    # timings.update(prd_timings)

    # with open(results_file, 'w') as file:
    #     file.write(prd_results)
    # print(f"[*] Results saved to {results_file}")

    # with open(stats_file, 'w') as file:
    #     file.write("--- Benchmark Summary ---\n")
    #     for key, value in timings.items():
    #         file.write(f"{key}: {value:.2f}\n")
    # print(f"[*] Stats saved to {stats_file}")


def run_benchmark(benchmark_name, config):
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
    nkeys = run_config["default_args"]["nkeys"]
    nthreads = run_config["default_args"]["nthreads"]

    pm_file = generate_random_pm_file()
    trace_file = os.path.join(output_dir, f"{benchmark_name}_{nkeys}_{nthreads}.trace")
    races_file = os.path.join(output_dir, f"{benchmark_name}_{nkeys}_{nthreads}.races")
    stats_file = os.path.join(output_dir, f"{benchmark_name}_{nkeys}_{nthreads}.stats")
    binary_output = os.path.join(output_dir, f"{benchmark_name}.exe")

    stats = {
        'name': benchmark_name,
        'trace_file': trace_file,
        'races_file': races_file,
        'binary_output': binary_output,
    }

    try:
        # Compile
        s = compile_benchmark(compile_commands, compile_dir, binary, binary_output)
        stats.update(s)

        # Execute
        run_args = {
            "pm_file": pm_file,
            "nkeys": nkeys,
            "nthreads": nthreads,
        }
        stats.update(run_args)
        
        run_command_final = run_command_template.format(**run_args)
        s = execute_benchmark(run_command_final, run_dir, trace_file)
        stats.update(s)

        # Analyze
        s = analyze_prd(trace_file, races_file)
        stats.update(s)
        
        # Save stats
        with open(stats_file, 'w') as f:
            json.dump(stats, f)
            
        from pprint import pprint
        pprint(stats)

    except Exception as e:
        print(f"[!] An error occurred while running the benchmark '{benchmark_name}': {e}")

def main():
    parser = argparse.ArgumentParser(description='Benchmark Runner for PRD')
    parser.add_argument('benchmark', type=str, help='The name of the benchmark to run')
    parser.add_argument('--config', type=str, default=os.path.join(os.path.dirname(__file__), 'benchmarks.json'), help='Path to the configuration file')

    args = parser.parse_args()

    with open(args.config, 'r') as file:
        config = json.load(file)

    run_benchmark(args.benchmark, config)

if __name__ == "__main__":
    main()
