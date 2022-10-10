from typing import Dict, Generator, Iterable, List, Set, Tuple
from collections import namedtuple
from enum import Enum
import networkx as nx
import intervaltree
import nodes


CACHELINE_SIZE = 64


class EdgeType(Enum):
    INTER_THREAD                = 'inter-thread'
    INTRA_THREAD                = 'intra-thread'
    TRAVERSAL_POSTORDER         = 'traversal-postorder'
    TRAVERSAL_REVERSE_POSTORDER = 'traversal-reverse-postorder'


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
        
        self._add_traversal_postorder_edges()
        
        self._vars: Set[Tuple[int, int]] = set()
        self._cache_lines: Dict[Tuple[int, int], Set[Tuple[int, int]]] = {}
        
        
        mask = ((1 << 64) - 1) * CACHELINE_SIZE
        
        for n in self.read_write_nodes:
            # TODO: assert vars are contained in cache lines
            if n.interval in self._vars:
                continue
            self._vars.add(n.interval)
            cache_line_address = n.address & mask
            self._cache_lines.setdefault((cache_line_address, cache_line_address+CACHELINE_SIZE), set()).add(n.interval)
        
        assert nx.is_directed_acyclic_graph(self), 'HBG is not a DAG'
        
        return self
    
    def _add_traversal_postorder_edges(self):
        """Adds edges that cause a postorder to visit an epoch node before all intra-parents of its intra-children"""
        for epoch_node in self.epoch_nodes:
            for inter_child in self.get_inter_children(epoch_node):
                intra_parent = self.get_intra_parent(inter_child)
                if intra_parent:
                    self.add_edge(intra_parent, epoch_node, type=EdgeType.TRAVERSAL_POSTORDER)
        
    @property
    def inter(self) -> nx.DiGraph:
        return self._inter_graph
    
    @property
    def intra(self) -> nx.DiGraph:
        return self._intra_graph
    
    @property
    def tids(self) -> Iterable[int]:
        return self._nodes_by_thread.keys()
    
    @property
    def vars(self) -> Set[Tuple[int, int]]:
        return self._vars
    
    def get_vars_in_cache_line(self, cache_line):
        return self._cache_lines[cache_line]
    # def get_vars_in_range(self, begin: int, end: int) -> Generator[Tuple[int, int], None, None]:
    #     for i in self._vars_tree.envelop(begin, end):
    #         i: intervaltree.Interval
    #         yield (i.begin, i.end)
    
    def get_node_by_location(self, location: NodeLocation | Tuple[int, int]) -> nodes.AbstractNode:
        location = NodeLocation(*location)
        return self._nodes_by_thread[location.tid][location.tindex]
    
    def get_node_location(self, node: nodes.AbstractNode) -> NodeLocation:
        return self._nodes_location[node]
    
    def get_thread_nodes(self, tid: int) -> List[nodes.AbstractNode]:
        return self._nodes_by_thread[tid]
    
    def get_nodes_by_type(self, itype: nodes.NodeType) -> Set[nodes.AbstractNode]:
        return self._nodes_by_type[itype]
    
    def get_inter_children(self, node: nodes.AbstractNode) -> Iterable[nodes.AbstractNode]:
        return self.inter.neighbors(node)

    def get_inter_parents(self, node: nodes.AbstractNode) -> Iterable[nodes.AbstractNode]:
        return self.inter.predecessors(node)

    def get_intra_child(self, node: nodes.AbstractNode) -> nodes.AbstractNode:
        children = list(self.intra.neighbors(node))

        if not children:
            return None
        
        child, = children
        return child

    def get_intra_parent(self, node) -> nodes.AbstractNode:
        parents = list(self.intra.predecessors(node))
        
        if not parents:
            return None
        
        parent, = parents
        return parent
    
    @property
    def write_nodes(self) -> Set[nodes.InstructionNode]:
        return self.get_nodes_by_type(nodes.NodeType.WRITE)
    
    @property
    def read_nodes(self) -> Set[nodes.InstructionNode]:
        return self.get_nodes_by_type(nodes.NodeType.READ)
    
    @property
    def flush_nodes(self) -> Set[nodes.InstructionNode]:
        return self.get_nodes_by_type(nodes.NodeType.FLUSH)
    
    @property
    def epoch_nodes(self) -> Set[nodes.EpochNode]:
        return self.get_nodes_by_type(nodes.NodeType.EPOCH)
    
    @property
    def read_write_nodes(self) -> Set[nodes.InstructionNode]:
        return self.read_nodes | self.write_nodes
    
    @property
    def instruction_nodes(self) -> Set[nodes.InstructionNode]:
        return self.read_nodes | self.write_nodes | self.flush_nodes


