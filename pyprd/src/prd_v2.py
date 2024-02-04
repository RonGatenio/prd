from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Tuple
from nodes import AbstractNode, NodeType, ReadNode, WriteNode, FlushNode, EpochNode
from vector_clock import PersistencyVectorClock, ReversedVectorClock
from hbg import HBG
from pdg import PDG
import utils


###########################################################
# Types
###########################################################
Var         = Tuple[int, int]
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
        space = 16
        s = []
        s.append('PERSISTENCY RACE!')
        s.append(f'{"Write Node: ":{space}}{self.write_node}')
        s.append(f'{"Read Node: ":{space}}{self.read_node}')
        s.append(f'{"Dependent Node: ":{space}}{self.dependent_node}')
        return '\n\t'.join(s)


class PersistencyRaceDetector:
    def __init__(self, hbg: HBG, pdg: PDG):
        self._hbg = hbg
        self._pdg = pdg
        
    @property
    def hbg(self):
        return self._hbg
    
    @property
    def pdg(self):
        return self._pdg
    
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
    
    def _do_persisted_before_vector_clocks_analysis(self, vc_per_read_node: Dict[ReadNode, ReversedVectorClock], show_first_bug_only=False):
        pvc_per_thread:     Dict[Cacheline, Dict[ThreadId, PersistencyVectorClock]]  = defaultdict(lambda: utils.DefaultDictByKey(lambda tid: PersistencyVectorClock(tid)))
        pvc_per_epoch_node: Dict[Cacheline, Dict[EpochNode, PersistencyVectorClock]] = defaultdict(lambda: utils.DefaultDictByKey(lambda n: PersistencyVectorClock(n.tid)))

        for n in self._hbg.reverse_postorder():
            n:   AbstractNode

            match n.itype:
                case NodeType.WRITE:
                    n: WriteNode
                    pvc: PersistencyVectorClock = pvc_per_thread[n.get_cacheline_address()][n.tid]
                    pvc.add_epoch(self._hbg.get_node_location(n).tindex)
                    
                    # Find bugs
                    for read_node in self._pdg.get_dependencies(n):
                        assert read_node.get_cacheline_address() != n.get_cacheline_address()
                        
                        pvc: PersistencyVectorClock = pvc_per_thread[read_node.get_cacheline_address()][n.tid]

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

                                write_node_loc = self._hbg.get_node_location(write_node)

                                # Is a different var
                                if not write_node.is_overlap(read_node):
                                    continue
                                
                                # Is already persisted
                                if pvc.is_event_persisted(*write_node_loc):
                                    continue

                                # Is happens after the read
                                if vc_per_read_node[read_node].is_happens_after(*write_node_loc):
                                    break

                                # It is a bug! Report it!
                                yield PersistencyRace(read_node, write_node, n)

                                if show_first_bug_only:
                                    break

                case NodeType.READ:
                    n: ReadNode
                    pvc: PersistencyVectorClock = pvc_per_thread[n.get_cacheline_address()][n.tid]
                    pvc.add_epoch(self._hbg.get_node_location(n).tindex)

                case NodeType.FLUSH:
                    n: FlushNode
                    pvc: PersistencyVectorClock = pvc_per_thread[n.get_cacheline_address()][n.tid]
                    pvc.flush()

                case NodeType.EPOCH:
                    n: EpochNode

                    for cacheline in pvc_per_thread:
                        pvc: PersistencyVectorClock = pvc_per_thread[cacheline][n.tid]

                        # Tell inter children the current state
                        for child in self._hbg.get_inter_children(n):
                            child: EpochNode
                            child_pvc: PersistencyVectorClock = pvc_per_epoch_node[cacheline][child]
                            child_pvc.merge(pvc)

                        # Merge my state with thread state and delete me
                        _pvc: ReversedVectorClock = pvc_per_epoch_node[cacheline][n]
                        pvc.merge(_pvc)
                        d = pvc_per_epoch_node[cacheline]
                        del d[n]

    def run(self, show_first_bug_only=False):
        with utils.timeit('build_happens_after_vector_clocks'):
            vc_per_read_node = self._build_happens_after_vector_clocks()

        with utils.timeit('Bug detection'):
            return list(self._do_persisted_before_vector_clocks_analysis(vc_per_read_node, show_first_bug_only))

