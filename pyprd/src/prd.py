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
    
