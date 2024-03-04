from hbg_trace_parser import TraceParser
from pdg import generate_mock_pdg_v2
from prd_v2 import PersistencyRaceDetector
from utils import timeit
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace")

    args = parser.parse_args()

    trace = TraceParser.from_file(args.trace)

    with timeit('hbg build'):
        hbg = trace.to_hbg(filter_volatile_nodes=True)

    with timeit('hbg stats'):
        print(hbg.stats())
    
    with timeit('pdg build'):
        pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    with timeit('find races'):
        prd.run(show_first_bug_only=True)

    print(' --- ')
    print(prd.races)


if __name__ == "__main__":
    main()
