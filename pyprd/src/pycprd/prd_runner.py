from dataclasses import dataclass
# from timeit import timeit

from .trace_parser import TraceParser
from .pdg import generate_mock_pdg_v2
from .prd import PersistencyRaceDetector
from .utils import timeit


@dataclass
class PersistencyRaceDetectorRunner:
    pass


def _run(hbg, pdg,
        ignore_inter_thread_edges=False,
        ignore_flush_nodes=False,
        ignore_persisted_before_index=False,
        ignore_happens_after_index=False,
        ignore_read_node_persistency=False,
        show_only_first_bug_in_thread=False,
        use_fast=True):
    prd = PersistencyRaceDetector(hbg, pdg,
                                  ignore_inter_thread_edges     = ignore_inter_thread_edges,
                                  ignore_flush_nodes            = ignore_flush_nodes,
                                  ignore_persisted_before_index = ignore_persisted_before_index,
                                  ignore_happens_after_index    = ignore_happens_after_index,
                                  ignore_read_node_persistency  = ignore_read_node_persistency,
                                  show_only_first_bug_in_thread = show_only_first_bug_in_thread)
    prd.run(use_faster_version=use_fast)
    print(prd.stats())
    return prd


def run(trace_file: str):
    with timeit(f'open trace file "{trace_file}"'):
        trace = TraceParser.from_file(trace_file)

    with timeit('hbg build'):
        hbg = trace.build_hbg(filter_volatile_nodes=False)

    with timeit('hbg stats'):
        print(hbg.stats(True))

    with timeit('pdg build'):
        if False:
            pdg = generate_mock_pdg_v2(hbg)
        else:
            pdg = trace.build_pdg(hbg, True)

    prd = _run(hbg, pdg,
        ignore_inter_thread_edges=False,
        ignore_flush_nodes=False,
        ignore_persisted_before_index=False,
        ignore_happens_after_index=False,
        ignore_read_node_persistency=False,
        show_only_first_bug_in_thread=False)
    
    if True:
        return

    print('')
    
    tops = [
        r"main::\$_\d+::operator\(\)\(int, int(, int)?\) const",
        # r'std::function<std::unique_ptr<std::__future_base::_Result_base, std::__future_base::_Result_base::_Deleter>',
    ]
    
    with timeit('print races'):
        print(prd.races.to_str(callstack_top=tops, trace_lines=False))
