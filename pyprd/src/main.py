from collections import defaultdict, namedtuple
from contextlib import contextmanager
from datetime import datetime
from functools import reduce
import dill as pickle
# import pickle
from typing import Any, Dict, Set, Tuple
from hbg_trace_parser import TraceParser
from pdg import PDG, generate_mock_pdg, generate_mock_pdg_v2
from hbg import HBG, HBGBuilder
import time
import networkx as nx
import nodes
import prd
from prd_v2 import PersistencyRaceDetector
import serializer
from utils import timeit


def main():
    # HBG
    trace = TraceParser.from_file(r'C:\Home\Projects\llvm-project\pyprd\real_tests\2022-12-16\trace.txt')
    # with timeit('hbg without dc'):
    #     hbg = trace.to_hbg(make_daisy_chains=False)

    # with timeit('trace file parsing'):
    #     trace = TraceParser.from_file(r'C:\Home\Projects\llvm-project\pyprd\real_tests\2022-12-16\trace.txt')
    with timeit('hbg with dc'):
        # hbg = trace.to_hbg(max_lines=1000000)
        hbg = trace.to_hbg()

    with timeit('hbg stats'):
        print(hbg.stats())
    
    with timeit('pdg'):
        pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    with timeit('find races'):
        races = prd.run(show_first_bug_only=False)
        # for race in prd.run(show_first_bug_only=True):
        #     print(race)

    print(' --- ')
    print(' --- ')
    print(' --- ')
    print(' --- ')
    print(' --- ')
    print(' --- ')
    print(' --- ')
    print(' --- ')
    print(' --- ')
    print(prd.races)
    return

    
    import os
    def simplify_info(s: str):
        parts = s.split()
        parts[-2] = f'<{os.path.basename(parts[-2])}>'
        return ' '.join(parts)

    for n in hbg.read_write_nodes:
        n._info = simplify_info(n.info)

    # PDG
    with timeit('pdg'):
        pdg = generate_mock_pdg(hbg, 30)
    
    # PRD
    p = prd.PersistencyRaceDetector(hbg, pdg)
    
    races = p.run()
    
    dirname = f'test-results/{datetime.now():%Y-%m-%d_%H-%M}-{trace.name}'
    try:
        os.makedirs(dirname)
    except:
        pass
        
    with open(f'{dirname}/races.txt', 'w') as f:
        f.write('\n----------\n'.join(map(str, races)))
    
    with open(f'{dirname}/races_summary.txt', 'w') as f:
        f.write(p.races_to_str())
    
    with timeit('save all'):
        serializer.save(hbg=hbg, pdg=pdg, p=p, filename=f'{dirname}/data.bin')
    return

    print()
    fw_fr_tests(p)

    print()
    ha_tests(p)


def main_2022_10_13():
    filename = r'H:\Projects\LLVM\llvm-project\pyprd\src\2022-10-13-17-15\data.bin'
    with timeit(f'Load data'):
        data = serializer.load(filename)
    
    hbg: HBG                                                    = data['hbg']
    pdg: PDG                                                    = data['pdg']
    p: prd.PersistencyRaceDetector                              = data['p']
    delta_ha_groups: Dict[ReadNode, Dict[Var, Set[WriteNode]]]  = data['delta_ha_groups']
    delta_fw_groups: Dict[WriteNode, Dict[Var, Set[WriteNode]]] = data['delta_fw_groups']
    delta_fr_groups: Dict[WriteNode, Dict[Var, Set[ReadNode]]]  = data['delta_fr_groups']
    nodes_info_dict: Dict[str, Set[nodes.InstructionNode]]      = data['nodes_info_dict']
    races_info_dict: Dict[str, Set[str]]                        = data['races_info_dict']
    races_dict: Dict[ReadNode, Set[WriteNode]]                  = data['races_dict']
        
    print(hbg.stats())
    
    races = {r: [w for w in writes if 'example+0x4d7a81' in w.info] for r, writes in races_dict.items() if 'example+0x4d778a' in r.info}
    races: Dict[ReadNode, WriteNode] = {r: s[0] for r, s in races.items() if s}
    # print(races)
    
    violating_nodes = set()
    for k, v in nodes_info_dict.items():
        if 'clht_lb_res.c:767:' in k:
            violating_nodes.update(v)
        
    print(f'Desird violating nodes count: {len(violating_nodes)}')
    
    violating_node: WriteNode = list(violating_nodes)[0]
    print(f'Desird violating node: {violating_node}')
    print()
    
    violating_node_loc = hbg.get_node_location(violating_node)
    
    flush_node = hbg.get_intra_child(violating_node)
    assert flush_node.itype == nodes.NodeType.FLUSH
    
    for r, w in races.items():
        if violating_node in nx.dfs_successors(hbg._graph, r):
            print('Happens after - not a race')
            continue
        
        if w in nx.dfs_successors(hbg._graph, flush_node):
            print('After flush - not a race')
            continue
        
        print('Should be a race')
        # print((r, w))
        # print(hbg.get_node_location(r))
        # print(hbg.get_node_location(w))
            
    print()
    print('R(X)s')
    print('\n'.join(list({v.info for v in hbg._vars[violating_node.interval]})))
    print()
    
    the_real_r_x = [n for n in hbg.read_nodes if 'clht_put <clht_lb_res.c> (example+0x4d7768)' in n.info][0]
    
    assert the_real_r_x.interval == violating_node.interval
    
    print('The real R(X)')
    print(the_real_r_x)
    print()
    
    print('R(X) dependants')
    print(list(pdg.get_dependants(the_real_r_x)))
    print()
    
    n = the_real_r_x
    read_count = 1
    for i in range(1000):
        found = False
        
        if n.itype == nodes.NodeType.READ:
            for w in pdg.get_dependants(n):
                if 'clht_lb_res.c:452:' in w.info:
                    print(f'Found the depandant for read at {hbg.get_node_location(n)} - at offset {read_count} from the real_r_x node')
                    found = True
                    break
            read_count += 1
        if found:
            break
        n = hbg.get_intra_child(n)
    
    
    import ipdb; ipdb.set_trace()
    return
    

