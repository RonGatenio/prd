import pytest
from nodes import NodeType
from prd_v2 import PersistencyRaceDetector
from pdg import PDG, PDGBuilder
from hbg import HBG, HBGBuilder
from vector_clock import VectorClock


def setup() -> (HBG, PDG):
    # HBG
    b = HBGBuilder()
    
    # thread 0
    r00 = b.add_instruction_node('READ', 0, 0, 0x1000, 8)
    f01 = b.add_instruction_node('FLUSH', 0, 0, 0x1000, 64)
    e02 = b.add_epoch_node(0, 0)
    w03 = b.add_instruction_node('WRITE', 0, 0, 0x2000, 8)
    e04 = b.add_epoch_node(0, 1)
    
    # thread 1
    e10 = b.add_epoch_node(1, 0)
    f11 = b.add_instruction_node('FLUSH', 1, 0, 0x1000, 64)
    w12 = b.add_instruction_node('WRITE', 1, 0, 0x1000, 8)
    e13 = b.add_epoch_node(1, 1)
    w14 = b.add_instruction_node('WRITE', 1, 0, 0x1000, 8)
    e15 = b.add_epoch_node(1, 2)
    w16 = b.add_instruction_node('WRITE', 1, 0, 0x1000, 8)

    # thread 2
    w20 = b.add_instruction_node('WRITE', 2, 0, 0x1000, 8)
    e21 = b.add_epoch_node(2, 0)
    
    # edges
    b.add_happens_before_edge(2, 0, 1, 0)
    b.add_happens_before_edge(1, 1, 0, 0)
    b.add_happens_before_edge(0, 1, 1, 2)

    return [(b.build(filter_volatile_nodes=False), None)]


@pytest.mark.parametrize('hbg,pdg', setup())
def test_happens_after_vector_clocks(hbg: HBG, pdg: PDG):
    prd = PersistencyRaceDetector(hbg, pdg)
    vcs = prd.build_happens_after_vector_clocks()

    r00 = hbg.get_node_by_location((0, 0))
    w03 = hbg.get_node_by_location((0, 3))
    w12 = hbg.get_node_by_location((1, 2))
    w14 = hbg.get_node_by_location((1, 4))
    w16 = hbg.get_node_by_location((1, 6))
    w20 = hbg.get_node_by_location((2, 0))

    assert NodeType.READ == r00.itype
    assert NodeType.WRITE == w03.itype
    assert NodeType.WRITE == w12.itype
    assert NodeType.WRITE == w14.itype
    assert NodeType.WRITE == w16.itype
    assert NodeType.WRITE == w20.itype

    vc00: VectorClock = vcs[r00]
    assert     vc00.is_happens_after(0, 3)
    assert not vc00.is_happens_after(1, 2)
    assert not vc00.is_happens_after(1, 4)
    assert     vc00.is_happens_after(1, 6)
    assert not vc00.is_happens_after(2, 0)

