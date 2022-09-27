from typing import Dict, List, Set
from hbg import HBG, nodes, EdgeType


class HBGBuilder:
    def __init__(self):
        self._hbg = HBG()
        self._thread_tails: Dict[int, nodes.AbstractNode] = {}
        self._threads: Dict[int, List[nodes.AbstractNode]] = {}
        self._nodes: Dict[nodes.NodeType, Set[nodes.AbstractNode]] = {}
        
    def add_node(self, node: nodes.AbstractNode):
        # self._hbg.add_node(node, **{node.itype: True, 'itype': node.itype})
        self._hbg.add_node(node)
        
        self._hbg.nodes[node]['itype'] = node.itype
        self._hbg.nodes[node][node.itype] = True
        
        self._threads.setdefault(node.tid, []).append(node)
        self._nodes.setdefault(node.itype, set()).add(node)
        
        if node.tid in self._thread_tails:
            self._hbg.add_edge(self._thread_tails[node.tid], node, type=EdgeType.INTRA_THREAD)
            
        self._thread_tails[node.tid] = node
        
    def add_happens_before_edge(self, src: nodes.EpochNode, dst: nodes.EpochNode):
        assert src.tid != dst.tid, 'TIDs must be different'
        self._hbg.add_edge(src, dst, type=EdgeType.INTER_THREAD)
        
    def build(self) -> HBG:
        return self._hbg.__post_init__(self._threads, self._nodes)
