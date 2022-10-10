from genericpath import isfile
from typing import Any, Dict, Set, Tuple
from hbg_trace_parser import TraceParser
from pdg import generate_mock_pdg
from hbg import HBG, HBGBuilder
from collections import namedtuple
import networkx as nx
import nodes


def analyze_cycle(g: HBG):
    if nx.is_directed_acyclic_graph(g):
        print('HBG is DAG :)')
        return
    
    cycle = nx.find_cycle(g)
    
    print(f'Found cycle of length {len(cycle)}')
    
    cycle_thread_breaks = [e for e in cycle if e[0].tid != e[1].tid]
    
    s = '\n'.join(f'{v1},\t{g.get_node_location(v1)}\t-> {v2},\t{g.get_node_location(v2)}' for v1, v2 in cycle_thread_breaks)
    print(s)


def analyze_vars(hbg: HBG):
    import intervaltree
    t = intervaltree.IntervalTree()
    for n in hbg.read_write_nodes:
        t.addi(*n.interval)
        
    t.merge_equals()
    
    interval_sizes = {}
    for i in t.all_intervals:
        size = i.length()
        interval_sizes.setdefault(size, set()).add(i)
    
    print(f'Variables found {len(t.all_intervals)}')
    print(f'Variable sizes  {list(interval_sizes.keys())}')
    
    max_size = max(interval_sizes.keys())
    for size, _nodes in interval_sizes.items():
        if size == max_size:
            continue
        print(f'Calculating for {len(_nodes)} of size {size}')
        for _size, __nodes in interval_sizes.items():
            if size < _size:
                print(f'is there an overlap with a var of size {_size}')
                # b = False
                for n in _nodes:
                    for _n in __nodes:
                        if n.overlaps(_n):
                            print(f'FOUND overlap: {n} {_n}')
                            b = True
                            break
                    if b:
                        break
                        
            
    # print(f'')

ReadNode = WriteNode = nodes.InstructionNode
Var = Tuple[int, int]


def merge(d1: Dict[Any, Set[Any]], d2: Dict[Any, Set[Any]]):
    for k, v in d2.items():
        d1.setdefault(k, set()).update(v)


def compare(hbg: HBG, d1: Dict[ReadNode, Dict[Var, Set[WriteNode]]], d2: Dict[ReadNode, Dict[Var, Set[WriteNode]]], delta_d2: Dict[ReadNode, Dict[Var, Set[WriteNode]]]):
    for r in hbg.read_nodes:
        dd1 = d1.get(r, {})
        dd2 = d2.get(r, {})
        
        for var in set(dd1.keys()) | set(dd2.keys()):
            s1 = dd1.get(var, set())
            s2 = dd2.get(var, set())
            
            if s1 != s2:
                print(f'Failed in {r.tid}')
                import ipdb; ipdb.set_trace()
                return False
            
    return True

def mycopy(d1: Dict[Var, Set[WriteNode]]):
    d = {}
    for k, v in d1.items():
        d[k] = v.copy()
    return d

def build_ha_groups(hbg: HBG, delta_ha_groups: Dict[ReadNode, Dict[Var, Set[WriteNode]]]):
    ha_groups: Dict[ReadNode, Dict[Var, Set[WriteNode]]] = {}
    
    for tid in hbg.tids:
        thread_nodes = hbg.get_thread_nodes(tid)
        prev: Dict[Var, Set[WriteNode]] = {}
        
        for n in reversed(thread_nodes):
            if n.itype != 'READ':
                continue
            merge(prev, delta_ha_groups.get(n, {}))
            ha_groups[n] = mycopy(prev)
            
    return ha_groups
        

