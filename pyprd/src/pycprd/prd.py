from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Generator, List, Set, Tuple
import logging
from .nodes import AbstractNode, NodeType, ReadNode, WriteNode, FlushNode, EpochNode
from .trace_event_info import TraceEventInfo
from .vector_clock import PersistencyVectorClock, ReversedVectorClock
from .hbg import HBG
from .pdg import PDG
from . import utils


logger = logging.getLogger(__name__)


###########################################################
# Types
###########################################################
ThreadId    = int
Cacheline   = int


@dataclass(frozen=True)
class PersistencyRace:
    read_node: ReadNode
    write_node: WriteNode
    dependent_node: WriteNode
    is_write_hb_read: bool|None = field(default=None, compare=False, repr=False)
    is_write_hb_dependent: bool|None = field(default=None, compare=False, repr=False)
    validate: bool = field(default=True, compare=False, repr=False)

    def __post_init__(self):
        if self.validate:
            assert self.read_node.tid == self.dependent_node.tid
            assert self.read_node.is_interval_overlap(self.write_node)
            assert not self.read_node.is_interval_overlap(self.dependent_node)
            assert not self.write_node.is_interval_overlap(self.dependent_node)

    @property
    def tid(self):
        return self.read_node.tid
    
    def is_inter(self):
        return self.read_node.tid != self.write_node.tid
    
    def is_intra(self):
        return not self.is_inter()
    
    def __str__(self) -> str:
        s = []
        s.append('PERSISTENCY RACE!')
        s.append(f'W(X): {self.write_node}')
        s.append(f'R(X): {self.read_node}')
        s.append(f'W(Y): {self.dependent_node}')
        return '\n\t'.join(s)


