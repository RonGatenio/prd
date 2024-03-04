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
    # with timeit('hbg without dc'):
    #     hbg = trace.to_hbg(make_daisy_chains=False)

    # with timeit('trace file parsing'):
    #     trace = TraceParser.from_file(r'C:\Home\Projects\llvm-project\pyprd\real_tests\2022-12-16\trace.txt')
    with timeit('hbg with dc'):
        # hbg = trace.to_hbg(max_lines=1000000)
        hbg = trace.to_hbg(filter_volatile_nodes=True)

    with timeit('hbg stats'):
        print(hbg.stats())
    
    with timeit('pdg'):
        pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    with timeit('find races'):
        races = prd.run(show_first_bug_only=True)
        # for race in prd.run(show_first_bug_only=True):
        #     print(race)

    print(' --- ')
    print(prd.races)
    return


if __name__ == "__main__":
    main()