def main():
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe_2.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe_3.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_out_small.txt')
    # trace = TraceParser.from_file(r'H:\Home\Technion\Projects\Repos\RECIPE\P-CLHT\build\test_recipe_4.txt')
    
    # b = HBGBuilder()
    # b.add_epoch_node(0, 0)
    # b.add_instruction_node('WRITE', 0, 0, 0, 0)
    # b.add_instruction_node('WRITE', 0, 0, 0, 0)
    # b.add_instruction_node('WRITE', 0, 0, 0, 0)
    # b.add_instruction_node('WRITE', 0, 0, 0, 0)
    # b.add_instruction_node('WRITE', 0, 0, 0, 0)
    # b.add_instruction_node('WRITE', 0, 0, 0, 0)
    # b.add_instruction_node('WRITE', 0, 0, 0, 0)
    # b.add_instruction_node('WRITE', 0, 0, 0, 0)
    # b.add_epoch_node(0, 1)
    
    # hbg = b.build(False)
    # assert nx.is_directed_acyclic_graph(hbg._intra_graph)
    # import ipdb; ipdb.set_trace()
    
    import time
    import intervaltree
    
    # s = time.time()
    # hbg = trace.to_hbg(filter=False)
    # print(f'hbg {time.time() - s} sec')
    
    # for t in nodes.NodeType:
    #     print(f'{t.name:6} {len(hbg.get_nodes_by_type(t))}')
        
    # t = intervaltree.IntervalTree()
    # for n in hbg.read_write_nodes:
    #     t.addi(*n.interval)
        
    # t.merge_equals()
    
    # print({(i.begin, i.end) for i in t.all_intervals})
    # import ipdb; ipdb.set_trace()
    # import ipdb; ipdb.set_trace()
    
    hbg, pdg = None, None
    
    # import os
    # if os.path.isfile('data.bin'):
    #     with open('data.bin', 'rb') as f:
    #         from pickle import Unpickler
    #         upp = Unpickler(f)
    #         hbg, pdg = upp.load()
    
    if not hbg:
        s = time.time()
        hbg = trace.to_hbg(filter=True, max_lines=10000)
        print(f'hbg {time.time() - s} sec')
    
        
        for t in nodes.NodeType:
            print(f'{t.name:6} {len(hbg.get_nodes_by_type(t))}')
            
    # analyze_cycle(hbg)
    # # print('HBG is DAG' if nx.is_directed_acyclic_graph(hbg) else 'HBG is not DAG ):')
    # analyze_vars(hbg)
    # return
    
    
    # t = intervaltree.IntervalTree()
    # for n in hbg.read_write_nodes:
    #     t.addi(*n.interval)
        
    # t.merge_equals()
    
    # intervals = {(i.begin, i.end) for i in t.all_intervals}
    # interval_sizes = {(i.end - i.begin) for i in t.all_intervals}
    # print(interval_sizes)
    # print(len(intervals))
    # import ipdb; ipdb.set_trace()
    
    if not pdg:
        s = time.time()
        pdg = generate_mock_pdg(hbg)
        print(f'pdg {time.time() - s} sec')
        
        print(f'nodes count {len(hbg.read_nodes)}')
        total = len(hbg.read_nodes)
    
    import pickle
    
    # if not os.path.isfile('data.bin'):
    #     with open('data.bin', 'wb') as f:
    #         pp = pickle.Pickler(f)
    #         pp.dump((hbg, pdg))
    
    
    import prd
    p = prd.PersistencyRaceDetector(hbg, pdg)
    
    s = time.time()
    op1 = p.build_delta_ha_groups_opt1()
    print(f'build_delta_ha_groups_opt1 {time.time() - s} sec')
    
    s = time.time()
    ha1 = build_ha_groups(hbg, op1)
    print(f'build_ha_groups {time.time() - s} sec')
    
    # s = time.time()
    # op3 = p.build_delta_ha_groups_opt3()
    # print(f'build_delta_ha_groups_opt3 {time.time() - s} sec')
    
    s = time.time()
    op4 = p.build_delta_ha_groups_opt4()
    print(f'build_delta_ha_groups_opt4 {time.time() - s} sec')
    
    print(compare(hbg, op4, ha1, op1))
    
    import ipdb; ipdb.set_trace()
    
    # s = time.time()
    # happens_after_sets = {}
    # next = 0
    # for i, n in enumerate(hbg.read_nodes):
    #     if i / total > next:
    #         next = (i / total) + 0.001
    #         print(f'completed {i / total * 100}%')
    #         print(f'ha0 so far {time.time() - s} sec')
    #     happens_after_sets[n] = nx.descendants(hbg, n)
    # print(f'ha0 {time.time() - s} sec')
    
    # s = time.time()
    # hbg.add_edges_from(((n, d) for n in hbg.read_nodes for d in nx.descendants(hbg, n)))
    # print(f'ha3 {time.time() - s} sec')
    
    # next = 0
    # wn = list(hbg.write_nodes)[-1]
    # s = time.time()
    # for i, n in enumerate(hbg.read_nodes):
    #     wn in nx.descendants(hbg, n)
    #     if i / total > next:
    #         next = (i / total) + 0.0001
    #         print(f'completed {i / total * 100}%')
    #         print(f'ha4 so far {time.time() - s} sec')
    # # hbg.add_edges_from(((n, d) for n in hbg.read_nodes for d in nx.descendants(hbg, n)))
    # print(f'ha4 {time.time() - s} sec')
    
    # s = time.time()
    # happens_after_sets = {}
    # next = 0
    # for i, n in enumerate(hbg):
    #     if i / total > next:
    #         next = (i / total) + 0.000001
    #         print(f'completed {i / total * 100}%')
    #         print(f'ha1 so far {time.time() - s} sec')
    #     happens_after_sets[n] = nx.bfs_tree(hbg, n).nodes
    # print(f'ha1 {time.time() - s} sec')
    
    # s = time.time()
    # happens_after_sets2 = {}
    # next = 0
    # print(f'cc count {len(list(nx.connected_components(hbg.to_undirected())))}')
    # for cc in nx.connected_components(hbg.to_undirected()):
    #     collect = set()
    #     for i, n in enumerate(nx.dfs_postorder_nodes(hbg)):
    #         if i / total > next:
    #             next = (i / total) + 0.01
    #             print(f'completed {i / total * 100}%')
    #             print(f'ha2 so far {time.time() - s} sec')
    #         happens_after_sets2[n] = collect.copy()
    #         collect.add(n)
    # print(f'ha2 {time.time() - s} sec')
    
    # s = time.time()
    # # print(f'cc count {len(list(nx.connected_components(hbg.to_undirected())))}')
    # for cc in nx.connected_components(hbg.to_undirected()):
    #     collect = set()
    #     next = 0
    #     for i, n in enumerate(nx.dfs_postorder_nodes(hbg)):
    #         if i / total > next:
    #             next = (i / total) + 0.01
    #             print(f'completed {i / total * 100}%')
    #             print(f'ha5 so far {time.time() - s} sec')
    #         hbg.add_edges_from(((n, d) for d in collect))
    #         collect.add(n)
    # print(f'ha5 {time.time() - s} sec')
    
    import ipdb; ipdb.set_trace()

if __name__ == "__main__":
    main()