class PersistencyRaces:
    def __init__(self):
        self._races:                Set[PersistencyRace]                       = set()
        self._races_by_pc:          Dict[int, Dict[int, Set[PersistencyRace]]] = defaultdict(lambda: defaultdict(set))
        self._races_by_pc_tstate:   Dict[int, Dict[int, Set[str]]]             = defaultdict(lambda: defaultdict(set))
        self._races_by_pc_wx_hb_wy: Dict[int, Dict[int, Set[str]]]             = defaultdict(lambda: defaultdict(set))
        self._races_by_info:        Dict[int, Dict[int, Set[PersistencyRace]]] = defaultdict(lambda: defaultdict(set))
        self._races_by_info_tstate: Dict[int, Dict[int, Set[str]]]             = defaultdict(lambda: defaultdict(set))
        self._races_by_info_wx_hb_wy: Dict[int, Dict[int, Set[str]]]             = defaultdict(lambda: defaultdict(set))
    
    @staticmethod
    def _get_race_id_by_pc(race: PersistencyRace):
        return race.read_node.pc, race.write_node.pc
    
    @staticmethod
    def _get_race_id_by_info(race: PersistencyRace):
        return race.read_node.info, race.write_node.info

    @property
    def races(self):
        return self._races
    
    @property
    def races_by_pc(self):
        return self._races_by_pc
    
    @property
    def races_by_info(self):
        return self._races_by_info

    def add_race(self, race: PersistencyRace):
        tstate = 'inter' if race.is_inter() else 'intra'
        wx_hb_wy = 'W(X)->W(Y)' if race.is_write_hb_dependent else 'W(X)|W(Y)'
        
        self._races.add(race)

        read_already_saved  = race.read_node.pc  in self._races_by_pc
        write_already_saved = race.write_node.pc in self._races_by_pc[race.read_node.pc]
        self._races_by_pc[race.read_node.pc][race.write_node.pc].add(race)
        self._races_by_pc_tstate[race.read_node.pc][race.write_node.pc].add(tstate)
        self._races_by_pc_wx_hb_wy[race.read_node.info][race.write_node.info].add(wx_hb_wy)
        
        read_already_saved  = race.read_node.info  in self._races_by_info
        write_already_saved = race.write_node.info in self._races_by_info[race.read_node.info]
        self._races_by_info[race.read_node.info][race.write_node.info].add(race)
        self._races_by_info_tstate[race.read_node.info][race.write_node.info].add(tstate)
        self._races_by_info_wx_hb_wy[race.read_node.info][race.write_node.info].add(wx_hb_wy)

    def clear(self):
        self._races.clear()
        self._races_by_pc.clear()
        
    @staticmethod
    def races_iterator(races: Dict[int, Dict[int, Set[PersistencyRace]]]) -> Generator[Tuple[int, ReadNode, WriteNode, Set[WriteNode]], None, None]:
        for i, read_id in enumerate(races):
            read_node = dependent_node = None
            write_nodes = set()
            for write_id, _races in races[read_id].items():
                race: PersistencyRace = next(iter(_races))
                if not read_node:
                    read_node = race.read_node
                    dependent_node = race.dependent_node
                write_nodes.add(race.write_node)

            if read_node:
                yield i, read_node, dependent_node, write_nodes

    def race_nodes_by_read_pc(self) -> Generator[Tuple[int, ReadNode, WriteNode, Set[WriteNode]], None, None]:
        return self.races_iterator(self._races_by_pc)

    def race_nodes_by_read_info(self) -> Generator[Tuple[int, ReadNode, WriteNode, Set[WriteNode]], None, None]:
        return self.races_iterator(self._races_by_info)
    
    def to_str(self, callstack_top: str | List[str] | None = None, group_by_info=True, trace_lines=False):
        all_lines = []
        
        def node_to_str(node: ReadNode | WriteNode, indent: int = 0) -> str:
            if isinstance(node.info, TraceEventInfo):
                return node.info.full_info(callstack_top_func=callstack_top, indent=indent)
            return node.info

        races = self.race_nodes_by_read_info() if group_by_info else self.race_nodes_by_read_pc()
        races_by_group = self._races_by_info if group_by_info else self._races_by_pc
        races_by_group_tsate = self._races_by_info_tstate if group_by_info else self._races_by_pc_tstate
        races_by_group_wx_hb_wy = self._races_by_info_wx_hb_wy if group_by_info else self._races_by_pc_wx_hb_wy

        for i, read_node, dependent_node, write_nodes in races:
            lines = [
                f'Race {i+1:4}',
                f'R(X): {node_to_str(read_node)}',
                f'W(Y): {node_to_str(dependent_node)}',
            ]
            for write_node in write_nodes:
                read_id = read_node.info if group_by_info else read_node.pc
                write_id = write_node.info if group_by_info else write_node.pc

                _all_races = races_by_group[read_id][write_id]

                frequency = len(_all_races) / len(self._races)
                tstate = ",".join(races_by_group_tsate[read_id][write_id])
                wx_hb_wy = ",".join(races_by_group_wx_hb_wy[read_id][write_id])
                
                _trace_lines = ''
                if trace_lines:
                    _trace_lines = ', '.join(sorted({f'(W {r.write_node.trace_line_number}, R {r.read_node.trace_line_number})' for r in _all_races}))
                    _trace_lines = f'\n    {_trace_lines}\n'
                
                lines.append(f'    W(X) {100*frequency:3.2f}% {len(_all_races):3}/{len(self._races)} ({tstate}) ({wx_hb_wy}): {node_to_str(write_node, indent=4)}{_trace_lines}')

            all_lines.append('\n'.join(lines))

        return f'\n{"":-^20}\n'.join(all_lines)

    def __str__(self) -> str:
        return self.to_str()


