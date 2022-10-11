from typing import Dict, Generator, Iterable, List, Set, Tuple
from collections import namedtuple, defaultdict
from enum import Enum
import networkx as nx
import nodes
import utils
import config


class EdgeType(Enum):
    INTER_THREAD                = 'inter-thread'
    INTRA_THREAD                = 'intra-thread'


NodeLocation = namedtuple('NodeLocation', ['tid', 'tindex'])


class HBG:
    def __init__(self,
                 base_graph: nx.DiGraph,
                 nodes_by_thread: Dict[int, List[nodes.AbstractNode]],
                 nodes_by_type: Dict[nodes.NodeType, Set[nodes.AbstractNode]],
                 nodes_location: Dict[nodes.AbstractNode, NodeLocation],
                 cacheline_size=config.DEFAULT_CACHELINE_SIZE):

        self._graph           = base_graph
        self._nodes_by_thread = nodes_by_thread
        self._nodes_by_type   = nodes_by_type
        self._nodes_location  = nodes_location
        self._cacheline_size  = cacheline_size

        self._inter_graph = nx.subgraph_view(self._graph, filter_edge=lambda u, v: self._graph[u][v]['type'] == EdgeType.INTER_THREAD)
        self._intra_graph = nx.subgraph_view(self._graph, filter_edge=lambda u, v: self._graph[u][v]['type'] == EdgeType.INTRA_THREAD)

        self._vars:                Dict[Tuple[int, int], Set[nodes.InstructionNode]] = defaultdict(set)
        self._read_nodes_by_vars:  Dict[Tuple[int, int], Set[nodes.InstructionNode]] = defaultdict(set)
        self._write_nodes_by_vars: Dict[Tuple[int, int], Set[nodes.InstructionNode]] = defaultdict(set)
        self._vars_by_size:        Dict[int, Set[Tuple[int, int]]]                   = defaultdict(set)
        self._cachelines:          Dict[Tuple[int, int], Set[Tuple[int, int]]]       = defaultdict(set)

        self._find_vars()

        assert nx.is_directed_acyclic_graph(self._graph), 'HBG graph is not a DAG'

    def _find_vars(self):
        for n in self.read_write_nodes:
            if n.interval not in self._vars:
                cacheline_address = utils.get_cacheline_address(n.address, self._cacheline_size)
                next_cacheline_address = cacheline_address + self._cacheline_size

                assert n.interval[1] <= next_cacheline_address, f'Variable at {n.address:#x} of size {n.size} crosses a cacheline'

                self._vars_by_size[n.size].add(n.interval)
                self._cachelines[(cacheline_address, cacheline_address+self._cacheline_size)].add(n.interval)

            self._vars[n.interval].add(n)

            if n.itype == nodes.NodeType.READ:
                self._read_nodes_by_vars[n.interval].add(n)
            elif n.itype == nodes.NodeType.WRITE:
                self._write_nodes_by_vars[n.interval].add(n)

    def stats(self, full=False) -> str:
        import statistics
        
        lines = []
        
        INDENT = ' ' * 2

        # Threads
        lines.append(f'Number of Threads     {len(self.tids)}')

        # Variables
        lines.append(f'Number of Variables   {len(self._vars)}')
        for k in sorted(self._vars_by_size):
            lines.append(f'{INDENT}{k:<2} {len(self._vars_by_size[k])}')

        # Nodes per variable statistics
        lines.append('Nodes per variable statistics')
        total_nodes_per_var = sorted(list(map(len, self._vars.values())))
        assert sum(total_nodes_per_var) == len(self.read_write_nodes)
        lines.append(f'{INDENT}Average      {len(self.read_write_nodes) / len(self._vars):.2f}')
        lines.append(f'{INDENT}Variance     {statistics.variance(total_nodes_per_var):.2f}')
        total_nodes_per_var_set = set(total_nodes_per_var)
        lines.append(f'{INDENT}Unique sizes {len(total_nodes_per_var_set)}')
        if len(total_nodes_per_var_set) < 15:
            lines.append(f'{INDENT}Sizes        {sorted(list(total_nodes_per_var_set), reverse=True)}')
        # lines.append(f'{INDENT}2nd max  {total_nodes_per_var[-2]}')
        # lines.append(f'{INDENT}Min      {min(total_nodes_per_var)}')

        # Cachelines
        lines.append(f'Number of Cachelines  {len(self._cachelines)}')
        lines.append(f'Cacheline size        {self._cacheline_size}')

        # Nodes
        lines.append(f'Number of Nodes       {self._graph.number_of_nodes()}')
        for t in nodes.NodeType:
            lines.append(f'{INDENT}{t.name:6} {len(self.get_nodes_by_type(t))}')

        # Edges
        if full:
            lines.append(f'Number of Edges       {self._graph.number_of_edges()}')
            lines.append(f'{INDENT}Inter Edges {self.inter.number_of_edges()}')
            lines.append(f'{INDENT}Intra Edges {self.intra.number_of_edges()}')

        max_line_size = max(map(len, lines))
        lines.insert(0, f'{" HBG Stats ":#^{max_line_size}}')
        lines.append(f'{"":#^{max_line_size}}')

        return '\n'.join(lines)

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
    def vars(self) -> Iterable[Tuple[int, int]]:
        return self._vars.keys()

    @property
    def cacheline_size(self) -> int:
        return self._cacheline_size

    def get_vars_in_cache_line(self, cache_line: Tuple[int, int]):
        return self._cachelines[cache_line]

    def get_node_by_location(self, location: NodeLocation | Tuple[int, int]) -> nodes.AbstractNode:
        location = NodeLocation(*location)
        return self._nodes_by_thread[location.tid][location.tindex]

    def get_node_location(self, node: nodes.AbstractNode) -> NodeLocation:
        return self._nodes_location[node]

    def get_thread_nodes(self, tid: int) -> List[nodes.AbstractNode]:
        return self._nodes_by_thread[tid]

    def get_nodes_by_type(self, itype: nodes.NodeType) -> Set[nodes.AbstractNode]:
        return self._nodes_by_type.setdefault(itype, set())
    
    def get_nodes_by_var(self, var: Tuple[int, int]) -> Set[nodes.InstructionNode]:
        return self._vars[var]
    
    def get_read_nodes_by_var(self, var: Tuple[int, int]) -> Set[nodes.InstructionNode]:
        return self._read_nodes_by_vars[var]
    
    def get_write_nodes_by_var(self, var: Tuple[int, int]) -> Set[nodes.InstructionNode]:
        return self._write_nodes_by_vars[var]

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
    def all_nodes(self) -> Set[nodes.AbstractNode]:
        return self._graph.nodes()

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

    def is_before_in_thread(self, n1: nodes.AbstractNode, n2: nodes.AbstractNode):
        if not n1 or not n2:
            return False
        assert n1.tid == n2.tid
        return self.get_node_location(n1).tindex < self.get_node_location(n2).tindex

    def postorder(self) -> Generator[nodes.AbstractNode, None, None]:
        return nx.dfs_postorder_nodes(self._graph)

    def reverse_postorder(self) -> Generator[nodes.AbstractNode, None, None]:
        return nx.topological_sort(self._graph)


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
        n = nodes.EpochNode(tid, epoch)
        self._nodes.append(n)
        return n

    def add_instruction_node(self, itype: nodes.NodeType, tid: int, pc: int, address: int, size: int, info=None):
        n = nodes.InstructionNode(itype, tid, pc, address, size, info)
        self._nodes.append(n)
        return n

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
        cacheline_size = None

        if filter_volatile_nodes:
            self._filter_volatile_nodes()

        for n in self._nodes:
            self._add_node(n)
            if not cacheline_size and n.itype == nodes.NodeType.FLUSH:
                n: nodes.InstructionNode
                cacheline_size = n.size

        for src, dst in self._edges:
            self._add_happens_before_edge(src, dst)

        if not cacheline_size:
            cacheline_size = config.DEFAULT_CACHELINE_SIZE

        return HBG(self._graph, self._nodes_by_thread, self._nodes_by_type, self._nodes_location, cacheline_size=cacheline_size)
