from collections import OrderedDict
from dataclasses import dataclass
from typing import Tuple

from .statistics_collector import StatisticsCollector
from .trace_parser import TraceParser
from .pdg import generate_mock_pdg_v2
from .prd import PersistencyRaceDetector
from .utils import timeit


def run(trace_file: str, use_mock_pdg=False) -> Tuple[PersistencyRaceDetector, StatisticsCollector]:
    stats = StatisticsCollector('PRD')
    
    with timeit(f'open trace file "{trace_file}"'):
        trace = TraceParser.from_file(trace_file)

    with timeit('hbg build') as hbg_build:
        hbg = trace.build_hbg(filter_volatile_nodes=False)

    with timeit('hbg stats'):
        _stats = hbg.stats()
        print(_stats)
    stats.merge(_stats)
    
    with timeit('pdg build') as pdg_build:
        if use_mock_pdg:
            pdg = generate_mock_pdg_v2(hbg)
        else:
            pdg = trace.build_pdg(hbg, True)
            
    with timeit('cprd_time') as cprd_time:
        prd = PersistencyRaceDetector(hbg, pdg,
            ignore_inter_thread_edges     = False,
            ignore_flush_nodes            = False,
            ignore_persisted_before_index = False,
            ignore_happens_after_index    = False,
            ignore_read_node_persistency  = False,
            show_only_first_bug_in_thread = False)
        
        prd.run(use_faster_version=True)
        
    _stats = prd.stats()
    print(_stats)
    stats.merge(_stats)
    
    stats.add_statistic('Duration', 'HBG build [sec]', hbg_build.total)
    stats.add_statistic('Duration', 'PDG build [sec]', pdg_build.total)
    stats.add_statistic('Duration', 'Algorithm [sec]', cprd_time.total)
    
    return prd, stats


def races_to_str(prd: PersistencyRaceDetector) -> Tuple[str, float]:
    tops = [
        r"main::\$_\d+::operator\(\)\(int, int(, int)?\) const",
        r'std::function<std::unique_ptr<std::__future_base::_Result_base, std::__future_base::_Result_base::_Deleter>',
    ]
    
    with timeit('Races to Str') as races_evaluation_time:
        s = prd.races.to_str(callstack_top=tops, trace_lines=False)
        
    return s, races_evaluation_time.total
