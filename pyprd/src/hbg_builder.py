from typing import Dict
from hbg import HBG, nodes, EdgeType


class HBGBuilder:
    def __init__(self):
        self._hbg = HBG()
        self.thread_tails: Dict[int, nodes.AbstractNode] = {}
        
    def add_node(self, node: nodes.AbstractNode):
        # self._hbg.add_node(node, **{node.itype: True, 'itype': node.itype})
        self._hbg.add_node(node)
        
        self._hbg.nodes[node]['tid'] = node.tid
        self._hbg.nodes[node][f'tid_{node.tid}'] = True
        self._hbg.nodes[node]['itype'] = node.itype
        self._hbg.nodes[node][node.itype] = True
        
        if node.tid in self.thread_tails:
            self._hbg.add_edge(self.thread_tails[node.tid], node, type=EdgeType.INTRA_THREAD)
            
        self.thread_tails[node.tid] = node
        
    def add_happens_before_edge(self, src: nodes.EpochNode, dst: nodes.EpochNode):
        assert src.tid != dst.tid, 'TIDs must be different'
        self._hbg.add_edge(src, dst, type=EdgeType.INTER_THREAD)
        
    def build(self) -> HBG:
        return self._hbg.__post_init__()