class PersistencyRaceDetector:
    def __init__(self, hbg: HBG, pdg: PDG,
                 ignore_inter_thread_edges=False,
                 ignore_flush_nodes=False,
                 ignore_persisted_before_index=False,
                 ignore_happens_after_index=False,
                 ignore_read_node_persistency=False,
                 show_only_first_bug_in_thread=False):
        self._hbg = hbg
        self._pdg = pdg
        self._races = PersistencyRaces()

        self._ignore_inter_thread_edges     = ignore_inter_thread_edges
        self._ignore_flush_nodes            = ignore_flush_nodes
        self._ignore_persisted_before_index = ignore_persisted_before_index
        self._ignore_happens_after_index    = ignore_happens_after_index
        self._ignore_read_node_persistency  = ignore_read_node_persistency
        self._show_only_first_bug_in_thread = show_only_first_bug_in_thread

        self._time_first_stage  = None
        self._time_second_stage = None
        
        self._race_counter_dropped_by_read_persistency = 0

    def stats(self) -> str:
        lines = []
        
        INDENT = ' ' * 2

        # Presets
        lines.append('Presets')
        lines.append(f"{INDENT}Ignore inter-thread edges (skipping Epoch nodes)                     {self._ignore_inter_thread_edges}")
        lines.append(f"{INDENT}Ignore flush nodes                                                   {self._ignore_flush_nodes}")
        lines.append(f"{INDENT}Ignore Persisted-Before vectors (all Write nodes are unflushed)      {self._ignore_persisted_before_index}")
        lines.append(f"{INDENT}Ignore Happens-After vectors (no nodes happen-after the read node)   {self._ignore_happens_after_index}")
        lines.append(f"{INDENT}Ignore read node persistency (the read is never considered flushed)  {self._ignore_read_node_persistency}")
        lines.append(f"{INDENT}Show only first bug in thread (don't iterate over all W(X)s)         {self._show_only_first_bug_in_thread}")

        # Races
        if self._races:
            lines.append('Races')
            lines.append(f"{INDENT}Total races by trace events      {len(self._races.races):,}")
            lines.append(f"{INDENT}Total races by instructions      {sum(map(len, self._races.races_by_pc.values())):,}")
            lines.append(f"{INDENT}Total races by callstack (info)  {sum(map(len, self._races.races_by_info.values())):,}")
            lines.append(f"{INDENT}Total races by read instructions {len(list(self._races.race_nodes_by_read_pc())):,}")
            lines.append(f"{INDENT}Duration                         {self._time_first_stage + self._time_second_stage:.3f} sec")
            lines.append(f"{INDENT}{INDENT}1st stage duration {self._time_first_stage:.3f} sec")
            lines.append(f"{INDENT}{INDENT}2nd stage duration {self._time_second_stage:.3f} sec")

        max_line_size = max(map(len, lines))
        lines.insert(0, f'{" CPRD Stats ":#^{max_line_size}}')
        lines.append(f'{"":#^{max_line_size}}')

        return '\n'.join(lines)

    @property
    def hbg(self):
        return self._hbg

    @property
    def pdg(self):
        return self._pdg
    
    @property
    def races(self):
        return self._races

    def _build_happens_after_vector_clocks(self):
        vc_per_thread:     Dict[ThreadId, ReversedVectorClock]  = utils.DefaultDictByKey(lambda tid: ReversedVectorClock(tid))
        vc_per_epoch_node: Dict[EpochNode, ReversedVectorClock] = utils.DefaultDictByKey(lambda n: ReversedVectorClock(n.tid))
        vc_per_read_node:  Dict[ReadNode, ReversedVectorClock]  = utils.DefaultDictByKey(lambda n: ReversedVectorClock(n.tid))

        for n in self._hbg.postorder():
            n:  AbstractNode
            vc: ReversedVectorClock = vc_per_thread[n.tid]

            match n.itype:
                case NodeType.WRITE:
                    n: WriteNode
                    vc.add_epoch(self._hbg.get_node_location(n).tindex)

                case NodeType.READ:
                    n: ReadNode
                    _vc: ReversedVectorClock = vc_per_read_node[n]
                    _vc.copy_from(vc)

                case NodeType.EPOCH:
                    if self._ignore_inter_thread_edges:
                        continue

                    n: EpochNode

                    # Tell inter parents the current state
                    for parent in self._hbg.get_inter_parents(n):
                        parent: EpochNode
                        _vc: ReversedVectorClock = vc_per_epoch_node[parent]
                        _vc.merge(vc)

                    # Merge my state with thread state and delete me
                    _vc: ReversedVectorClock = vc_per_epoch_node[n]
                    vc.merge(_vc)
                    del vc_per_epoch_node[n]

        return vc_per_read_node

    def _find_bugs(self,
                   dependent_node: WriteNode,
                   pvc_per_thread: Dict[ThreadId, Dict[Cacheline, PersistencyVectorClock]],
                   vc_per_read_node: Dict[ReadNode, ReversedVectorClock]):
        for read_node in self._pdg.get_dependencies(dependent_node):
            assert read_node.get_cacheline_address() != dependent_node.get_cacheline_address()

            pvc: PersistencyVectorClock = pvc_per_thread[dependent_node.tid][read_node.get_cacheline_address()]

            loc = self._hbg.get_node_location(read_node)

            # If the read is persisted, not a bug
            if not self._ignore_read_node_persistency and not self._ignore_persisted_before_index:
                if pvc.is_event_persisted(*loc):
                    self._race_counter_dropped_by_read_persistency += 1
                    continue

            # Find bugs
            daisy_chains = self._hbg.daisy_chains
            assert daisy_chains, "Can't find bugs without daisy chains"

            for tid in self._hbg.tids:
                last_persisted_epoch = pvc.get_persisted_epoch(tid) if not self._ignore_persisted_before_index else None

                if last_persisted_epoch is not None:
                    last_persisted_node = self._hbg.get_node_by_location((tid, last_persisted_epoch))
                    chain = daisy_chains.get_chain_by_node(last_persisted_node)
                else:
                    chain = daisy_chains.get_chain_by_thread(tid, read_node.get_cacheline_address())

                for write_node in chain:
                    write_node: WriteNode

                    # Is a different var
                    if not write_node.is_interval_overlap(read_node):
                        continue

                    write_node_loc = self._hbg.get_node_location(write_node)

                    # Is already persisted
                    if not self._ignore_persisted_before_index:
                        if pvc.is_event_persisted(*write_node_loc):
                            continue

                    # Is happens after the read
                    if not self._ignore_happens_after_index:
                        if vc_per_read_node[read_node].is_happens_after(*write_node_loc):
                            break

                    # It is a bug! Report it!
                    race = PersistencyRace(read_node, write_node, dependent_node,
                                           is_write_hb_dependent=pvc.is_event_happened_before(*write_node_loc))
                    self._races.add_race(race)
                    
                    # if (240227, 245017) == (race.write_node.trace_line_number, race.read_node.trace_line_number):
                    #     print(f'Found my race. is race: {self.is_bug(race)}')
                    #     import ipdb; ipdb.set_trace()
                    #     pass
                    
                    yield race

                    if self._show_only_first_bug_in_thread:
                        break

    def _do_persisted_before_vector_clocks_analysis(self, vc_per_read_node: Dict[ReadNode, ReversedVectorClock]):
        pvc_per_thread:          Dict[ThreadId, Dict[Cacheline, PersistencyVectorClock]]  = utils.DefaultDictByKey(lambda tid: defaultdict(lambda: PersistencyVectorClock(tid)))
        pvc_per_epoch_node:      Dict[EpochNode, Dict[Cacheline, PersistencyVectorClock]] = utils.DefaultDictByKey(lambda n: defaultdict(lambda: PersistencyVectorClock(n.tid)))
        dirty_cachelines:        Dict[ThreadId, Set[Cacheline]]                           = defaultdict(set)
        dirty_cachelines_vector: Dict[ThreadId, Dict[ThreadId, Set[Cacheline]]]           = defaultdict(lambda: defaultdict(set))

        for n in self._hbg.reverse_postorder():
            n: AbstractNode

            match n.itype:
                case NodeType.WRITE:
                    n: WriteNode
                    pvc: PersistencyVectorClock = pvc_per_thread[n.tid][n.get_cacheline_address()]
                    pvc.add_epoch(self._hbg.get_node_location(n).tindex)
                    dirty_cachelines[n.tid].add(n.get_cacheline_address())

                    # Find bugs
                    yield from self._find_bugs(n, pvc_per_thread, vc_per_read_node)

                case NodeType.READ:
                    n: ReadNode
                    pvc: PersistencyVectorClock = pvc_per_thread[n.tid][n.get_cacheline_address()]
                    pvc.add_epoch(self._hbg.get_node_location(n).tindex)
                    dirty_cachelines[n.tid].add(n.get_cacheline_address())

                case NodeType.FLUSH:
                    if self._ignore_flush_nodes:
                        continue

                    n: FlushNode
                    pvc: PersistencyVectorClock = pvc_per_thread[n.tid][n.get_cacheline_address()]
                    pvc.flush()
                    dirty_cachelines[n.tid].add(n.get_cacheline_address())

                case NodeType.EPOCH:
                    if self._ignore_inter_thread_edges:
                        continue

                    n: EpochNode

                    if dirty_cachelines[n.tid]:
                        for thread in self._hbg.tids:
                            if thread != n.tid:
                                dirty_cachelines_vector[n.tid][thread].update(dirty_cachelines[n.tid])

                        # clear temp dirty buffer
                        dirty_cachelines[n.tid].clear()

                    # Tell inter children the current state
                    for child in self._hbg.get_inter_children(n):
                        child: EpochNode

                        for cacheline in dirty_cachelines_vector[n.tid][child.tid]:
                            my_pvc: PersistencyVectorClock = pvc_per_thread[n.tid][cacheline]
                            child_pvc: PersistencyVectorClock = pvc_per_epoch_node[child][cacheline]
                            child_pvc.merge(my_pvc)
                            # dirty_cachelines_per_epoch_node[child].add(cacheline)

                        # clean dirty
                        dirty_cachelines_vector[n.tid][child.tid].clear()

                    # Merge my state with thread state and delete me
                    # for cacheline in dirty_cachelines_per_epoch_node
                    for cacheline in pvc_per_epoch_node[n]:
                        # only dirty cachelines
                        _pvc: PersistencyVectorClock = pvc_per_epoch_node[n][cacheline]
                        pvc: PersistencyVectorClock  = pvc_per_thread[n.tid][cacheline]
                        pvc.merge(_pvc)
                        dirty_cachelines[n.tid].add(cacheline)
                    del pvc_per_epoch_node[n]

    def run(self, validate=False):
        self._races.clear()

        with utils.timeit() as t:
            vc_per_read_node = self._build_happens_after_vector_clocks()
        self._time_first_stage = t.total

        with utils.timeit() as t:
            races = list(self._do_persisted_before_vector_clocks_analysis(vc_per_read_node))
        self._time_second_stage = t.total

        if validate:
            for race in races:
                if not self.is_bug(race):
                    raise Exception(f'Not a race!\n{race}')

        return races

    def is_bug(self, race: PersistencyRace):
        assert race.read_node.itype == NodeType.READ
        assert race.write_node.itype == NodeType.WRITE
        assert race.dependent_node.itype == NodeType.WRITE

        # If W(X) and R(X) are of different vars, then this is not a bug
        if not race.read_node.is_interval_overlap(race.write_node):
            return False

        # Find happens-after group
        happens_after_group = {n for n in self._hbg.bfs_successors(race.read_node) if NodeType.is_instruction_type(n.itype)}

        assert race.dependent_node in happens_after_group, "W(Y) isn't happening after R(X)"

        # If W(X) happens after R(X), there is no bug
        if race.write_node in happens_after_group:
            return False

        # Find last known FLUSH from each thread
        last_known_flushes = {}
        for n in self._hbg.bfs_predecessors(race.dependent_node):
            if n.tid in last_known_flushes:
                continue
            if n.itype == NodeType.FLUSH and n.is_interval_contains(race.read_node):
                last_known_flushes[n.tid] = n

        # Find persisted-before group
        persisted_before = set()
        for flush_node in last_known_flushes.values():
            persisted_before |= {n for n in self._hbg.bfs_predecessors(flush_node) if NodeType.is_instruction_type(n.itype)}

        # If R(X) is persisted before W(Y), there is no bug
        if race.read_node in persisted_before:
            return False

        # If W(X) is persisted before W(Y), there is no bug
        if race.write_node in persisted_before:
            return False
        
        return True
        