class HBGBuilder:
    def __init__(self, verbose=True):
        self._log = print if verbose else lambda x: None

        self._nodes: List[nodes.AbstractNode] = []
        self._edges: Set[Tuple[nodes.AbstractNode, nodes.AbstractNode]] = set()

        self._graph = nx.DiGraph()
        self._thread_tails: Dict[int, nodes.AbstractNode] = {}
        self._nodes_by_thread: Dict[int, List[nodes.AbstractNode]] = {}
        self._nodes_by_type: Dict[nodes.NodeType, Set[nodes.AbstractNode]] = {}
        self._nodes_location: Dict[nodes.AbstractNode, NodeLocation] = {}

    def add_epoch_node(self, tid: int, epoch: int):
        self._nodes.append(nodes.EpochNode(tid, epoch))

    def add_instruction_node(self, itype: nodes.NodeType, tid: int, pc: int, address: int, size: int, info=None):
        self._nodes.append(nodes.InstructionNode(itype, tid, pc, address, size, info))

    def add_happens_before_edge(self, src_tid, src_epoch, dst_tid, dst_epoch):
        self._edges.add((nodes.EpochNode(src_tid, src_epoch), nodes.EpochNode(dst_tid, dst_epoch)))

    def _filter_volatile_nodes(self):
        import intervaltree

        t = intervaltree.IntervalTree()

        for n in self._nodes:
            if n.itype == nodes.NodeType.FLUSH:
                n: nodes.InstructionNode
                t.addi(*n.interval)

        t.merge_overlaps(strict=False)

        def should_keep(n: nodes.AbstractNode):
            if n.itype not in (nodes.NodeType.READ, nodes.NodeType.WRITE):
                return True

            n: nodes.InstructionNode
            if t.overlaps_range(*n.interval):
                return True

            return False

        self._log(f'Total nodes before filter {len(self._nodes)}')
        self._nodes = list(filter(should_keep, self._nodes))
        self._log(f'Total nodes after filter  {len(self._nodes)}')

        return self

    def _add_node(self, node: nodes.AbstractNode):
        self._graph.add_node(node)

        self._graph.nodes[node]['itype'] = node.itype
        self._graph.nodes[node][node.itype] = True

        self._nodes_by_thread.setdefault(node.tid, [])
        self._nodes_location[node] = NodeLocation(node.tid, len(self._nodes_by_thread[node.tid]))
        self._nodes_by_thread[node.tid].append(node)
        self._nodes_by_type.setdefault(node.itype, set()).add(node)
        
        if node.tid in self._thread_tails:
            self._graph.add_edge(self._thread_tails[node.tid], node, type=EdgeType.INTRA_THREAD)

        self._thread_tails[node.tid] = node

    def _add_happens_before_edge(self, src: nodes.EpochNode, dst: nodes.EpochNode):
        assert src.tid != dst.tid, 'TIDs must be different'
        self._graph.add_edge(src, dst, type=EdgeType.INTER_THREAD)

    def build(self, filter_volatile_nodes=True) -> HBG:
        if filter_volatile_nodes:
            self._filter_volatile_nodes()
            
        for n in self._nodes:
            self._add_node(n)

        for src, dst in self._edges:
            self._add_happens_before_edge(src, dst)

        return HBG(self._graph, self._nodes_by_thread, self._nodes_by_type, self._nodes_location)