def main_2022_10_20():
    filename = r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-10-20-01-16\data.bin'
    with timeit(f'Load data'):
        data = serializer.load(filename)
    
    hbg: HBG                                                    = data['hbg']
    pdg: PDG                                                    = data['pdg']
    p: prd.PersistencyRaceDetector                              = data['p']
        
    with timeit(f'Stats'):
        print(hbg.stats())
        
    # r_x = hbg.get_node_by_location((3, 147009))
    # w_y = hbg.get_node_by_location((3, 147010))
    # w_x = hbg.get_node_by_location((3, 114225))
    
    # print(r_x)
    # print(w_x)
    
    r_x = hbg.get_node_by_location((6, 27566))
    w_y = hbg.get_node_by_location((6, 27567))
    w_x = hbg.get_node_by_location((8, 15260))
    
    print(r_x)
    print(w_x)
    
    pp = nx.shortest_path(hbg._graph, w_x, r_x)
    
    print(len(pp))
    
    prev_tid = None
    for n in pp:
        if n.tid != prev_tid:
            print(n.tid)
            import ipdb; ipdb.set_trace()
            prev_tid = n.tid
        if not isinstance(n, nodes.InstructionNode):
            continue
        
        if n.itype.name == 'FLUSH':
            import ipdb; ipdb.set_trace()
    
    # r_x = hbg.get_node_by_location((6, 27573))
    # w_y = hbg.get_node_by_location((6, 27574))
    # w_x = hbg.get_node_by_location((8, 19356))
    
    # with open('callstack.txt', 'w') as f:
    
    #     thread_nodes = hbg.get_thread_nodes(3)
    #     for i in range(114225, 147009):
    #         n = thread_nodes[i]
            
    #         if not isinstance(n, nodes.InstructionNode):
    #             continue
            
    #         f.write(f'{n.info}\n')
            
    #         if n.itype == 'FLUSH':
    #             import ipdb; ipdb.set_trace()
    
    
    return

    p2 = prd.PersistencyRaceDetector(hbg, pdg)
    # import ipdb; ipdb.set_trace()
    list(p2.finale(
        p._delta_ha_groups,
        p._delta_fw_groups,
        p._delta_fr_groups,
    ))
    # for r in p._all_races:
    #     if '0x4d8bdc' in r.read_node.info and ''


def get_nodes_by_sourceline(hbg: HBG, line, col=None, var=None):
    location_str = f':{line}:'
    if col is not None:
        location_str += f'{col}'
        
    group = hbg.instruction_nodes
    if var is not None:
        group = hbg.get_nodes_by_var(var)
        
    return list(filter(lambda n: location_str in n.info, group))


def main_2022_11_04():
    filename = r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-11-04\data.bin'
    with timeit(f'Load data'):
        data = serializer.load(filename)
    
    hbg: HBG                                                    = data['hbg']
    pdg: PDG                                                    = data['pdg']
    p: prd.PersistencyRaceDetector                              = data['p']
    
    print(hbg.stats())
    
    newp = prd.PersistencyRaceDetector(p.hbg, p.ppdg)
    
    list(newp.finale(p._delta_ha_groups, p._delta_fw_groups, p._delta_fr_groups))
    return
    
    
    
    read_nodes = get_nodes_by_sourceline(hbg, 575, 31)
    
    # Single case
    # read_node = read_nodes[100]
    # write_node, = get_nodes_by_sourceline(hbg, 442, 27, read_node.interval)
    
    # assert read_node in nx.dfs_successors(hbg.graph, write_node)
    
    # cachline = utils.get_cacheline_address(read_node.address, hbg.cacheline_size)
    # flush_nodes = list(filter(lambda n: n.address == cachline, hbg.flush_nodes))
    # flush_node, = list(filter(lambda n: n.tid == write_node.tid, flush_nodes))
    
    # assert flush_node in nx.dfs_successors(hbg.graph, write_node)
    # assert read_node in nx.dfs_successors(hbg.graph, flush_node)
    
    # All cases
    ss= defaultdict(lambda: 0)
    for read_node in read_nodes:
        write_nodes = get_nodes_by_sourceline(hbg, 442, 27, read_node.interval)
        if not write_nodes:
            continue
        
        if len(write_nodes) > 1:
            print(read_node in nx.dfs_successors(hbg.graph, write_nodes[0]))
            print(read_node in nx.dfs_successors(hbg.graph, write_nodes[1]))
            print(write_nodes[1] in nx.dfs_successors(hbg.graph, read_node))
            import ipdb; ipdb.set_trace()
            pass
        
        ss[len(write_nodes)] +=1
        # if len(write_nodes) > 1:
            # print('what')
            # for write_node in write_nodes:
            #     print(f'{write_node} - {hbg.get_node_location(write_node)}')
    print(ss)
    
    # nw = []
    # for n in nr:
    #     nw.extend(get_nodes_by_sourceline(hbg, 442, 27, n.interval))
    
    while True:
        import ipdb; ipdb.set_trace()
        pass


if __name__ == "__main__":
    # test2()
    # test3()
    main()
    # main_2022_10_13()
    # main_2022_10_20()
    # main_2022_11_04()
