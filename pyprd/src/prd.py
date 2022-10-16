from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Set, Tuple
import nodes
from hbg import HBG
from pdg import PDG
import networkx as nx
import utils


class PersistencyRace:
    def __init__(self, write_node: nodes.InstructionNode, read_node: nodes.InstructionNode):
        self._write_node = write_node
        self._read_node = read_node
        
        assert self.read_node.interval != self.write_node.interval
        assert self.read_node.tid == self.write_node.tid

    @property
    def write_node(self):
        return self._write_node

    @property
    def read_node(self):
        return self._read_node
    
    @property
    def tid(self):
        return self._read_node.tid

    def __str__(self) -> str:
        space = 14
        s = []
        s.append('PERSISTENCY RACE!')
        s.append(f'{"Write Node: ":{space}}{self.write_node}')
        s.append(f'{"Read Node: ":{space}}{self.read_node}')
        return '\n\t'.join(s)


ThreadId = int
Var = Tuple[int, int]
ReadNode = nodes.InstructionNode
WriteNode = nodes.InstructionNode

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


# class NodeContext:
#     def __init__(self):
#         self._last_read_node: Dict[ThreadId, nodes.InstructionNode] = {}



class PersistencyRaceDetector:
    def __init__(self, hbg: HBG, ppdg: PDG):
        self._hbg = hbg
        self._ppdg = ppdg
        
    @property
    def hbg(self):
        return self._hbg
    
    @property
    def ppdg(self):
        return self._ppdg

    def build_delta_ha_groups_opt1(self):
        ReadNode = nodes.InstructionNode
        WriteNode = nodes.InstructionNode
        NodeContextType = Dict[ThreadId, ReadNode]
        last_read_nodes_storage: Dict[nodes.EpochNode, NodeContextType] = defaultdict(dict)
        last_read_nodes_current: Dict[ThreadId, NodeContextType] = defaultdict(dict)
        delta_ha_groups: Dict[ReadNode, Dict[Var, Set[WriteNode]]] = defaultdict(lambda: defaultdict(set))

        for n in self._hbg.reverse_postorder():
            if n.itype == nodes.NodeType.READ:
                last_read_nodes_current[n.tid][n.tid] = n

            elif n.itype == nodes.NodeType.WRITE:
                n: nodes.InstructionNode

                for tid in self._hbg.tids:
                    last_read_node = last_read_nodes_current[n.tid].get(tid)
                    if last_read_node:
                        delta_ha_groups[last_read_node][n.interval].add(n)

            elif n.itype == nodes.NodeType.EPOCH:
                n: nodes.EpochNode

                for parent in self._hbg.get_inter_parents(n):
                    assert isinstance(parent, nodes.EpochNode)

                    parent: nodes.EpochNode

                    for tid in self._hbg.tids:
                        n1 = last_read_nodes_current[n.tid].get(tid)
                        n2 = last_read_nodes_storage[parent].get(tid)
                        if n2 and (not n1 or self._hbg.is_before_in_thread(n1, n2)):
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


    def build_delta_fw_groups_opt00(self):
        ReadNode = nodes.InstructionNode
        WriteNode = nodes.InstructionNode
        
        hbg = self._hbg
        
        class SearchContext:
            def __init__(self):
                self._last_found_write: Dict[ThreadId, WriteNode] = {}  # last found write instruction node in the thread
                self._last_found_write_before_flush: Dict[ThreadId, Dict[int, WriteNode]] = {}  # last write from thread i that was found before the last flush(Var)
                
                for tid in hbg.tids:
                    self._last_found_write_before_flush.setdefault(tid, {})
            
            def add_node(self,
                         node: nodes.InstructionNode,
                         delta_fw_group: Dict[WriteNode, Dict[int, Set[WriteNode]]],
                         delta_fr_group: Dict[WriteNode, Dict[int, Set[ReadNode]]]):
                if node.itype == nodes.NodeType.WRITE:
                    self._last_found_write[node.tid] = node
                    
                if node.itype == nodes.NodeType.WRITE:
                    cacheline_address = utils.get_cacheline_address(node.address, hbg.cacheline_size)
                    for tid in hbg.tids:
                        other_node = self._last_found_write_before_flush[tid].get(cacheline_address)
                        if other_node:
                            delta_fw_group.setdefault(other_node, {}).setdefault(cacheline_address, set()).add(node)
                    
                elif node.itype == nodes.NodeType.READ:
                    cacheline_address = utils.get_cacheline_address(node.address, hbg.cacheline_size)
                    for tid in hbg.tids:
                        other_node = self._last_found_write_before_flush[tid].get(cacheline_address)
                        if other_node:
                            delta_fr_group.setdefault(other_node, {}).setdefault(cacheline_address, set()).add(node)
                
                elif node.itype == nodes.NodeType.FLUSH:
                    for tid in hbg.tids:
                        if tid not in self._last_found_write:
                            continue
                        self._last_found_write_before_flush[tid][node.address] = self._last_found_write[tid]

            def merge(self, other: 'SearchContext'):
                for tid in hbg.tids:
                    n1 = self._last_found_write.get(tid)
                    n2 = other._last_found_write.get(tid)
                    if n2 and (not n1 or hbg.is_before_in_thread(n2, n1)):
                        self._last_found_write[tid] = n2

                    for var in other._last_found_write_before_flush[tid]:
                        n1 = self._last_found_write_before_flush[tid].get(var)
                        n2 = other._last_found_write_before_flush[tid][var]
                        
                        if n2 and (not n1 or hbg.is_before_in_thread(n2, n1)):
                            self._last_found_write_before_flush[tid][var] = n2
        
        thread_context: Dict[ThreadId, SearchContext] = {}
        node_context: Dict[nodes.EpochNode, SearchContext] = {}
        
        delta_fw_groups: Dict[WriteNode, Dict[int, Set[WriteNode]]] = {}
        delta_fr_groups: Dict[WriteNode, Dict[int, Set[ReadNode]]] = {}
        
        for tid in self._hbg.tids:
            thread_context.setdefault(tid, SearchContext())
        
        for i, n in enumerate(self._hbg.postorder()):
            if isinstance(n, nodes.InstructionNode):
                thread_context[n.tid].add_node(n, delta_fw_groups, delta_fr_groups)
                
            elif isinstance(n, nodes.EpochNode):
                if n in node_context:
                    thread_context[n.tid].merge(node_context[n])
                    del node_context[n]
                    
                for parent in self._hbg.get_inter_parents(n):
                    if parent not in node_context:
                        node_context[parent] = SearchContext()
                    
                    node_context[parent].merge(thread_context[n.tid])
                
        return delta_fw_groups, delta_fr_groups

    def build_delta_fw_groups_opt0(self):
        ReadNode = nodes.InstructionNode
        WriteNode = nodes.InstructionNode
        
        hbg = self._hbg
        
        def _copy(d1: Dict[Any, Dict[Any, Any]]):
            d = {}
            for k, v in d1.items():
                d[k] = v.copy()
            return d
        
        class SearchContext:
            def __init__(self):
                self._last_found_write: Dict[ThreadId, WriteNode] = {}  # last found write instruction node in the thread
                self._last_found_write_before_flush: Dict[ThreadId, Dict[Var, WriteNode]] = {}  # last write from thread i that was found before the last flush(Var)
                
                for tid in hbg.tids:
                    self._last_found_write_before_flush.setdefault(tid, {})
            
            def add_node(self,
                         node: nodes.InstructionNode,
                         delta_fw_group: Dict[WriteNode, Dict[Var, Set[WriteNode]]],
                         delta_fr_group: Dict[WriteNode, Dict[Var, Set[ReadNode]]]):
                if node.itype == nodes.NodeType.WRITE:
                    self._last_found_write[node.tid] = node
                    
                if node.itype == nodes.NodeType.WRITE:
                    for tid in hbg.tids:
                        other_node = self._last_found_write_before_flush[tid].get(node.interval)
                        if other_node:
                            delta_fw_group.setdefault(other_node, {}).setdefault(node.interval, set()).add(node)
                    
                elif node.itype == nodes.NodeType.READ:
                    for tid in hbg.tids:
                        other_node = self._last_found_write_before_flush[tid].get(node.interval)
                        if other_node:
                            delta_fr_group.setdefault(other_node, {}).setdefault(node.interval, set()).add(node)
                
                elif node.itype == nodes.NodeType.FLUSH:
                    for tid in hbg.tids:
                        if tid not in self._last_found_write:
                            continue
                        for var in hbg.get_vars_in_cacheline(node.address):
                            self._last_found_write_before_flush[tid][var] = self._last_found_write[tid]

            def merge(self, other: 'SearchContext'):
                for tid in hbg.tids:
                    n1 = self._last_found_write.get(tid)
                    n2 = other._last_found_write.get(tid)
                    if n2 and (not n1 or hbg.is_before_in_thread(n2, n1)):
                        self._last_found_write[tid] = n2

                    for var in other._last_found_write_before_flush[tid]:
                        n1 = self._last_found_write_before_flush[tid].get(var)
                        n2 = other._last_found_write_before_flush[tid][var]
                        
                        if n2 and (not n1 or hbg.is_before_in_thread(n2, n1)):
                            self._last_found_write_before_flush[tid][var] = n2
            
            def copy(self) -> 'SearchContext':
                s = SearchContext()
                s._last_found_write = self._last_found_write.copy()
                s._last_found_write_before_flush = _copy(self._last_found_write_before_flush)
                return s
        
        thread_context: Dict[ThreadId, SearchContext] = {}
        node_context: Dict[nodes.EpochNode, SearchContext] = {}
        
        delta_fw_groups: Dict[WriteNode, Dict[Var, Set[WriteNode]]] = {}
        delta_fr_groups: Dict[WriteNode, Dict[Var, Set[ReadNode]]] = {}
        
        for tid in self._hbg.tids:
            thread_context.setdefault(tid, SearchContext())
        
        for n in self._hbg.postorder():
            if isinstance(n, nodes.InstructionNode):
                thread_context[n.tid].add_node(n, delta_fw_groups, delta_fr_groups)
                
            elif isinstance(n, nodes.EpochNode):
                if n in node_context:
                    thread_context[n.tid].merge(node_context[n])
                    del node_context[n]
                    
                for parent in self._hbg.get_inter_parents(n):
                    if parent not in node_context:
                        node_context[parent] = SearchContext()
                    
                    node_context[parent].merge(thread_context[n.tid])
                
        return delta_fw_groups, delta_fr_groups
    
    def build_delta_fw_groups_opt1(self):
        ReadNode = nodes.InstructionNode
        WriteNode = nodes.InstructionNode
        
        hbg = self._hbg
        
        def _copy(d1: Dict[Any, Dict[Any, Any]]):
            d = {}
            for k, v in d1.items():
                d[k] = v.copy()
            return d
        
        class SearchContext:
            def __init__(self):
                self._last_found_write: Dict[ThreadId, WriteNode] = {}  # last found write instruction node in the thread
                self._last_found_write_before_flush: Dict[ThreadId, Dict[Var, WriteNode]] = {}  # last write from thread i that was found before the last flush(Var)
                
                for tid in hbg.tids:
                    self._last_found_write_before_flush.setdefault(tid, {})
            
            def add_node(self,
                         node: nodes.InstructionNode,
                         delta_fw_group: Dict[WriteNode, Dict[Var, Set[WriteNode]]],
                         delta_fr_group: Dict[WriteNode, Dict[Var, Set[ReadNode]]]):
                if node.itype == nodes.NodeType.WRITE:
                    self._last_found_write[node.tid] = node
                    
                if node.itype == nodes.NodeType.WRITE:
                    for tid in hbg.tids:
                        other_node = self._last_found_write_before_flush[tid].get(node.interval)
                        if other_node:
                            delta_fw_group.setdefault(other_node, {}).setdefault(node.interval, set()).add(node)
                    
                elif node.itype == nodes.NodeType.READ:
                    for tid in hbg.tids:
                        other_node = self._last_found_write_before_flush[tid].get(node.interval)
                        if other_node:
                            delta_fr_group.setdefault(other_node, {}).setdefault(node.interval, set()).add(node)
                
                elif node.itype == nodes.NodeType.FLUSH:
                    for tid in hbg.tids:
                        if tid not in self._last_found_write:
                            continue
                        for var in hbg.get_vars_in_cacheline(node.address):
                            self._last_found_write_before_flush[tid][var] = self._last_found_write[tid]

            def merge(self, other: 'SearchContext'):
                for tid in hbg.tids:
                    n1 = self._last_found_write.get(tid)
                    n2 = other._last_found_write.get(tid)
                    if n2 and (not n1 or hbg.is_before_in_thread(n2, n1)):
                        self._last_found_write[tid] = n2

                    for var in other._last_found_write_before_flush[tid]:
                        n1 = self._last_found_write_before_flush[tid].get(var)
                        n2 = other._last_found_write_before_flush[tid][var]
                        
                        if n2 and (not n1 or hbg.is_before_in_thread(n2, n1)):
                            self._last_found_write_before_flush[tid][var] = n2
            
            def copy(self) -> 'SearchContext':
                s = SearchContext()
                s._last_found_write = self._last_found_write.copy()
                s._last_found_write_before_flush = _copy(self._last_found_write_before_flush)
                return s
        
        thread_context: Dict[ThreadId, SearchContext] = {}
        node_context: Dict[nodes.EpochNode, SearchContext] = {}
        
        delta_fw_groups: Dict[WriteNode, Dict[Var, Set[WriteNode]]] = {}
        delta_fr_groups: Dict[WriteNode, Dict[Var, Set[ReadNode]]] = {}
        
        for tid in self._hbg.tids:
            thread_context.setdefault(tid, SearchContext())
        
        for n in self._hbg.postorder():
            if isinstance(n, nodes.InstructionNode):
                thread_context[n.tid].add_node(n, delta_fw_groups, delta_fr_groups)
                
            elif isinstance(n, nodes.EpochNode):
                for child in self._hbg.get_inter_children(n):
                    thread_context[n.tid].merge(node_context[child])
                    
                node_context[n] = thread_context[n.tid].copy()
                
        return delta_fw_groups, delta_fr_groups

    def build_fw_groups_opt2(self):
        ReadNode = nodes.InstructionNode
        WriteNode = nodes.InstructionNode
        
        hbg = self._hbg
        
        def _copy(d1: Dict[Any, Set[Any]]):
            d = {}
            for k, v in d1.items():
                d[k] = v.copy()
            return d
        
        class SearchContext:
            def __init__(self):
                self._unflushed_writes: Dict[Var, Set[WriteNode]] = {}
                self._flushed_writes: Dict[Var, Set[WriteNode]] = {}
                self._unflushed_reads: Dict[Var, Set[ReadNode]] = {}
                self._flushed_reads: Dict[Var, Set[ReadNode]] = {}
                
            def copy_flushed_reads(self):
                return _copy(self._flushed_reads)
            
            def copy_flushed_writes(self):
                return _copy(self._flushed_writes)
                
            def add_node(self, node: nodes.InstructionNode):
                if node.itype == nodes.NodeType.READ:
                    self._unflushed_reads.setdefault(node.interval, set()).add(node)
                elif node.itype == nodes.NodeType.WRITE:
                    self._unflushed_writes.setdefault(node.interval, set()).add(node)
                elif node.itype == nodes.NodeType.FLUSH:
                    for var in hbg.get_vars_in_cacheline(node.address):
                        if var in self._unflushed_reads:
                            self._flushed_reads[var] = self._unflushed_reads[var]
                            self._unflushed_reads[var] = set()
                        if var in self._unflushed_writes:
                            self._flushed_writes[var] = self._unflushed_writes[var]
                            self._unflushed_writes[var] = set()
                            
            def copy(self) -> 'SearchContext':
                s = SearchContext()
                s._unflushed_reads = _copy(self._unflushed_reads)
                s._flushed_reads = _copy(self._flushed_reads)
                s._unflushed_writes = _copy(self._unflushed_writes)
                s._flushed_writes = _copy(self._flushed_writes)
                return s
            
            def merge(self, other: 'SearchContext'):
                def _merge(d1: Dict[Any, Set[Any]], d2: Dict[Any, Set[Any]]):
                    for k, v in d2.items():
                        d1.setdefault(k, set()).update(v)
                
                def _sub(d1: Dict[Any, Set[Any]], d2: Dict[Any, Set[Any]]):
                    for k, v in d2.items():
                        d1.setdefault(k, set()).difference_update(v)
                
                _merge(self._unflushed_writes, other._unflushed_writes)
                _sub(self._unflushed_writes, other._flushed_writes)
                
                _merge(self._flushed_writes, other._flushed_writes)
                
                _merge(self._unflushed_reads, other._unflushed_reads)
                _sub(self._unflushed_reads, other._flushed_reads)
                
                _merge(self._flushed_reads, other._flushed_reads)
                
        thread_context: Dict[ThreadId, SearchContext] = {}
        node_context: Dict[nodes.EpochNode, SearchContext] = {}
        
        fw_groups: Dict[WriteNode, Dict[Var, Set[WriteNode]]] = {}
        fr_groups: Dict[WriteNode, Dict[Var, Set[ReadNode]]] = {}
        
        for tid in self._hbg.tids:
            thread_context.setdefault(tid, SearchContext())
        
        for n in self._hbg.reverse_postorder():
            if isinstance(n, nodes.InstructionNode):
                thread_context[n.tid].add_node(n)
                
                if n.itype == nodes.NodeType.WRITE:
                    fw_groups[n] = thread_context[n.tid].copy_flushed_writes()
                    fr_groups[n] = thread_context[n.tid].copy_flushed_reads()
            
            elif isinstance(n, nodes.EpochNode):
                for parent in self._hbg.get_inter_parents(n):
                    thread_context[n.tid].merge(node_context[parent])
                    
                node_context[n] = thread_context[n.tid].copy()
                
        return fw_groups, fr_groups

    def build_delta_fw_groups_opt3(self):
        ReadNode = nodes.InstructionNode
        WriteNode = nodes.InstructionNode
        
        hbg = self._hbg
        
        def _copy(d1: Dict[Any, Dict[Any, Any]]):
            d = {}
            for k, v in d1.items():
                d[k] = v.copy()
            return d
        
        unfound_nodes: Dict[Var, Set[nodes.InstructionNode]] = _copy(self._hbg.nodes_by_var)
        
        class SearchContext:
            def __init__(self):
                self._last_found_write: Dict[ThreadId, WriteNode] = {}  # last found write instruction node in the thread
                self._last_found_write_before_flush: Dict[ThreadId, Dict[Var, WriteNode]] = {}  # last write from thread i that was found before the last flush(Var)
                
                for tid in hbg.tids:
                    self._last_found_write_before_flush.setdefault(tid, {})
            
            def add_node(self,
                         node: nodes.InstructionNode,
                         delta_fw_group: Dict[WriteNode, Dict[Var, Set[WriteNode]]],
                         delta_fr_group: Dict[WriteNode, Dict[Var, Set[ReadNode]]]):
                if node.itype == nodes.NodeType.WRITE:
                    self._last_found_write[node.tid] = node
                    
                if node.itype == nodes.NodeType.WRITE:
                    for tid in hbg.tids:
                        other_node = self._last_found_write_before_flush[tid].get(node.interval)
                        if other_node:
                            delta_fw_group.setdefault(other_node, {}).setdefault(node.interval, set()).add(node)
                    
                elif node.itype == nodes.NodeType.READ:
                    for tid in hbg.tids:
                        other_node = self._last_found_write_before_flush[tid].get(node.interval)
                        if other_node:
                            delta_fr_group.setdefault(other_node, {}).setdefault(node.interval, set()).add(node)
                
                elif node.itype == nodes.NodeType.FLUSH:
                    for tid in hbg.tids:
                        if tid not in self._last_found_write:
                            continue
                        for var in hbg.get_vars_in_cacheline(node.address):
                            self._last_found_write_before_flush[tid][var] = self._last_found_write[tid]

            def merge(self, other: 'SearchContext'):
                for tid in hbg.tids:
                    n1 = self._last_found_write.get(tid)
                    n2 = other._last_found_write.get(tid)
                    if n2 and (not n1 or hbg.is_before_in_thread(n2, n1)):
                        self._last_found_write[tid] = n2

                    vars_to_remove = set()
                    
                    for var in other._last_found_write_before_flush[tid]:
                        # if there are no unfound nodes for this var, ignore it
                        if not unfound_nodes.get(var):
                            vars_to_remove.add(var)
                            continue
                        
                        n1 = self._last_found_write_before_flush[tid].get(var)
                        n2 = other._last_found_write_before_flush[tid][var]
                        
                        if n2 and (not n1 or hbg.is_before_in_thread(n2, n1)):
                            self._last_found_write_before_flush[tid][var] = n2
                            
                    for var in vars_to_remove:
                        for _tid in other._last_found_write_before_flush:
                            if var in other._last_found_write_before_flush[_tid]:
                                del other._last_found_write_before_flush[_tid][var]
            
            def copy(self) -> 'SearchContext':
                s = SearchContext()
                s._last_found_write = self._last_found_write.copy()
                s._last_found_write_before_flush = _copy(self._last_found_write_before_flush)
                return s
        
        thread_context: Dict[ThreadId, SearchContext] = {}
        node_context: Dict[nodes.EpochNode, SearchContext] = {}
        
        delta_fw_groups: Dict[WriteNode, Dict[Var, Set[WriteNode]]] = {}
        delta_fr_groups: Dict[WriteNode, Dict[Var, Set[ReadNode]]] = {}
        
        for tid in self._hbg.tids:
            thread_context.setdefault(tid, SearchContext())
        
        for n in self._hbg.postorder():
            if isinstance(n, nodes.InstructionNode):
                thread_context[n.tid].add_node(n, delta_fw_groups, delta_fr_groups)
                if nodes.NodeType.is_read_write_type(n.itype):
                    unfound_nodes.get(n.interval, set()).remove(n)
                
            elif isinstance(n, nodes.EpochNode):
                if n in node_context:
                    thread_context[n.tid].merge(node_context[n])
                    del node_context[n]
                    
                for parent in self._hbg.get_inter_parents(n):
                    if parent not in node_context:
                        node_context[parent] = SearchContext()
                    
                    node_context[parent].merge(thread_context[n.tid])
                
        return delta_fw_groups, delta_fr_groups
    
    def finale(self,
               delta_ha_groups: Dict[ReadNode,  Dict[Var, Set[WriteNode]]],
               delta_fw_groups: Dict[WriteNode, Dict[Var, Set[WriteNode]]],
               delta_fr_groups: Dict[WriteNode, Dict[Var, Set[ReadNode]]]) -> Generator[PersistencyRace, None, None]:
        
        self._races: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        
        def merge(d1: Dict[Any, Set[Any]], d2: Dict[Any, Set[Any]]):
            for k, v in d2.items():
                d1.setdefault(k, set()).update(v)
                
        def discard(d1: Dict[Any, Set[Any]], d2: Dict[Any, Set[Any]]):
            for k, v in d2.items():
                d1.setdefault(k, set()).difference_update(v)
                
        def copy(d: Dict[Any, Set[Any]]):
            _d = defaultdict(set)
            for k, v in d.items():
                _d[k] = v.copy()
            return _d
                
        for tid in self._hbg.tids:
            ha_groups: Dict[Var, Set[WriteNode]] = defaultdict(set)
            fw_groups: Dict[Var, Set[WriteNode]] = defaultdict(set)
            fr_groups: Dict[Var, Set[ReadNode]]  = defaultdict(set)
            
            # Get thread nodes in order
            thread_nodes = self._hbg.get_thread_nodes(tid)
            
            # Initialize ha group
            for n in filter(lambda n: n.itype == nodes.NodeType.READ, thread_nodes):
                merge(ha_groups, delta_ha_groups.get(n, {}))
            
            # Run over thread nodes in order (top to bottom)
            for i, n in enumerate(thread_nodes):
                if not isinstance(n, nodes.InstructionNode):
                    continue
                
                if n.itype == nodes.NodeType.READ:
                    n: ReadNode
                    
                    temp_fr_group:   Set[ReadNode]  = fr_groups[n.interval].copy()
                    temp_safe_group: Set[WriteNode] = ha_groups[n.interval] | fw_groups[n.interval]
                    
                    dependant_writes = list(self._ppdg.get_dependants(n))
                    
                    # if no depandant writes, no possible races with this read
                    if not dependant_writes:
                        # Update ha_groups
                        discard(ha_groups, delta_ha_groups.get(n, {}))
                        continue
                    
                    locations = list(map(self._hbg.get_node_location, dependant_writes))
                    
                    total_write_nodes_of_var = len(self._hbg.get_write_nodes_by_var(n.interval))
                    
                    for j in range(i, max(locations).tindex + 1):
                        temp_n = thread_nodes[j]
                        
                        if temp_n.itype != nodes.NodeType.WRITE:
                            continue
                        
                        read_node: ReadNode   = n
                        write_node: WriteNode = temp_n
                        
                        # Update fr and safe group
                        temp_fr_group |= delta_fr_groups.get(write_node, {}).get(read_node.interval, set())
                        temp_safe_group |= delta_fw_groups.get(write_node, {}).get(read_node.interval, set())
                        
                        # if not a depandent node, continue, no race here
                        if write_node not in dependant_writes:
                            continue
                        
                        # if var(W) == var(R), continue, there is no race here
                        if write_node.interval == read_node.interval:
                            continue
                        
                        # if the Read node is flushed from this point. No need to continue. No possible races from here
                        if read_node in temp_fr_group:
                            break
                        
                        # if the safe group contains all possible W(var)s, no need to continue. No possible races from here
                        if len(temp_safe_group) == total_write_nodes_of_var:
                            break
                        
                        yield PersistencyRace(write_node, read_node)
                        
                        if not self._races.get(read_node.info, {}).get(write_node.info):
                            violation_nodes = self._hbg.get_write_nodes_by_var(read_node.interval) - temp_safe_group
                            violation_nodes = {v.info for v in violation_nodes}
                            self._races[read_node.info][write_node.info].update(violation_nodes)
                
                    # Update ha_groups
                    discard(ha_groups, delta_ha_groups.get(n, {}))
                
                elif n.itype == nodes.NodeType.WRITE:
                    # Update fw fr groups
                    merge(fw_groups, delta_fw_groups.get(n, {}))
                    merge(fr_groups, delta_fr_groups.get(n, {}))
