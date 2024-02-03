from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Set, Tuple
from nodes import AbstractNode, NodeType, ReadNode, WriteNode, FlushNode, EpochNode, InstructionNode
from hbg import HBG, NodeLocation
from pdg import PDG
import networkx as nx
import utils
from copy import deepcopy

from vector_clock import ReversedVectorClock, VectorClock


###########################################################
# Types
###########################################################
Var         = Tuple[int, int]
ThreadId    = int


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

    def _get_first_dependent(self, read_node: InstructionNode) -> InstructionNode:
        return next(self.pdg.get_dependants(read_node))
    
    def build_happens_after_vector_clocks(self):
        vc_per_thread:     Dict[ThreadId, ReversedVectorClock]  = utils.DefaultDictByKey(lambda tid: ReversedVectorClock(tid))
        vc_per_epoch_node: Dict[EpochNode, ReversedVectorClock] = utils.DefaultDictByKey(lambda n: ReversedVectorClock(n.tid))
        vc_per_read_node:  Dict[ReadNode, ReversedVectorClock]  = utils.DefaultDictByKey(lambda n: ReversedVectorClock(n.tid))

        for n in self._hbg.postorder():
            n: AbstractNode
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
    
    def build_persisted_before_vector_clocks(self):
        vc_per_thread:     Dict[ThreadId, VectorClock]  = utils.DefaultDictByKey(lambda tid: VectorClock(tid))
