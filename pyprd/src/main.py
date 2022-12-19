from collections import defaultdict, namedtuple
from contextlib import contextmanager
from functools import reduce
import dill as pickle
# import pickle
from typing import Any, Dict, Set, Tuple
from hbg_trace_parser import TraceParser
from pdg import PDG, generate_mock_pdg
from hbg import HBG, HBGBuilder
import time
import networkx as nx
import nodes
import prd
import serializer
import utils


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


ReadNode = WriteNode = nodes.InstructionNode
Var = Tuple[int, int]


def merge(d1: Dict[Any, Set[Any]], d2: Dict[Any, Set[Any]]):
    for k, v in d2.items():
        d1.setdefault(k, set()).update(v)


def compare(hbg: HBG, d1: Dict[ReadNode, Dict[Var, Set[WriteNode]]], d2: Dict[ReadNode, Dict[Var, Set[WriteNode]]], delta_d2: Dict[ReadNode, Dict[Var, Set[WriteNode]]]=None):
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

def mycopy(d1: Dict[Any, Set[Any]]):
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


def build_ha_groups_per_thread(hbg: HBG, delta_ha_groups: Dict[ReadNode, Dict[Var, Set[WriteNode]]]):
    ha_groups: Dict[int, Dict[Var, Set[WriteNode]]] = {}

    for tid in hbg.tids:
        thread_nodes = hbg.get_thread_nodes(tid)
        ha_groups[tid] = {}

        for n in reversed(thread_nodes):
            if n.itype != 'READ':
                continue
            merge(ha_groups[tid], delta_ha_groups.get(n, {}))

    return ha_groups

def build_fwr_groups(hbg: HBG, delta_fwr_groups: Dict[WriteNode, Dict[Var, Set[nodes.InstructionNode]]]):
    fwr_groups: Dict[WriteNode, Dict[Var, Set[nodes.InstructionNode]]] = {}

    for tid in hbg.tids:
        thread_nodes = hbg.get_thread_nodes(tid)
        prev: Dict[WriteNode, Dict[Var, Set[nodes.InstructionNode]]] = {}

        for n in thread_nodes:
            if n.itype != 'WRITE':
                continue
            merge(prev, delta_fwr_groups.get(n, {}))
            fwr_groups[n] = mycopy(prev)

    return fwr_groups


@contextmanager
def timeit(name):
    s = time.time()
    yield
    total = time.time() - s
    print(f'[*] {name:60} {total} sec')


def fw_fr_tests(p: prd.PersistencyRaceDetector, full=True):
    hbg = p.hbg

    print(f'{" FW FR Tests ":*^30}')

    # op00
    with timeit('opt00 - delta groups -  using cahclines instead of vars'):
        delta_fw_op00, delta_fr_op00 = p.build_delta_fw_groups_opt00()

    # op0
    with timeit('opt0  - delta groups'):
        delta_fw_op0, delta_fr_op0 = p.build_delta_fw_groups_opt0()

    with timeit('opt0  - full groups (from the delta groups)'):
        fw_op0 = build_fwr_groups(hbg, delta_fw_op0)
        fr_op0 = build_fwr_groups(hbg, delta_fr_op0)

    # op1
    with timeit('opt1  - delta groups'):
        delta_fw_op1, delta_fr_op1 = p.build_delta_fw_groups_opt1()

    with timeit('opt1  - full groups (from the delta groups)'):
        fw_op1 = build_fwr_groups(hbg, delta_fw_op1)
        fr_op1 = build_fwr_groups(hbg, delta_fr_op1)

    # op2
    with timeit('opt2  - full groups'):
        fw_op2, fr_op2 = p.build_fw_groups_opt2()
        
    # op3
    with timeit('opt3  - delta groups'):
        delta_fw_op3, delta_fr_op3 = p.build_delta_fw_groups_opt3()

    with timeit('opt3  - full groups (from the delta groups)'):
        fw_op3 = build_fwr_groups(hbg, delta_fw_op3)
        fr_op3 = build_fwr_groups(hbg, delta_fr_op3)

    # assert compare(hbg, fw_op0, fw_op1)
    # assert compare(hbg, fw_op0, fw_op2)
    assert compare(hbg, fw_op0, fw_op3)
    # assert compare(hbg, fr_op0, fr_op1)
    # assert compare(hbg, fr_op0, fr_op2)
    assert compare(hbg, fr_op0, fr_op3)

    print(f'{"":*^30}')


