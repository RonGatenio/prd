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
