from typing import Any, Dict, Generator, Iterable, List, Set, Tuple
from collections import namedtuple, defaultdict
from enum import Enum
import networkx as nx
import math
from . import nodes
from .nodes import ReadNode, WriteNode
from . import utils
from . import config


class EdgeType(Enum):
    INTER_THREAD                = 'inter-thread'
    INTRA_THREAD                = 'intra-thread'


class NodeLocation(namedtuple('NodeLocation', ['tid', 'tindex'])):
    class DifferentThreadsException(Exception): pass

    def _convert(self, obj: object):
        if isinstance(obj, self.__class__):
            if obj.tid != self.tid:
                raise self.DifferentThreadsException("Can't compare different tids")
            return obj
        elif obj is None:
            return self.__class__(self.tid, -math.inf)
        raise TypeError(f"Can't convert {obj} to {self.__class__}")
    
    def __eq__(self, other: 'NodeLocation') -> bool:
        return super().__eq__(self._convert(other))
    
    def __ne__(self, other: 'NodeLocation') -> bool:
        return super().__ne__(self._convert(other))

    def __gt__(self, other: 'NodeLocation') -> bool:
        return super().__gt__(self._convert(other))
    
    def __ge__(self, other: 'NodeLocation') -> bool:
        return super().__ge__(self._convert(other))
    
    def __lt__(self, other: 'NodeLocation') -> bool:
        return super().__lt__(self._convert(other))
    
    def __le__(self, other: 'NodeLocation') -> bool:
        return super().__le__(self._convert(other))


class DaisyChain:
    def __init__(self):
        self._first_node:     WriteNode                             = None
        self._last_node:      WriteNode                             = None
        self._chain:          Dict[WriteNode | ReadNode, WriteNode] = {}
        self._write_nodes:    Set[WriteNode]                        = set()
        self._dangling_reads: Set[ReadNode]                         = set()

    def add_write_node(self, n: WriteNode):
        if self._last_node is not None:
            self._chain[self._last_node] = n
        else:
            self._first_node = n
        self._last_node = n
        self._chain[n] = None

        while self._dangling_reads:
            r = self._dangling_reads.pop()
            self._chain[r] = n

        self._write_nodes.add(n)

    def add_read_node(self, n: ReadNode):
        self._dangling_reads.add(n)
        self._chain[n] = None

    def get_chain(self, start_node: WriteNode | None = None):
        if start_node is None:
            if self._first_node is None:
                return
            start_node = self._first_node
        elif start_node not in self._chain:
            raise IndexError(start_node)
        
        next_node = start_node
        while True:
            # TODO: can be changed to a itype validation
            if next_node in self._write_nodes:
                yield next_node
            next_node = self._chain[next_node]
            if next_node is None:
                return
            
    def __len__(self):
        return len(self._chain)


# TODO: move these
ThreadId = int
Cacheline = int


class DaisyChains:
    def __init__(self):
        self._chains: Dict[Cacheline, Dict[ThreadId, DaisyChain]] = defaultdict(lambda: defaultdict(DaisyChain))

    def add_write_node(self, n: nodes.WriteNode):
        self._chains[n.get_cacheline_address()][n.tid].add_write_node(n)
        return n
    
    def add_read_node(self, n: nodes.ReadNode):
        self._chains[n.get_cacheline_address()][n.tid].add_read_node(n)
        return n
    
    def add_node(self, n: nodes.AbstractNode):
        op = {
            nodes.NodeType.WRITE: self.add_write_node,
            nodes.NodeType.READ: self.add_read_node,
        }.get(n.itype)

        if op:
            return op(n)

    def get_chain_by_node(self, n: nodes.WriteNode | nodes.ReadNode):
        return self._chains[n.get_cacheline_address()][n.tid].get_chain(n)

    def get_chain_by_thread(self, tid: ThreadId, cacheline: Cacheline):
        return self._chains[cacheline][tid].get_chain()
    
    def get_daisychains(self):
        for _, d in self._chains.items():
            for _, dc in d.items():
                yield dc