def ha_tests(p: prd.PersistencyRaceDetector):
    hbg = p.hbg

    print(f'{" HA Tests ":*^30}')

    ## op1
    with timeit('opt1 - delta groups'):
        dop1 = p.build_delta_ha_groups_opt1()

    with timeit('opt1 - full groups (from the delta groups)'):
        op1 = build_ha_groups(hbg, dop1)

    with timeit('opt1 - the top full group per thread (from the delta groups)'):
        top1 = build_ha_groups_per_thread(hbg, dop1)

    for tid in hbg.tids:
        for n in hbg.get_thread_nodes(tid):
            if n.itype == 'READ':
                break
        if not compare(hbg, top1[tid], op1[n]):
            print('NOT EQUAL')

    ## op2
    with timeit('opt2 - delta groups'):
        dop2 = p.build_delta_ha_groups_opt2()

    with timeit('opt2 - full groups (from the delta groups)'):
        op2 = build_ha_groups(hbg, dop2)

    ## op3
    with timeit('opt3 - full groups'):
        op3 = p.build_ha_groups_opt3()

    # op4
    with timeit('opt4 - full groups - BFS from each READ'):
        op4 = p.build_ha_groups_opt4()

    assert compare(hbg, op1, op2)
    assert compare(hbg, op1, op3)
    assert compare(hbg, op1, op4)

    print(f'{"":*^30}')


def simple_test():
    b = HBGBuilder()
    r00 = b.add_instruction_node('READ', 0, 0, 0x1000, 8)
    f01 = b.add_instruction_node('FLUSH', 0, 0, 0x1000, 64)
    b.add_epoch_node(0, 0)
    w02 = b.add_instruction_node('WRITE', 0, 0, 0x2000, 8)
    b.add_epoch_node(1, 0)
    f10 = b.add_instruction_node('FLUSH', 1, 0, 0x1000, 64)
    w11 = b.add_instruction_node('WRITE', 1, 0, 0x1000, 8)
    b.add_epoch_node(1, 1)
    w20 = b.add_instruction_node('WRITE', 2, 0, 0x1000, 8)
    b.add_epoch_node(2, 0)
    b.add_happens_before_edge(2, 0, 1, 0)
    b.add_happens_before_edge(1, 1, 0, 0)

    hbg = b.build(False)
    pdg = generate_mock_pdg(hbg)
    p = prd.PersistencyRaceDetector(hbg, pdg)
    fw, fr = p.build_fw_groups_opt2()

    assert w11 not in fw[w02][w11.interval]
    assert w20 in fw[w02][w11.interval]
    assert r00 in fr[w02][w11.interval]


def test2(dbg=True):
    if dbg:
        print(f'{"Test 2":*^30}')
        
    b = HBGBuilder(dbg)
    
    v1 = 0x1000
    v2 = 0x2000
    v3 = 0x3000
    
    w11 = b.add_instruction_node('WRITE', 1, 0, v1, 8, 'w11')
    b.add_instruction_node('FLUSH', 1, 0, v1, 64)
    b.add_epoch_node(1, 0)
    w12 = b.add_instruction_node('WRITE', 1, 0, v1, 8, 'w12')
    b.add_instruction_node('FLUSH', 1, 0, v1, 64)
    b.add_epoch_node(1, 1)
    w13 = b.add_instruction_node('WRITE', 1, 0, v2, 8, 'w13')
    
    r21 = b.add_instruction_node('READ', 2, 0, v1, 8, 'r21')
    r22 = b.add_instruction_node('READ', 2, 0, v2, 8, 'r22')
    b.add_instruction_node('FLUSH', 2, 0, v2, 64)
    b.add_epoch_node(2, 0)
    w21 = b.add_instruction_node('WRITE', 2, 0, v1, 8, 'w21')
    b.add_epoch_node(2, 1)
    w22 = b.add_instruction_node('WRITE', 2, 0, v3, 8, 'w22')
    b.add_epoch_node(2, 2)
    w23 = b.add_instruction_node('WRITE', 2, 0, v2, 8, 'w23')
    
    w31 = b.add_instruction_node('WRITE', 3, 0, v1, 8, 'w31')
    w32 = b.add_instruction_node('WRITE', 3, 0, v2, 8, 'w32')
    b.add_instruction_node('FLUSH', 3, 0, v1, 64)
    b.add_epoch_node(3, 0)
    b.add_epoch_node(3, 1)
    w33 = b.add_instruction_node('WRITE', 3, 0, v1, 8, 'w33')
    b.add_instruction_node('FLUSH', 3, 0, v3, 64)
    
    b.add_happens_before_edge(1, 0, 2, 1)
    b.add_happens_before_edge(1, 1, 2, 2)
    b.add_happens_before_edge(2, 0, 1, 1)
    b.add_happens_before_edge(2, 0, 3, 1)
    b.add_happens_before_edge(3, 0, 2, 0)
    
    hbg = b.build()
    pdg = generate_mock_pdg(hbg)
    p = prd.PersistencyRaceDetector(hbg, pdg)
    
    delta_ha_groups = p.build_delta_ha_groups_opt1()
    delta_fw_groups, delta_fr_groups = p.build_delta_fw_groups_opt0()
    races = list(p.finale(delta_ha_groups, delta_fw_groups, delta_fr_groups))
        
    if dbg:
        print(p.races_to_str())
    
    assert len(races) == 1
    race, = races
    assert race.read_node == r21
    assert race.write_node == w22


