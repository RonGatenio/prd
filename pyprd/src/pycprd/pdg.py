from collections import defaultdict
import networkx as nx
from typing import Iterable
from . import nodes
from .hbg import HBG


class PDG:
    def __init__(self, base_graph: nx.DiGraph):
        self._graph = base_graph

    def get_dependencies(self, write_node: nodes.InstructionNode) -> Iterable[nodes.InstructionNode]:
        if write_node not in self._graph:
            return set()
        return self._graph.neighbors(write_node)

    def get_dependants(self, read_node: nodes.InstructionNode) -> Iterable[nodes.InstructionNode]:
        if read_node not in self._graph:
            return set()
        return self._graph.predecessors(read_node)


class PDGBuilder:
    def __init__(self):
        self._graph = nx.DiGraph()
        self._dependencies: dict[int, set[int]] = defaultdict(set)
        self._total_dependencies = 0
        
    @property
    def total_dependencies(self):
        return self._total_dependencies

    def add_dependency(self, write_node: nodes.InstructionNode, read_node: nodes.InstructionNode):
        assert write_node.itype == nodes.NodeType.WRITE, f'expected a write node but got {write_node.itype}'
        assert read_node.itype == nodes.NodeType.READ, f'expected a read node but got {read_node.itype}'
        assert write_node.tid == read_node.tid, 'expected tids to be the same'

        self._graph.add_edge(write_node, read_node)
        self._total_dependencies += 1
        
    def add_dependency_pc(self, write_node_pc: int, read_node_pc: int):
        self._dependencies[write_node_pc].add(read_node_pc)
        self._total_dependencies += 1

    def build(self, hbg: HBG = None):
        if self._dependencies:
            assert hbg, 'There are PC based dependencies, HBG is required'

            for tid in hbg.tids:
                pending_reads = defaultdict(set)
                
                for n in hbg.get_thread_nodes(tid):
                    n: nodes.AbstractNode
                    
                    if n.itype == nodes.NodeType.READ:
                        n: nodes.ReadNode
                        pending_reads[n.pc].add(n)

                    elif n.itype == nodes.NodeType.WRITE:
                        n: nodes.WriteNode
                        for read_pc in self._dependencies[n.pc]:
                            for read_node in pending_reads[read_pc]:
                                self.add_dependency(n, read_node)
            
        return PDG(self._graph)


def generate_mock_pdg(hbg: HBG, threshold=10) -> PDG:
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


def generate_mock_pdg_v2(hbg: HBG) -> PDG:
    pdgbuilder = PDGBuilder()

    for tid in hbg.tids:
        read_instruction_nodes = set()

        for n in hbg.get_thread_nodes(tid):
            n: nodes.AbstractNode

            match n.itype:
                case nodes.NodeType.READ:
                    read_instruction_nodes.add(n)
                case nodes.NodeType.WRITE:
                    cacheline_address = n.get_cacheline_address()
                    for read_node in set(filter(lambda r: r.get_cacheline_address() != cacheline_address, read_instruction_nodes)):
                        pdgbuilder.add_dependency(n, read_node)
                        read_instruction_nodes.remove(read_node)

    return pdgbuilder.build()
