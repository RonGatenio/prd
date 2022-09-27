from typing import Dict
import networkx as nx
from enum import Enum
import nodes


class EdgeType(Enum):
    INTER_THREAD = 'inter-thread'
    INTRA_THREAD = 'intra-thread'


class HBG(nx.DiGraph):
    def __post_init__(self):
        self._node_by_type = {itype: nx.get_node_attributes(self, itype) for itype in nodes.NodeType}
        assert sum(map(len, self._node_by_type.values())) == len(self)
        
        self._inter_graph = nx.subgraph_view(self, filter_edge=lambda u, v: self[u][v]['type'] == EdgeType.INTER_THREAD)
        self._intra_graph = nx.subgraph_view(self, filter_edge=lambda u, v: self[u][v]['type'] == EdgeType.INTRA_THREAD)
        
        self._tids = list(nx.get_node_attributes(self, 'tid').values())
        self._thread_graphs = {tid: nx.get_node_attributes(self, f'tid_{tid}') for tid in self._tids}
        
        return self
        
    @property
    def inter(self):
        return self._inter_graph
    
    @property
    def intra(self):
        return self._intra_graph
    
    @property
    def tids(self):
        return self._tids
    
    def get_thread_subgraph(self, tid):
        return self._thread_graphs[tid]
    
    def get_nodes_by_type(self, itype: nodes.NodeType):
        return self._node_by_type[itype]
    
    def get_write_nodes(self):
        return self.get_nodes_by_type(nodes.NodeType.WRITE)
    
    def get_read_nodes(self):
        return self.get_nodes_by_type(nodes.NodeType.READ)
    
    def get_flush_nodes(self):
        return self.get_nodes_by_type(nodes.NodeType.FLUSH)
