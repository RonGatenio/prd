from contextlib import contextmanager
import dill as pickle
# import pickle
from typing import Any, Dict, Set, Tuple
from hbg_trace_parser import TraceParser
from pdg import generate_mock_pdg
from hbg import HBG, HBGBuilder
import time
import networkx as nx
import nodes
import prd


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

    assert compare(hbg, fw_op0, fw_op1)
    assert compare(hbg, fw_op0, fw_op2)
    assert compare(hbg, fr_op0, fr_op1)
    assert compare(hbg, fr_op0, fr_op2)

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


def main():
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe_2.txt')
    trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_recipe_3.txt')
    # trace = TraceParser.from_file(r'H:\Projects\LLVM\llvm-project\py_persistency_race_detector\tests\traces\real\test_out_small.txt')
    # trace = TraceParser.from_file(r'H:\Home\Technion\Projects\Repos\RECIPE\P-CLHT\build\test_recipe_4.txt')


    # Simple test
    with timeit('simple_test'):
        simple_test()

    # HBG
    with timeit('hbg'):
        hbg = trace.to_hbg(max_lines=10000)
        # hbg = trace.to_hbg()

    with timeit('hbg stats'):
        print(hbg.stats())

    # PDG
    with timeit('pdg'):
        pdg = generate_mock_pdg(hbg)
    
    # PRD
    p = prd.PersistencyRaceDetector(hbg, pdg)
    
    with timeit('ha delta groups'):
        delta_ha_groups = p.build_delta_ha_groups_opt1()
    
    with timeit('fw fr delta groups'):
        delta_fw_groups, delta_fr_groups = p.build_delta_fw_groups_opt0()

    print()
    fw_fr_tests(p)

    print()
    ha_tests(p)


if __name__ == "__main__":
    main()
