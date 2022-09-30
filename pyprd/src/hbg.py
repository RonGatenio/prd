from typing import Collection, Dict, List, Set, Tuple
from collections import namedtuple
from enum import Enum
import networkx as nx
import nodes


class EdgeType(Enum):
    INTER_THREAD = 'inter-thread'
    INTRA_THREAD = 'intra-thread'


NodeLocation = namedtuple('NodeLocation', ['tid', 'tindex'])


class HBG(nx.DiGraph):
    def __post_init__(self,
                      nodes_by_thread: Dict[int, List[nodes.AbstractNode]],
                      nodes_by_type: Dict[nodes.NodeType, Set[nodes.AbstractNode]],
                      nodes_location: Dict[nodes.AbstractNode, NodeLocation]):
        self._nodes_by_thread = nodes_by_thread
        self._nodes_by_type = nodes_by_type
        self._nodes_location = nodes_location
        
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
        return self._nodes_by_thread.keys()
    
    def get_node_by_location(self, location: NodeLocation | Tuple[int, int]):
        location = NodeLocation(*location)
        return self._nodes_by_thread[location.tid][location.tindex]
    
    def get_node_location(self, node: nodes.AbstractNode) -> NodeLocation:
        return self._nodes_location[node]
    
    def get_thread_nodes(self, tid):
        return self._nodes_by_thread[tid]
    
    def get_nodes_by_type(self, itype: nodes.NodeType):
        return self._nodes_by_type[itype]
    
    @property
    def write_nodes(self):
        return self.get_nodes_by_type(nodes.NodeType.WRITE)
    
    @property
    def read_nodes(self):
        return self.get_nodes_by_type(nodes.NodeType.READ)
    
    @property
    def flush_nodes(self):
        return self.get_nodes_by_type(nodes.NodeType.FLUSH)
    
    @property
    def epoch_nodes(self):
        return self.get_nodes_by_type(nodes.NodeType.EPOCH)
    
    @property
    def read_write_nodes(self):
        return self.read_nodes | self.write_nodes
    
    @property
    def instruction_nodes(self):
        return self.read_nodes | self.write_nodes | self.flush_nodes


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
