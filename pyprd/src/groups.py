from typing import Tuple, Dict, Set, Any
from hbg import HBG
import nodes


ReadNode = WriteNode = nodes.InstructionNode
Var = Tuple[int, int]


def merge(d1: Dict[Any, Set[Any]], d2: Dict[Any, Set[Any]]):
    for k, v in d2.items():
        d1.setdefault(k, set()).update(v)


def compare(hbg: HBG, d1: Dict[ReadNode, Dict[Var, Set[WriteNode]]], d2: Dict[ReadNode, Dict[Var, Set[WriteNode]]]):
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


def copy(d1: Dict[Any, Set[Any]]):
    d = {}
    for k, v in d1.items():
        d[k] = v.copy()
    return d


def build_ha_groups_per_node(hbg: HBG, delta_ha_groups: Dict[ReadNode, Dict[Var, Set[WriteNode]]]):
    ha_groups: Dict[ReadNode, Dict[Var, Set[WriteNode]]] = {}

    for tid in hbg.tids:
        thread_nodes = hbg.get_thread_nodes(tid)
        prev: Dict[Var, Set[WriteNode]] = {}

        for n in reversed(thread_nodes):
            if n.itype != 'READ':
                continue
            merge(prev, delta_ha_groups.get(n, {}))
            ha_groups[n] = copy(prev)

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


def build_fwr_groups_per_node(hbg: HBG, delta_fwr_groups: Dict[WriteNode, Dict[Var, Set[nodes.InstructionNode]]]):
    fwr_groups: Dict[WriteNode, Dict[Var, Set[nodes.InstructionNode]]] = {}

    for tid in hbg.tids:
        thread_nodes = hbg.get_thread_nodes(tid)
        prev: Dict[WriteNode, Dict[Var, Set[nodes.InstructionNode]]] = {}

        for n in thread_nodes:
            if n.itype != 'WRITE':
                continue
            merge(prev, delta_fwr_groups.get(n, {}))
            fwr_groups[n] = copy(prev)

    return fwr_groups
