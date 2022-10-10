from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple
import nodes
from hbg import HBG
from pdg import PDG
import networkx as nx


class PersistencyRace:
    def __init__(self, write_node: nodes.InstructionNode, read_node: nodes.InstructionNode):
        self._write_node = write_node
        self._read_node = read_node

    @property
    def write_node(self):
        return self._write_node

    @property
    def read_node(self):
        return self._read_node

    def is_valid(self):
        return self.read_node.interval != self.write_node.interval

    def __str__(self) -> str:
        space = 14
        s = []
        s.append('PERSISTENCY RACE!')
        s.append(f'{"Write Node: ":{space}}{self.write_node}')
        s.append(f'{"Read Node: ":{space}}{self.read_node}')
        return '\n\t'.join(s)


ThreadId = int
Var = Tuple[int, int]

import intervaltree


# class VarTree:
#     def __init__(self):
#         self._itree = intervaltree.IntervalTree()
#         self._vars = {}

#     # def __get__(self, var):
#     #     # self._itree.
#     #     pass

#     # def __set__(self, var, node):

#     @property
#     def vars(self):
#         return self._vars.keys()

#     def range(self, var: Var):
#         for i in self._itree.envelop(*var):
#             yield (i.begin, i.end)

#     def set(self, var: Var, data: Any):
#         self._vars[var] = data
#         self._itree.addi(*var)

#     def get(self, var: Var, default=None):
#         return self._vars.get(var, default)

#     def set_all(self, var: Var, data: Any):
#         for v in self.range(var):
#             self._vars[v] = data

#     # def add(self, var: Var, data: Any):
#     #     if var not in self._vars:
#     #         self._vars[var] = intervaltree.Interval(*var, data=set())
#     #         self._itree.add(self._vars[var])
#     #     self._vars[var].data.add(data)

#     # def get(self, var: Var):
#     #     a = set()
#     #     for i in self._itree[var[0]:var[1]]:
#     #         i: intervaltree.Interval
#     #         a |= i.data
#     #     return a


# @dataclass
class ThreadContext:
    def __init__(self):
        self.lfw: Dict[ThreadId, nodes.InstructionNode] = {}  # last found write instruction node in the thread
        self.lpw: Dict[ThreadId, Dict[Var, nodes.InstructionNode]] = {}  # last write from thread i that was found before the last flush(Var)
        # self.lpw: Dict[ThreadId, VarTree] = {}  # last write from thread i that was found before the last flush(Var)


