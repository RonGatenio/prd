from typing import Dict, List, Set
import networkx as nx
from enum import Enum
import nodes


class EdgeType(Enum):
    INTER_THREAD = 'inter-thread'
    INTRA_THREAD = 'intra-thread'


class HBG(nx.DiGraph):
    def __post_init__(self, nodes_by_tid: Dict[int, List[nodes.AbstractNode]], nodes_by_type: Dict[nodes.NodeType, Set[nodes.AbstractNode]]):
        self._threads = nodes_by_tid
        self._nodes = nodes_by_type
        
        self._inter_graph = nx.subgraph_view(self, filter_edge=lambda u, v: self[u][v]['type'] == EdgeType.INTER_THREAD)
        self._intra_graph = nx.subgraph_view(self, filter_edge=lambda u, v: self[u][v]['type'] == EdgeType.INTRA_THREAD)
        
        return self
        
    @property
    def inter(self):
        return self._inter_graph
    
    @property
    def intra(self):
        return self._intra_graph
    
    @property
    def tids(self):
        return self._threads.keys()
    
    def get_thread_nodes(self, tid):
        return self._threads[tid]
    
    def get_nodes_by_type(self, itype: nodes.NodeType):
        return self._nodes[itype]
    
    def get_write_nodes(self):
        return self.get_nodes_by_type(nodes.NodeType.WRITE)
    
    def get_read_nodes(self):
        return self.get_nodes_by_type(nodes.NodeType.READ)
    
    def get_flush_nodes(self):
        return self.get_nodes_by_type(nodes.NodeType.FLUSH)

class HBGBuilder:
    def __init__(self):
        self._hbg = HBG()
        self._thread_tails: Dict[int, nodes.AbstractNode] = {}
        self._nodes_by_thread: Dict[int, List[nodes.AbstractNode]] = {}
        self._nodes_by_type: Dict[nodes.NodeType, Set[nodes.AbstractNode]] = {}
        self._nodes_location: Dict[nodes.AbstractNode, NodeLocation] = {}
        
    @classmethod
    def from_elements(cls, inodes: Collection[nodes.AbstractNode], hbedges: Collection[Tuple[nodes.AbstractNode, nodes.AbstractNode]]):
        builder = cls()
        
        for n in inodes:
            builder.add_node(n)
            
        for e in hbedges:
            builder.add_happens_before_edge(*e)
            
        return builder
        
    def add_node(self, node: nodes.AbstractNode):
        self._hbg.add_node(node)
        
        self._hbg.nodes[node]['itype'] = node.itype
        self._hbg.nodes[node][node.itype] = True
        
        self._nodes_by_thread.setdefault(node.tid, [])
        self._nodes_location[node] = NodeLocation(node.tid, len(self._nodes_by_thread[node.tid]))
        self._nodes_by_thread[node.tid].append(node)
        self._nodes_by_type.setdefault(node.itype, set()).add(node)
        
        if node.tid in self._thread_tails:
            self._hbg.add_edge(self._thread_tails[node.tid], node, type=EdgeType.INTRA_THREAD)
        
        self._thread_tails[node.tid] = node
        
    def add_happens_before_edge(self, src: nodes.EpochNode, dst: nodes.EpochNode):
        assert src.tid != dst.tid, 'TIDs must be different'
        self._hbg.add_edge(src, dst, type=EdgeType.INTER_THREAD)
        
    def build(self) -> HBG:
        return self._hbg.__post_init__(self._nodes_by_thread, self._nodes_by_type, self._nodes_location)
