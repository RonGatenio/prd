from hbg_trace_parser import TraceParser
from pdg import generate_mock_pdg_v2
from prd import PersistencyRaceDetector
from utils import timeit
import argparse


def run(hbg, pdg,
        ignore_inter_thread_edges=False,
        ignore_flush_nodes=False,
        ignore_persisted_before_index=False,
        ignore_happens_after_index=False,
        ignore_read_node_persistency=False,
        show_only_first_bug_in_thread=False):
    prd = PersistencyRaceDetector(hbg, pdg,
                                  ignore_inter_thread_edges     = ignore_inter_thread_edges,
                                  ignore_flush_nodes            = ignore_flush_nodes,
                                  ignore_persisted_before_index = ignore_persisted_before_index,
                                  ignore_happens_after_index    = ignore_happens_after_index,
                                  ignore_read_node_persistency  = ignore_read_node_persistency,
                                  show_only_first_bug_in_thread = show_only_first_bug_in_thread)
    prd.run()
    print(prd.stats())
    return prd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace")

    args = parser.parse_args()

    with timeit('open trace file'):
        trace = TraceParser.from_file(args.trace)

    with timeit('hbg build'):
        hbg = trace.to_hbg(filter_volatile_nodes=False)

    with timeit('hbg stats'):
        print(hbg.stats(True))

    with timeit('pdg build'):
        pdg = generate_mock_pdg_v2(hbg)

    prd = run(hbg, pdg,
        ignore_inter_thread_edges=False,
        ignore_flush_nodes=False,
        ignore_persisted_before_index=False,
        ignore_happens_after_index=False,
        ignore_read_node_persistency=False,
        show_only_first_bug_in_thread=False)

    # run(hbg, pdg,
    #     ignore_inter_thread_edges=False,
    #     ignore_flush_nodes=False,
    #     ignore_persisted_before_index=True,
    #     ignore_happens_after_index=False,
    #     ignore_read_node_persistency=False,
    #     show_only_first_bug_in_thread=False)

    # run(hbg, pdg,
    #     ignore_inter_thread_edges=False,
    #     ignore_flush_nodes=True,
    #     ignore_persisted_before_index=False,
    #     ignore_happens_after_index=False,
    #     ignore_read_node_persistency=False,
    #     show_only_first_bug_in_thread=False)
    
    # run(hbg, pdg,
    #     ignore_inter_thread_edges=False,
    #     ignore_flush_nodes=False,
    #     ignore_persisted_before_index=True,
    #     ignore_happens_after_index=True,
    #     ignore_read_node_persistency=True,
    #     show_only_first_bug_in_thread=False)
    
    # run(hbg, pdg,
    #     ignore_inter_thread_edges=True,
    #     ignore_flush_nodes=True,
    #     ignore_persisted_before_index=True,
    #     ignore_happens_after_index=True,
    #     ignore_read_node_persistency=True,
    #     show_only_first_bug_in_thread=False)

    print('')
    
    tops = [
        "main ",
        "main::$_0::operator()(int, int) const",
        "main::$_1::operator()(int, int) const",
        'main::$_0::operator()(int, int, int) const'
        'main::$_1::operator()(int, int, int) const'
    ]
    
    with timeit('print races'):
        print(prd.races.to_str(callstack_top=tops))


if __name__ == "__main__":
    main()