class HBG:
    def __init__(self,
                 base_graph: nx.DiGraph,
                 nodes: List[nodes.AbstractNode],
                 nodes_by_thread: Dict[int, List[nodes.AbstractNode]],
                 nodes_by_type: Dict[nodes.NodeType, Set[nodes.AbstractNode]],
                 nodes_location: Dict[nodes.AbstractNode, NodeLocation],
                 cacheline_size=config.DEFAULT_CACHELINE_SIZE,
                 daisy_chains: DaisyChains = None):

        self._graph           = base_graph
        self._nodes           = nodes
        self._nodes_by_thread = nodes_by_thread
        self._nodes_by_type   = nodes_by_type
        self._nodes_location  = nodes_location
        self._cacheline_size  = cacheline_size
        self._daisy_chains   = daisy_chains

        self._inter_graph = nx.subgraph_view(self._graph, filter_edge=lambda u, v: self._graph[u][v]['type'] == EdgeType.INTER_THREAD)
        self._intra_graph = nx.subgraph_view(self._graph, filter_edge=lambda u, v: self._graph[u][v]['type'] == EdgeType.INTRA_THREAD)

        self._vars:                Dict[Tuple[int, int], Set[nodes.InstructionNode]] = defaultdict(set)
        self._read_nodes_by_vars:  Dict[Tuple[int, int], Set[nodes.InstructionNode]] = defaultdict(set)
        self._write_nodes_by_vars: Dict[Tuple[int, int], Set[nodes.InstructionNode]] = defaultdict(set)
        self._vars_by_size:        Dict[int, Set[Tuple[int, int]]]                   = defaultdict(set)
        self._cachelines:          Dict[int, Set[Tuple[int, int]]]                   = defaultdict(set)
        
        self._pc_info = {n.pc: n.info for n in self.instruction_nodes}

        self._find_vars()

        assert nx.is_directed_acyclic_graph(self._graph), 'HBG graph is not a DAG'

    def _find_vars(self):
        for n in self.read_write_nodes:
            if n.interval not in self._vars:
                cacheline_address = utils.get_cacheline_address(n.address, self._cacheline_size)
                next_cacheline_address = cacheline_address + self._cacheline_size

                assert n.interval[1] <= next_cacheline_address, f'Variable at {n.address:#x} of size {n.size} crosses a cacheline'
                # TODO: if this assert occurs, we must handle these cases!

                self._vars_by_size[n.size].add(n.interval)
                self._cachelines[cacheline_address].add(n.interval)

            self._vars[n.interval].add(n)

            if n.itype == nodes.NodeType.READ:
                self._read_nodes_by_vars[n.interval].add(n)
            elif n.itype == nodes.NodeType.WRITE:
                self._write_nodes_by_vars[n.interval].add(n)

    def _cacheline_liveliness_analysis(self):
        cacheline_first = {}
        cacheline_last  = {}

        for i, n in enumerate(self._nodes):
            if not nodes.NodeType.is_instruction_type(n.itype):
                continue
            n: nodes.InstructionNode
            cacheline = n.get_cacheline_address()
            if cacheline not in cacheline_first:
                cacheline_first[cacheline] = i
            cacheline_last[cacheline] = i

        return {cacheline: (cacheline_last[cacheline] - cacheline_first[cacheline]) / len(self._nodes) for cacheline in cacheline_first}

    def stats(self, full=False) -> str:
        import statistics
        
        lines = []
        
        INDENT = ' ' * 2

        # Threads
        lines.append(f'Number of Threads     {len(self.tids):,}')

        # Variables
        lines.append(f'Number of Variables   {len(self._vars):,}')
        for k in sorted(self._vars_by_size):
            lines.append(f'{INDENT}{k:<2} {len(self._vars_by_size[k]):,}')

        # Nodes per variable statistics
        lines.append('Nodes per variable statistics')
        total_nodes_per_var = sorted(list(map(len, self._vars.values())))
        assert sum(total_nodes_per_var) == len(self.read_write_nodes)
        lines.append(f'{INDENT}Average      {len(self.read_write_nodes) / len(self._vars):,.2f}')
        lines.append(f'{INDENT}Variance     {statistics.variance(total_nodes_per_var):,.2f}')
        total_nodes_per_var_set = set(total_nodes_per_var)
        lines.append(f'{INDENT}Unique sizes {len(total_nodes_per_var_set):,}')
        if len(total_nodes_per_var_set) < 15:
            lines.append(f'{INDENT}Sizes        {sorted(list(total_nodes_per_var_set), reverse=True)}')
        # lines.append(f'{INDENT}2nd max  {total_nodes_per_var[-2]}')
        # lines.append(f'{INDENT}Min      {min(total_nodes_per_var)}')
            
        # RW Candidates
        _write_pcs_by_read_pc = defaultdict(set)
        for var, read_nodes in self._read_nodes_by_vars.items():
            write_nodes = self._write_nodes_by_vars.get(var, [])
            for r in read_nodes:
                _write_pcs_by_read_pc[r.pc] |= ({w.pc for w in write_nodes})

        _total_rw_couples = sum(map(len, _write_pcs_by_read_pc.values()))
        lines.append(f'R/W Candidates {_total_rw_couples:,}')

        # PC
        lines.append('Instructions')
        lines.append(f'{INDENT}Total instructions            {len(self._pc_info):,}')
        lines.append(f'{INDENT}{INDENT}Total read instructions  {len({r.pc for r in self._nodes_by_type[nodes.NodeType.READ]}):,}')
        lines.append(f'{INDENT}{INDENT}Total write instructions {len({r.pc for r in self._nodes_by_type[nodes.NodeType.WRITE]}):,}')
        lines.append(f'{INDENT}{INDENT}Total flush instructions {len({r.pc for r in self._nodes_by_type[nodes.NodeType.FLUSH]}):,}')
        lines.append(f'{INDENT}Trace events per instructions {self._graph.number_of_nodes()/len(self._pc_info):,.2f}')
        self._pc_info

        # Cachelines
        lines.append(f'Number of Cachelines  {len(self._cachelines):,}')
        lines.append(f'Cacheline size        {self._cacheline_size}')

        cacheline_liveliness = self._cacheline_liveliness_analysis()

        lines.append(f'{INDENT}Max liveliness {max(cacheline_liveliness.values()) * 100:,.2f}%')
        lines.append(f'{INDENT}Average length {statistics.mean(cacheline_liveliness.values()) * 100:,.2f}%')
        lines.append(f'{INDENT}Median length  {statistics.median(cacheline_liveliness.values()) * 100:,.2f}%')

        lines.append('Nodes per cacheline statistics')
        nodes_per_cacheline = defaultdict(int)
        for n in self._nodes:
            if nodes.NodeType.is_instruction_type(n.itype):
                nodes_per_cacheline[n.get_cacheline_address()] += 1

        lines.append(f'{INDENT}Max      {max(nodes_per_cacheline.values())}')
        lines.append(f'{INDENT}Median   {statistics.median(nodes_per_cacheline.values())}')
        lines.append(f'{INDENT}Average  {statistics.mean(nodes_per_cacheline.values()):,.2f}')
        lines.append(f'{INDENT}Variance {statistics.variance(nodes_per_cacheline.values()):,.2f}')

        # Nodes
        lines.append(f'Number of Nodes       {self._graph.number_of_nodes():,}')
        for t in nodes.NodeType:
            lines.append(f'{INDENT}{t.name:6} {len(self.get_nodes_by_type(t)):,}')

        # Edges
        if full:
            lines.append(f'Number of Edges       {self._graph.number_of_edges():,}')
            lines.append(f'{INDENT}Inter Edges {self.inter.number_of_edges():,}')
            lines.append(f'{INDENT}Intra Edges {self.intra.number_of_edges():,}')

        # DaisyChains
        if self._daisy_chains:
            daisy_chains = list(self._daisy_chains.get_daisychains())
            lines.append(f'Number of chains      {len(daisy_chains):,}')
            lines.append(f'{INDENT}Max length     {max(map(len, daisy_chains)):,}')
            lines.append(f'{INDENT}Average length {statistics.mean(map(len, daisy_chains)):,.2f}')
            lines.append(f'{INDENT}Median length  {statistics.median(map(len, daisy_chains)):,.2f}')

        max_line_size = max(map(len, lines))
        lines.insert(0, f'{" HBG Stats ":#^{max_line_size}}')
        lines.append(f'{"":#^{max_line_size}}')

        return '\n'.join(lines)
    
    def __len__(self):
        return len(self._nodes)

    @property
    def graph(self) -> nx.DiGraph:
        return  nx.subgraph_view(self._graph)

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

    @property
    def nodes_by_var(self):
        return self._vars
    
    @property
    def read_nodes_by_var(self):
        return self._read_nodes_by_vars
    
    @property
    def write_nodes_by_var(self):
        return self._write_nodes_by_vars
    
    @property
    def daisy_chains(self) -> DaisyChains | None:
        return self._daisy_chains
    
    def get_vars_in_cacheline(self, cacheline_address: int):
        return self._cachelines[cacheline_address]

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

    def get_intra_parent(self, node: nodes.AbstractNode) -> nodes.AbstractNode:
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
    
    def bfs_successors(self, source: nodes.AbstractNode) -> Generator[nodes.AbstractNode, None, None]:
        return (successor for _, successor in nx.bfs_edges(self._graph, source))

    def bfs_predecessors(self, source: nodes.AbstractNode) -> Generator[nodes.AbstractNode, None, None]:
        return (predecessor for _, predecessor in nx.bfs_edges(self._graph, source, reverse=True))

    def get_pc_info(self, pc: int) -> str | None:
        return self._pc_info.get(pc)


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

    def add_instruction_node(self, itype: nodes.NodeType, tid: int, pc: int, address: int, size: int, info: Any=None, trace_line_number: int=None):
        n = nodes.create_instruction_node(itype, tid, pc, address, size, info, trace_line_number)
        self._nodes.append(n)
        return n

    def add_happens_before_edge(self, src_tid, src_epoch, dst_tid, dst_epoch):
        self._edges.add((nodes.EpochNode(src_tid, src_epoch), nodes.EpochNode(dst_tid, dst_epoch)))

    def _filter_volatile_nodes(self, pmem_range=None, ignore_ranges: Set[Tuple[int, int]]|None = None):
        import intervaltree

        keep_tree = intervaltree.IntervalTree()
        ignore_tree = intervaltree.IntervalTree()

        if pmem_range:
            self._log(f'Filtering with given PMEM range from 0x{pmem_range[0]:x} to 0x{pmem_range[1]:x} (size of 0x{pmem_range[1]-pmem_range[0]:x})')
            keep_tree.addi(*pmem_range)
        else:
            for n in self._nodes:
                if n.itype == nodes.NodeType.FLUSH:
                    n: nodes.InstructionNode
                    keep_tree.addi(*n.interval)

        keep_tree.merge_overlaps(strict=False)
        
        if ignore_ranges:
            for begin, end in ignore_ranges:
                ignore_tree.addi(begin, end)

        def should_keep(n: nodes.AbstractNode):
            if n.itype not in (nodes.NodeType.READ, nodes.NodeType.WRITE):
                return True

            n: nodes.InstructionNode
            
            if ignore_tree.envelop(*n.interval):
                return False
            
            if keep_tree.overlaps_range(*n.interval):
                return True

            return False

        self._log(f'Total nodes before filter {len(self._nodes):,}')
        self._nodes = list(filter(should_keep, self._nodes))
        self._log(f'Total nodes after filter  {len(self._nodes):,}')

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

    def build(self, filter_volatile_nodes=True, pmem_range=None, make_daisy_chains=True, ignore_ranges=None) -> HBG:
        cacheline_size = None

        daisy_chains = None
        if make_daisy_chains:
            daisy_chains = DaisyChains()
        
        if filter_volatile_nodes:
            self._filter_volatile_nodes(pmem_range, ignore_ranges)

        for n in self._nodes:
            self._add_node(n)

            if daisy_chains:
                daisy_chains.add_node(n)

            if not cacheline_size and n.itype == nodes.NodeType.FLUSH:
                n: nodes.InstructionNode
                cacheline_size = n.size

        for src, dst in self._edges:
            self._add_happens_before_edge(src, dst)

        if not cacheline_size:
            cacheline_size = config.DEFAULT_CACHELINE_SIZE

        return HBG(self._graph, self._nodes, self._nodes_by_thread, self._nodes_by_type, self._nodes_location, cacheline_size=cacheline_size, daisy_chains=daisy_chains)