class PersistencyRaceDetector:
    def __init__(self, hbg: HBG, ppdg: PDG):
        self._hbg = hbg
        self._ppdg = ppdg
        self._delta_flushed_read_nodes: Dict[nodes.InstructionNode, Dict[Var, Set[nodes.InstructionNode]]] = {}
        self._delta_flushed_write_nodes: Dict[nodes.InstructionNode, Dict[Var, Set[nodes.InstructionNode]]] = {}
        self._thread_contexts: Dict[ThreadId, ThreadContext] = {}

    def build_delta_ha_groups_opt1(self):
        ReadNode = nodes.InstructionNode
        WriteNode = nodes.InstructionNode
        NodeContextType = Dict[ThreadId, ReadNode]
        last_read_nodes_storage: Dict[nodes.EpochNode, NodeContextType] = {}
        last_read_nodes_current: Dict[ThreadId, NodeContextType] = {}
        delta_ha_groups: Dict[ReadNode, Dict[Var, Set[WriteNode]]] = {}

        for n in self._hbg.reverse_postorder():
            if n.itype == nodes.NodeType.READ:
                last_read_nodes_current.setdefault(n.tid, {})[n.tid] = n

            elif n.itype == nodes.NodeType.WRITE:
                n: nodes.InstructionNode

                for tid in self._hbg.tids:
                    last_read_node = last_read_nodes_current.setdefault(n.tid, {}).get(tid)
                    if last_read_node:
                        delta_ha_groups.setdefault(last_read_node, {}).setdefault(n.interval, set()).add(n)

            elif n.itype == nodes.NodeType.EPOCH:
                n: nodes.EpochNode

                for parent in self._hbg.get_inter_parents(n):
                    assert isinstance(parent, nodes.EpochNode)

                    parent: nodes.EpochNode

                    for tid in self._hbg.tids:
                        n1 = last_read_nodes_current.setdefault(n.tid, {}).get(tid)
                        n2 = last_read_nodes_storage[parent].get(tid)
                        if n2 and ((not n1) or self._hbg.is_before_in_thread(n1, n2)):
                            last_read_nodes_current[n.tid][tid] = n2

                last_read_nodes_storage[n] = last_read_nodes_current.get(n.tid, {}).copy()

        return delta_ha_groups

    def build_delta_ha_groups_opt2(self):
        ReadNode = nodes.InstructionNode
        WriteNode = nodes.InstructionNode
        NodeContextType = Dict[Var, Set[WriteNode]]
        found_writes_storage: Dict[nodes.EpochNode, NodeContextType] = {}
        found_writes_prev: Dict[ThreadId, NodeContextType] = {}
        found_writes_current: Dict[ThreadId, NodeContextType] = {}
        delta_ha_groups: Dict[ReadNode, Dict[Var, Set[WriteNode]]] = {}

        def copy(d1: Dict[Any, Set[Any]]):
            d = {}
            for k, v in d1.items():
                d[k] = v.copy()
            return d

        def merge(d1: Dict[Any, Set[Any]], d2: Dict[Any, Set[Any]]):
            for k, v in d2.items():
                d1.setdefault(k, set()).update(v)

        def diff(d1: Dict[Any, Set[Any]], d2: Dict[Any, Set[Any]]) -> Dict[Any, Set[Any]]:
            d = {}
            for k, v in d1.items():
                d[k] = v - d2.get(k, set())
            return d

        for n in self._hbg.postorder():
            found_writes_current.setdefault(n.tid, {})

            if n.itype == nodes.NodeType.WRITE:
                n: WriteNode
                found_writes_current[n.tid].setdefault(n.interval, set()).add(n)

            elif n.itype == nodes.NodeType.READ:
                n: ReadNode

                delta_ha_groups[n] = diff(found_writes_current[n.tid], found_writes_prev.get(n.tid, {}))
                found_writes_prev[n.tid] = copy(found_writes_current[n.tid])

            elif n.itype == nodes.NodeType.EPOCH:
                n: nodes.EpochNode
                for child in self._hbg.get_inter_children(n):
                    merge(found_writes_current[n.tid], found_writes_storage[child])

                found_writes_storage[n] = copy(found_writes_current[n.tid])

        return delta_ha_groups

    def build_ha_groups_opt3(self):
        ReadNode = nodes.InstructionNode
        WriteNode = nodes.InstructionNode
        NodeContextType = Dict[Var, Set[WriteNode]]
        found_writes_storage: Dict[nodes.EpochNode, NodeContextType] = {}
        found_writes_current: Dict[ThreadId, NodeContextType] = {}
        ha_groups: Dict[ReadNode, Dict[Var, Set[WriteNode]]] = {}

        def copy(d1: Dict[Any, Set[Any]]):
            d = {}
            for k, v in d1.items():
                d[k] = v.copy()
            return d

        def merge(d1: Dict[Any, Set[Any]], d2: Dict[Any, Set[Any]]):
            for k, v in d2.items():
                d1.setdefault(k, set()).update(v)

        for n in self._hbg.postorder():
            found_writes_current.setdefault(n.tid, {})

            if n.itype == nodes.NodeType.WRITE:
                n: WriteNode
                found_writes_current[n.tid].setdefault(n.interval, set()).add(n)

            elif n.itype == nodes.NodeType.READ:
                n: ReadNode
                ha_groups[n] = copy(found_writes_current[n.tid])

            elif n.itype == nodes.NodeType.EPOCH:
                n: nodes.EpochNode
                for child in self._hbg.get_inter_children(n):
                    merge(found_writes_current[n.tid], found_writes_storage[child])

                found_writes_storage[n] = copy(found_writes_current[n.tid])

        return ha_groups

    def build_ha_groups_opt4(self):
        ReadNode = nodes.InstructionNode
        WriteNode = nodes.InstructionNode
        ha_groups: Dict[ReadNode, Dict[Var, Set[WriteNode]]] = {}

        for r in self._hbg.read_nodes:
            ha_groups[r] = {}
            for n in nx.dfs_postorder_nodes(self._hbg._graph, r):
                if n.itype != nodes.NodeType.WRITE:
                    continue

                ha_groups[r].setdefault(n.interval, set()).add(n)

        return ha_groups


    def build_delta_fw_groups_opt1(self):
        pass

    def build_delta_fw_groups_opt2(self):
        pass

    def part_1(self):
        """Find delta groups"""
        thread_contexts = self._thread_contexts

        for t in self._hbg.tids:
            thread_contexts.setdefault(t, ThreadContext())
            for _t in self._hbg.tids:
                thread_contexts[t].lpw.setdefault(_t, {})

        for n in nx.dfs_postorder_nodes(self._hbg):
            n: nodes.AbstractNode
            tid = n.tid

            if isinstance(n, nodes.InstructionNode):
                if n.itype == nodes.NodeType.WRITE:
                    thread_contexts[tid].lfw[tid] = n

                var = n.interval

                for t in self._hbg.tids:
                    if n.itype == nodes.NodeType.WRITE:
                        node = thread_contexts[tid].lpw[t].get(var)
                        if node:
                            self._delta_flushed_write_nodes.setdefault(node, {}).setdefault(var, set()).add(n)

                    elif n.itype == nodes.NodeType.READ:
                        node = thread_contexts[tid].lpw[t].get(var)
                        if node:
                            self._delta_flushed_read_nodes.setdefault(node, {}).setdefault(var, set()).add(n)

                    elif n.itype == nodes.NodeType.FLUSH:
                        if not thread_contexts[tid].lfw.get(t):
                            continue
                        for _var in self._hbg.get_vars_in_cache_line(var):
                            thread_contexts[tid].lpw[t][_var] = thread_contexts[tid].lfw.get(t)

            elif isinstance(n, nodes.EpochNode):
                def is_before(n1: nodes.AbstractNode, n2: nodes.AbstractNode):
                    if not n1 or not n2:
                        return False
                    assert n1.tid == n2.tid
                    return self._hbg.get_node_location(n1).tindex < self._hbg.get_node_location(n2).tindex

                for c in self._hbg.get_inter_children(n):
                    for t in self._hbg.tids:
                        n1 = thread_contexts[c.tid].lfw.get(t)
                        n2 = thread_contexts[tid].lfw.get(t)
                        if is_before(n1, n2):
                            thread_contexts[tid].lfw[t] = thread_contexts[c.tid].lfw.get(t)

                        for var in thread_contexts[c.tid].lpw[t].keys():
                            n1 = thread_contexts[c.tid].lpw[t].get(var)
                            n2 = thread_contexts[tid].lpw[t].get(var)
                            if is_before(n1, n2):
                                thread_contexts[tid].lpw[t][var] = thread_contexts[c.tid].lpw[t].get(var)

    # def run(self):
    #     self._first_iteration()
    #     self._second_iteration()
    #     return self._third_iteration()
