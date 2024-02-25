from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Generator, Set, Tuple
from nodes import AbstractNode, NodeType, ReadNode, WriteNode, FlushNode, EpochNode
from vector_clock import PersistencyVectorClock, ReversedVectorClock
from hbg import HBG
from pdg import PDG
import utils


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

    def __post_init__(self):
        assert self.read_node.tid == self.dependent_node.tid
        assert self.read_node.is_overlap(self.write_node)
        assert not self.read_node.is_overlap(self.dependent_node)
        assert not self.write_node.is_overlap(self.dependent_node)

    @property
    def tid(self):
        return self.read_node.tid

    def __str__(self) -> str:
        s = []
        s.append('PERSISTENCY RACE!')
        s.append(f'W(X): {self.write_node}')
        s.append(f'R(X): {self.read_node}')
        s.append(f'W(Y): {self.dependent_node}')
        return '\n\t'.join(s)


class PersistencyRaces:
    def __init__(self):
        self._races:       Set[PersistencyRace]                       = set()
        self._races_by_pc: Dict[int, Dict[int, Set[PersistencyRace]]] = defaultdict(lambda: defaultdict(set))

    @property
    def races(self):
        return self._races
    
    @property
    def races_by_pc(self):
        return self._races_by_pc

    def add_race(self, race: PersistencyRace):
        self._races.add(race)

        read_already_saved  = race.read_node.pc  in self._races_by_pc
        write_already_saved = race.write_node.pc in self._races_by_pc[race.read_node.pc]
        self._races_by_pc[race.read_node.pc][race.write_node.pc].add(race)

    def clear(self):
        self._races.clear()
        self._races_by_pc.clear()

    def _get_race_nodes_by_pc(self) -> Generator[Tuple[int, ReadNode, WriteNode, Set[WriteNode]], None, None]:
        for i, read_pc in enumerate(self._races_by_pc):
            read_node = dependent_node = None
            write_nodes = set()
            for write_pc, races in self._races_by_pc[read_pc].items():
                race: PersistencyRace = next(iter(races))
                if not read_node:
                    read_node = race.read_node
                    dependent_node = race.dependent_node
                write_nodes.add(race.write_node)

            if read_node:
                yield i, read_node, dependent_node, write_nodes

    def __str__(self) -> str:
        all_lines = []

        for i, read_node, dependent_node, write_nodes in self._get_race_nodes_by_pc():
            lines = [
                f'Race {i+1:4}',
                f'R(X): {read_node.info}',
                f'W(Y): {dependent_node.info}',
            ]
            lines.extend([
                f'    W(X): {write_node.info}' for write_node in write_nodes
            ])

            all_lines.append('\n'.join(lines))

        return f'\n{"":-^20}\n'.join(all_lines)


class PersistencyRaceDetector:
    def __init__(self, hbg: HBG, pdg: PDG):
        self._hbg = hbg
        self._pdg = pdg
        self._races = PersistencyRaces()

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
            if pvc.is_event_persisted(*loc):
                continue

            # Find bugs
            daisy_chains = self._hbg.daisy_chains
            assert daisy_chains, "Can't find bugs without daisy chains"

            for tid in self._hbg.tids:
                last_persisted_epoch = pvc.get_persisted_epoch(tid)
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
                    if pvc.is_event_persisted(*write_node_loc):
                        continue

                    # Is happens after the read
                    if vc_per_read_node[read_node].is_happens_after(*write_node_loc):
                        break

                    # It is a bug! Report it!
                    race = PersistencyRace(read_node, write_node, dependent_node)
                    self._races.add_race(race)
                    yield race


    def _do_persisted_before_vector_clocks_analysis(self, vc_per_read_node: Dict[ReadNode, ReversedVectorClock], show_first_bug_only=False):
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
                    n: FlushNode
                    pvc: PersistencyVectorClock = pvc_per_thread[n.tid][n.get_cacheline_address()]
                    pvc.flush()
                    dirty_cachelines[n.tid].add(n.get_cacheline_address())

                case NodeType.EPOCH:
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

    def run(self, show_first_bug_only=False):
        self._races.clear()

        with utils.timeit('build_happens_after_vector_clocks O(N*T^2) ~ O(N)'):
            vc_per_read_node = self._build_happens_after_vector_clocks()

        with utils.timeit('Bug detection O(N*V*T^2 + B) ~ O(N*(B+V))'):
            return list(self._do_persisted_before_vector_clocks_analysis(vc_per_read_node, show_first_bug_only))
        
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
        
