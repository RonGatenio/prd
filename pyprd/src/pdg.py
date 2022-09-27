import networkx as nx
from typing import Dict, List, Set, Tuple
from collections import namedtuple
from intervaltree import IntervalTree, Interval
import nodes
from hbg import HBG


class PDG(nx.DiGraph):
    def __post_init__(self):
        return self


class PDGBuilder:
    def __init__(self):
        self._pdg = PDG()
        
    def add_dependency(self, write_node: nodes.InstructionNode, read_node: nodes.InstructionNode):
        assert write_node.itype == nodes.NodeType.WRITE, f'expected a write node but got {write_node.itype}'
        assert read_node.itype == nodes.NodeType.READ, f'expected a read node but got {read_node.itype}'
        assert write_node.tid == read_node.tid, 'expected tids to be the same'
        
        self._pdg.add_edge(write_node, read_node)
        
    def build(self):
        return self._pdg.__post_init__()


def generate_mock_pdg(hbg: HBG, threshold=10):
    """
    Generates a full pdg. every WRITE is dependent of all previous READs in the thread.
    This is a mock!
    """
    pdgbuilder = PDGBuilder()
    
    for tid in hbg.tids:
        read_instruction_nodes = []
        
        for n in hbg.get_thread_nodes(tid):
            n: nodes.AbstractNode
            
            if n.itype == nodes.NodeType.READ:
                read_instruction_nodes.append(n)
                
            elif n.itype == nodes.NodeType.WRITE:
                for read_node in read_instruction_nodes[-threshold:]:
                    pdgbuilder.add_dependency(n, read_node)
    
    return pdgbuilder.build()
