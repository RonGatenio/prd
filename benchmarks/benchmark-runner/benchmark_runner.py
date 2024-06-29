import json
import subprocess
import time
import argparse
from alive_progress import alive_bar
from about_time import about_time
from threading import Thread


def run_command(command, cwd=None):
    result = subprocess.run(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"[!] Error running command: {command}\n{result.stderr.decode()}")
    return result


def show_elapsed_time(start_time, stop_flag):
    while not stop_flag.is_set():
        elapsed = time.time() - start_time
        print(f"\r[*] Elapsed time: {elapsed:.2f} seconds", end="")
        time.sleep(1)
    print()


def compile_benchmark(compile_commands, compile_dir, benchmark_name):
    print(f"\n[*] Compiling benchmark '{benchmark_name}'...\n")
    with alive_bar(len(compile_commands), title='Compiling') as bar:
        for command in compile_commands:
            print(f"\n[*] Compiling with command: {command}")
            start_time = time.time()
            stop_flag = Thread(target=show_elapsed_time, args=(start_time,))
            stop_flag.start()
            with about_time() as t:
                run_command(command, cwd=compile_dir)
            stop_flag.join()
            print(f"[*] Time taken: {t.duration_human}")
            bar()


def run_benchmark_command(run_command_final, run_dir, benchmark_name):
    print(f"\n[*] Running benchmark '{benchmark_name}' with command: {run_command_final}\n")
    start_time = time.time()
    stop_flag = Thread(target=show_elapsed_time, args=(start_time,))
    stop_flag.start()
    with about_time() as t:
        run_command(run_command_final, cwd=run_dir)
    stop_flag.join()
    print(f"[*] Execution time for {benchmark_name}: {t.duration_human}")


def analyze_trace(trace_file, results_file, benchmark_name):
    prd_command = f"pycprd {trace_file} > {results_file}"
    print(f"\n[*] Analyzing trace file with PRD for '{benchmark_name}'...\n")
    start_time = time.time()
    stop_flag = Thread(target=show_elapsed_time, args=(start_time,))
    stop_flag.start()
    with about_time() as t:
        run_command(prd_command)
    stop_flag.join()
    print(f"[*] PRD analysis time for {benchmark_name}: {t.duration_human}")

    with open(results_file, 'r') as file:
        results = file.read()
    print(f"\n[*] Results for {benchmark_name}:\n{results}")


def run_benchmark(benchmark_name, config, run_args):
    benchmark_config = config.get(benchmark_name, {})
    if not benchmark_config:
        print(f"[!] Benchmark '{benchmark_name}' not found in configuration.")
        return

    compile_config = benchmark_config.get("compile", {})
    run_config = benchmark_config.get("run", {})

    compile_dir = compile_config.get("directory")
    compile_commands = compile_config.get("commands", [])

    run_dir = run_config.get("directory")
    run_command_template = run_config.get("command")
    default_args = run_config.get("default_args", {})

    trace_file = benchmark_config.get("trace_file")
    results_file = benchmark_config.get("results_file")

    if not compile_dir or not compile_commands or not run_dir or not run_command_template or not trace_file or not results_file:
        print(f"[!] Invalid configuration for benchmark '{benchmark_name}'.")
        return

    try:
        compile_benchmark(compile_commands, compile_dir, benchmark_name)

        run_args_combined = {**default_args, **run_args}
        run_command_final = run_command_template.format(**run_args_combined, trace_file=trace_file)

        run_benchmark_command(run_command_final, run_dir, benchmark_name)

        analyze_trace(trace_file, results_file, benchmark_name)

    except Exception as e:
        print(f"[!] An error occurred while running the benchmark '{benchmark_name}': {e}")


def list_benchmarks(config):
    print("\n[*] Available Benchmarks:")
    for benchmark in config.keys():
        print(f" - {benchmark}")


def main():
    parser = argparse.ArgumentParser(description='Benchmark Runner for PRD')
    parser.add_argument('benchmark', type=str, nargs='?', help='The name of the benchmark to run')
    parser.add_argument('--config', type=str, default='benchmarks.json', help='Path to the configuration file')
    parser.add_argument('--args', type=str, nargs='*', help='Arguments to override default run arguments')
    parser.add_argument('--list', action='store_true', help='List all available benchmarks')

    args = parser.parse_args()

    with open(args.config, 'r') as file:
        config = json.load(file)

    if args.list:
        list_benchmarks(config)
        return

    if not args.benchmark:
        print("[!] Please specify a benchmark to run or use --list to see all available benchmarks.")
        return

    run_args = {}
    if args.args:
        for arg in args.args:
            key, value = arg.split('=')
            run_args[key] = value

    run_benchmark(args.benchmark, config, run_args)


if __name__ == "__main__":
    main()