def test3(dbg=True):
    if dbg:
        print(f'{"Test 3":*^30}')
        
    b = HBGBuilder(dbg)
    
    X = 0x1000
    Y = 0x2000
    Z = 0x3000
    
    w11 = b.add_instruction_node('WRITE', 1, 0, Z, 8, 'w11')
    w12 = b.add_instruction_node('WRITE', 1, 0, X, 8, 'w12')
    b.add_epoch_node(1, 0)
    b.add_instruction_node('FLUSH', 1, 0, X, 64)
    b.add_epoch_node(1, 1)
    w13 = b.add_instruction_node('WRITE', 1, 0, X, 8, 'w13')
    
    r21 = b.add_instruction_node('READ', 2, 0, X, 8, 'r21')
    r22 = b.add_instruction_node('READ', 2, 0, Z, 8, 'r22')
    b.add_instruction_node('FLUSH', 2, 0, Z, 64)
    b.add_epoch_node(2, 0)
    w21 = b.add_instruction_node('WRITE', 2, 0, Y, 8, 'w21')
    
    w31 = b.add_instruction_node('WRITE', 3, 0, X, 8, 'w31')
    b.add_instruction_node('FLUSH', 3, 0, X, 64)
    b.add_epoch_node(3, 0)
    w32 = b.add_instruction_node('WRITE', 3, 0, X, 8, 'w32')
    r31 = b.add_instruction_node('READ', 3, 0, Y, 8, 'r31')
    w33 = b.add_instruction_node('WRITE', 3, 0, Z, 8, 'w33')
    
    b.add_happens_before_edge(1, 0, 2, 0)
    b.add_happens_before_edge(2, 0, 1, 1)
    b.add_happens_before_edge(3, 0, 2, 0)
    
    hbg = b.build(False)
    pdg = generate_mock_pdg(hbg)
    p = prd.PersistencyRaceDetector(hbg, pdg)
    
    delta_ha_groups = p.build_delta_ha_groups_opt1()
    delta_fw_groups, delta_fr_groups = p.build_delta_fw_groups_opt0()
    races = list(p.finale(delta_ha_groups, delta_fw_groups, delta_fr_groups))
        
    if dbg:
        print(p.races_to_str())
    
    assert len(races) == 2
    
    races = {r.tid: r for r in races}
    
    assert races[2].read_node == r21
    assert races[2].write_node == w21
    
    assert races[3].read_node == r31
    assert races[3].write_node == w33


def main():
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe_2.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe_3.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe_2022-10-12.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe_2022-10-13.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-10-17_14-40\test_recipe_2022-10-17_10000-8.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-10-17-16-49\trace.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-10-17-21-15-gc\trace.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-10-18-02-29\trace.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-10-18-20-30\trace.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-10-19-00-16\trace.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-10-20-01-16\trace.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-10-20-01-16\trace.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-11-04\trace.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-11-30\trace.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\real_tests\2022-12-16\trace.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\tests\traces\trace.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\tests\traces\trace2.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\pyprd\tests\traces\trace3.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_out_small.txt')
    # trace = TraceParser.from_file(r'H:\Home\Technion\Projects\Repos\RECIPE\P-CLHT\build\test_recipe_4.txt')


    # Simple test
    with timeit('simple_test'):
        simple_test()

    # HBG
    with timeit('hbg'):
        # hbg = trace.to_hbg(max_lines=10000)
        # hbg = trace.to_hbg(max_lines=100000)
        # hbg = trace.to_hbg(max_lines=500000)
        # hbg = trace.to_hbg(max_lines=1000000)
        # hbg = trace.to_hbg(max_lines=1400000)
        hbg = trace.to_hbg()

    with timeit('hbg stats'):
        print(hbg.stats())

    
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
        
    with open('races.txt', 'w') as f:
        f.write('\n----------\n'.join(map(str, races)))
    
    with open('races_summary.txt', 'w') as f:
        f.write(p.races_to_str())
    
    with timeit('save all'):
        serializer.save(hbg=hbg, pdg=pdg, p=p)
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
