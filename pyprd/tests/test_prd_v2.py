import pytest
from nodes import EpochNode, NodeType
from prd_v2 import PersistencyRace, PersistencyRaceDetector
from pdg import PDG, PDGBuilder, generate_mock_pdg_v2
from hbg import HBG, HBGBuilder
from vector_clock import VectorClock


def add_edge(b: HBGBuilder, e1: EpochNode, e2: EpochNode):
    b.add_happens_before_edge(e1.tid, e1.epoch, e2.tid, e2.epoch)


def test_happens_after_vector_clocks():
    # Vars
    var1 = 0x1000
    var2 = 0x2000

    # HBG
    b = HBGBuilder()
    
    # Thread 0
    r00 = b.add_instruction_node('READ',  0, 0, var1, 8, 'r00')
    f01 = b.add_instruction_node('FLUSH', 0, 0, var1, 64, 'f01')
    e02 = b.add_epoch_node(0, 0)
    w03 = b.add_instruction_node('WRITE', 0, 0, var2, 8, 'w03')
    e04 = b.add_epoch_node(0, 1)
    
    # Thread 1
    e10 = b.add_epoch_node(1, 0)
    f11 = b.add_instruction_node('FLUSH', 1, 0, var1, 64, 'f11')
    w12 = b.add_instruction_node('WRITE', 1, 0, var1, 8, 'w12')
    e13 = b.add_epoch_node(1, 1)
    w14 = b.add_instruction_node('WRITE', 1, 0, var1, 8, 'w14')
    e15 = b.add_epoch_node(1, 2)
    w16 = b.add_instruction_node('WRITE', 1, 0, var1, 8, 'w16')

    # Thread 2
    w20 = b.add_instruction_node('WRITE', 2, 0, var1, 8, 'w20')
    e21 = b.add_epoch_node(2, 0)
    
    # Edges
    b.add_happens_before_edge(2, 0, 1, 0)
    b.add_happens_before_edge(1, 1, 0, 0)
    b.add_happens_before_edge(0, 1, 1, 2)

    hbg = b.build(filter_volatile_nodes=False)

    prd = PersistencyRaceDetector(hbg, None)

    vcs = prd._build_happens_after_vector_clocks()

    assert NodeType.READ  == r00.itype
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


def test_races_sanity():
    # Vars
    var1 = 0x1000
    var2 = 0x2000
    var3 = 0x3000

    # HBG
    b = HBGBuilder()
    
    # Thread 0
    w0_00 = b.add_instruction_node('WRITE', 0, 0, var3, 8,  'w0_00')
    w0_01 = b.add_instruction_node('WRITE', 0, 0, var1, 8,  'w0_01')
    e0_02 = b.add_epoch_node(0, 2)
    f0_03 = b.add_instruction_node('FLUSH', 0, 0, var1, 64, 'f0_03')
    e0_04 = b.add_epoch_node(0, 4)
    w0_05 = b.add_instruction_node('WRITE', 0, 0, var1, 8,  'w0_05')
    
    # Thread 1
    r1_00 = b.add_instruction_node('READ',  1, 0, var1, 8,  'r1_00')
    r1_01 = b.add_instruction_node('READ',  1, 0, var3, 8,  'r1_01')
    f1_02 = b.add_instruction_node('FLUSH', 1, 0, var3, 64, 'f1_02')
    e1_03 = b.add_epoch_node(1, 3)
    w1_04 = b.add_instruction_node('WRITE', 1, 0, var2, 8,  'w1_04')
    
    # Thread 2
    w2_00 = b.add_instruction_node('WRITE', 2, 0, var1, 8,  'w2_00')
    f2_01 = b.add_instruction_node('FLUSH', 2, 0, var1, 64, 'f2_01')
    e2_02 = b.add_epoch_node(2, 2)
    w2_03 = b.add_instruction_node('WRITE', 2, 0, var1, 8,  'w2_03')
    r2_04 = b.add_instruction_node('READ',  2, 0, var2, 8,  'r2_04')
    w2_05 = b.add_instruction_node('WRITE', 2, 0, var3, 8,  'w2_05')
    
    # Edges
    add_edge(b, e0_02, e1_03)
    add_edge(b, e1_03, e0_04)
    add_edge(b, e2_02, e1_03)

    hbg = b.build(filter_volatile_nodes=False)
    pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    assert set(prd.run()) == {
            PersistencyRace(r1_00, w0_01, w1_04),
            PersistencyRace(r1_00, w2_03, w1_04),
            PersistencyRace(r2_04, w1_04, w2_05),
        }


def test_races_sanity2():
    # Vars
    var1 = 0x1000
    var2 = 0x2000
    var3 = 0x3000

    # HBG
    b = HBGBuilder()
    
    # Thread 0
    w0_00 = b.add_instruction_node('WRITE', 0, 0, var1, 8,  'w0_00')
    f0_01 = b.add_instruction_node('FLUSH', 0, 0, var1, 64, 'f0_01')
    e0_02 = b.add_epoch_node(0, 2)
    w0_03 = b.add_instruction_node('WRITE', 0, 0, var1, 8,  'w0_03')
    f0_04 = b.add_instruction_node('FLUSH', 0, 0, var1, 64, 'f0_04')
    e0_05 = b.add_epoch_node(0, 5)
    w0_06 = b.add_instruction_node('WRITE', 0, 0, var2, 8,  'w0_06')
    
    # Thread 1
    r1_00 = b.add_instruction_node('READ',  1, 0, var1, 8,  'r1_00')
    r1_01 = b.add_instruction_node('READ',  1, 0, var2, 8,  'r1_01')
    f1_02 = b.add_instruction_node('FLUSH', 1, 0, var2, 64, 'f1_02')
    e1_03 = b.add_epoch_node(1, 3)
    w1_04 = b.add_instruction_node('WRITE', 1, 0, var1, 8,  'w1_04')
    e1_05 = b.add_epoch_node(1, 5)
    w1_06 = b.add_instruction_node('WRITE', 1, 0, var3, 8,  'w1_06')
    e1_07 = b.add_epoch_node(1, 7)
    w1_08 = b.add_instruction_node('WRITE', 1, 0, var2, 8,  'w1_08')
    
    # Thread 2
    w2_00 = b.add_instruction_node('WRITE', 2, 0, var1, 8,  'w2_00')
    w2_01 = b.add_instruction_node('WRITE', 2, 0, var2, 8,  'w2_01')
    f2_02 = b.add_instruction_node('FLUSH', 2, 0, var1, 64, 'f2_02')
    e2_03 = b.add_epoch_node(2, 3)
    e2_04 = b.add_epoch_node(2, 4)
    w2_05 = b.add_instruction_node('WRITE', 2, 0, var1, 8,  'w2_05')
    f2_06 = b.add_instruction_node('FLUSH', 2, 0, var3, 64, 'f2_06')
    
    # Edges
    add_edge(b, e0_02, e2_04)
    add_edge(b, e0_05, e1_07)
    add_edge(b, e1_03, e0_05)
    add_edge(b, e1_03, e2_04)
    add_edge(b, e2_03, e1_03)

    hbg = b.build(filter_volatile_nodes=False)
    pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    assert set(prd.run()) == {
            PersistencyRace(r1_00, w0_00, w1_06),
            PersistencyRace(r1_00, w0_03, w1_06),
        }


def test_races_flushed_in_different_thread_before_read():
    # Vars
    var1 = 0x1000
    var2 = 0x2000

    # HBG
    b = HBGBuilder()
    
    # Thread 0
    w0_00 = b.add_instruction_node('WRITE', 0, 0, var1, 8, 'w0_00')
    e0_01 = b.add_epoch_node(0, 1)
    e0_02 = b.add_epoch_node(0, 2)
    r0_03 = b.add_instruction_node('READ',  0, 0, var1, 8, 'r0_03')
    w0_04 = b.add_instruction_node('WRITE', 0, 0, var2, 8, 'w0_04')

    # Thread 1
    e1_00 = b.add_epoch_node(1, 0)
    f1_01 = b.add_instruction_node('FLUSH', 1, 0, var1, 64, 'f1_01')
    e1_02 = b.add_epoch_node(1, 2)
    
    # Edges
    b.add_happens_before_edge(0, 1, 1, 0)
    b.add_happens_before_edge(1, 2, 0, 2)

    hbg = b.build(filter_volatile_nodes=False)
    pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    assert set(prd.run()) == set()


def test_races_flushed_in_different_thread_before_read_but_masked_out_before_read_1():
    # Vars
    var1 = 0x1000
    var2 = 0x2000

    # HBG
    b = HBGBuilder()
    
    # Thread 0
    w0_00 = b.add_instruction_node('WRITE', 0, 0, var1, 8, 'w0_00')
    e0_01 = b.add_epoch_node(0, 1)
    e0_02 = b.add_epoch_node(0, 2)
    r0_03 = b.add_instruction_node('READ',  0, 0, var1, 8, 'r0_03')
    e0_04 = b.add_epoch_node(0, 4)
    e0_05 = b.add_epoch_node(0, 5)
    w0_06 = b.add_instruction_node('WRITE', 0, 0, var2, 8, 'w0_06')

    # Thread 1
    e1_00 = b.add_epoch_node(1, 0)
    f1_01 = b.add_instruction_node('FLUSH', 1, 0, var1, 64, 'f1_01')
    e1_02 = b.add_epoch_node(1, 2)
    e1_03 = b.add_epoch_node(1, 3)
    w1_04 = b.add_instruction_node('WRITE', 1, 0, var1, 8, 'w1_04')
    e1_05 = b.add_epoch_node(1, 5)
    
    # Edges
    b.add_happens_before_edge(0, 1, 1, 0)
    b.add_happens_before_edge(1, 2, 0, 2)
    b.add_happens_before_edge(1, 5, 0, 5)

    hbg = b.build(filter_volatile_nodes=False)
    pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    assert set(prd.run()) == {PersistencyRace(r0_03, w1_04, w0_06)}


def test_races_flushed_in_different_thread_before_read_but_masked_out_before_read_2():
    # Vars
    var1 = 0x1000
    var2 = 0x2000

    # HBG
    b = HBGBuilder()
    
    # Thread 0
    w0_00 = b.add_instruction_node('WRITE', 0, 0, var1, 8, 'w0_00')
    e0_01 = b.add_epoch_node(0, 1)
    e0_02 = b.add_epoch_node(0, 2)
    r0_03 = b.add_instruction_node('READ',  0, 0, var1, 8, 'r0_03')
    e0_04 = b.add_epoch_node(0, 4)
    e0_05 = b.add_epoch_node(0, 5)
    w0_06 = b.add_instruction_node('WRITE', 0, 0, var2, 8, 'w0_06')

    # Thread 1
    e1_00 = b.add_epoch_node(1, 0)
    f1_01 = b.add_instruction_node('FLUSH', 1, 0, var1, 64, 'f1_01')
    e1_02 = b.add_epoch_node(1, 2)
    e1_03 = b.add_epoch_node(1, 3)
    w1_04 = b.add_instruction_node('WRITE', 1, 0, var1, 8, 'w1_04')
    e1_05 = b.add_epoch_node(1, 5)
    
    # Edges
    b.add_happens_before_edge(0, 1, 1, 0)
    b.add_happens_before_edge(1, 2, 0, 2)

    hbg = b.build(filter_volatile_nodes=False)
    pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    assert set(prd.run()) == {PersistencyRace(r0_03, w1_04, w0_06)}


def test_races_flushed_in_different_thread_before_read_but_masked_out_after_read_1():
    # Vars
    var1 = 0x1000
    var2 = 0x2000

    # HBG
    b = HBGBuilder()
    
    # Thread 0
    w0_00 = b.add_instruction_node('WRITE', 0, 0, var1, 8, 'w0_00')
    e0_01 = b.add_epoch_node(0, 1)
    e0_02 = b.add_epoch_node(0, 2)
    r0_03 = b.add_instruction_node('READ',  0, 0, var1, 8, 'r0_03')
    e0_04 = b.add_epoch_node(0, 4)
    e0_05 = b.add_epoch_node(0, 5)
    w0_06 = b.add_instruction_node('WRITE', 0, 0, var2, 8, 'w0_06')

    # Thread 1
    e1_00 = b.add_epoch_node(1, 0)
    f1_01 = b.add_instruction_node('FLUSH', 1, 0, var1, 64, 'f1_01')
    e1_02 = b.add_epoch_node(1, 2)
    e1_03 = b.add_epoch_node(1, 3)
    w1_04 = b.add_instruction_node('WRITE', 1, 0, var1, 8, 'w1_04')
    e1_05 = b.add_epoch_node(1, 5)
    
    # Edges
    b.add_happens_before_edge(0, 1, 1, 0)
    b.add_happens_before_edge(1, 2, 0, 2)
    b.add_happens_before_edge(0, 4, 1, 3)
    b.add_happens_before_edge(1, 5, 0, 5)

    hbg = b.build(filter_volatile_nodes=False)
    pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    assert set(prd.run()) == set()


def test_races_flushed_in_different_thread_before_read_but_masked_out_after_read_2():
    # Vars
    var1 = 0x1000
    var2 = 0x2000

    # HBG
    b = HBGBuilder()
    
    # Thread 0
    w0_00 = b.add_instruction_node('WRITE', 0, 0, var1, 8, 'w0_00')
    e0_01 = b.add_epoch_node(0, 1)
    e0_02 = b.add_epoch_node(0, 2)
    r0_03 = b.add_instruction_node('READ',  0, 0, var1, 8, 'r0_03')
    e0_04 = b.add_epoch_node(0, 4)
    e0_05 = b.add_epoch_node(0, 5)
    w0_06 = b.add_instruction_node('WRITE', 0, 0, var2, 8, 'w0_06')

    # Thread 1
    e1_00 = b.add_epoch_node(1, 0)
    f1_01 = b.add_instruction_node('FLUSH', 1, 0, var1, 64, 'f1_01')
    e1_02 = b.add_epoch_node(1, 2)
    e1_03 = b.add_epoch_node(1, 3)
    w1_04 = b.add_instruction_node('WRITE', 1, 0, var1, 8, 'w1_04')
    e1_05 = b.add_epoch_node(1, 5)
    
    # Edges
    b.add_happens_before_edge(0, 1, 1, 0)
    b.add_happens_before_edge(1, 2, 0, 2)
    b.add_happens_before_edge(0, 4, 1, 3)

    hbg = b.build(filter_volatile_nodes=False)
    pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    assert set(prd.run()) == set()


def test_races_flushed_in_different_thread_after_read_1():
    # Vars
    var1 = 0x1000
    var2 = 0x2000

    # HBG
    b = HBGBuilder()
    
    # Thread 0
    w0_00 = b.add_instruction_node('WRITE', 0, 0, var1, 8, 'w0_00')
    e0_01 = b.add_epoch_node(0, 1)
    e0_02 = b.add_epoch_node(0, 2)
    r0_03 = b.add_instruction_node('READ',  0, 0, var1, 8, 'r0_03')
    e0_04 = b.add_epoch_node(0, 4)
    e0_05 = b.add_epoch_node(0, 5)
    w0_06 = b.add_instruction_node('WRITE', 0, 0, var2, 8, 'w0_06')

    # Thread 1
    e1_00 = b.add_epoch_node(1, 0)
    f1_01 = b.add_instruction_node('FLUSH', 1, 0, var1, 64, 'f1_01')
    e1_02 = b.add_epoch_node(1, 2)
    e1_03 = b.add_epoch_node(1, 3)
    w1_04 = b.add_instruction_node('WRITE', 1, 0, var1, 8, 'w1_04')
    e1_05 = b.add_epoch_node(1, 5)
    
    # Edges
    b.add_happens_before_edge(0, 4, 1, 0)
    b.add_happens_before_edge(1, 5, 0, 5)

    hbg = b.build(filter_volatile_nodes=False)
    pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    assert set(prd.run()) == set()


def test_races_flushed_in_different_thread_after_read_2():
    # Vars
    var1 = 0x1000
    var2 = 0x2000

    # HBG
    b = HBGBuilder()
    
    # Thread 0
    w0_00 = b.add_instruction_node('WRITE', 0, 0, var1, 8, 'w0_00')
    e0_01 = b.add_epoch_node(0, 1)
    e0_02 = b.add_epoch_node(0, 2)
    r0_03 = b.add_instruction_node('READ',  0, 0, var1, 8, 'r0_03')
    e0_04 = b.add_epoch_node(0, 4)
    e0_05 = b.add_epoch_node(0, 5)
    w0_06 = b.add_instruction_node('WRITE', 0, 0, var2, 8, 'w0_06')

    # Thread 1
    e1_00 = b.add_epoch_node(1, 0)
    f1_01 = b.add_instruction_node('FLUSH', 1, 0, var1, 64, 'f1_01')
    e1_02 = b.add_epoch_node(1, 2)
    e1_03 = b.add_epoch_node(1, 3)
    w1_04 = b.add_instruction_node('WRITE', 1, 0, var1, 8, 'w1_04')
    e1_05 = b.add_epoch_node(1, 5)
    
    # Edges
    b.add_happens_before_edge(0, 4, 1, 0)
    b.add_happens_before_edge(1, 3, 0, 5)

    hbg = b.build(filter_volatile_nodes=False)
    pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    assert set(prd.run()) == set()


def test_races_no_edges():
    # Vars
    var1 = 0x1000
    var2 = 0x2000

    # HBG
    b = HBGBuilder()
    
    # Thread 0
    w0_00 = b.add_instruction_node('WRITE', 0, 0, var1, 8, 'w0_00')
    e0_01 = b.add_epoch_node(0, 1)
    e0_02 = b.add_epoch_node(0, 2)
    r0_03 = b.add_instruction_node('READ',  0, 0, var1, 8, 'r0_03')
    e0_04 = b.add_epoch_node(0, 4)
    e0_05 = b.add_epoch_node(0, 5)
    w0_06 = b.add_instruction_node('WRITE', 0, 0, var2, 8, 'w0_06')

    # Thread 1
    e1_00 = b.add_epoch_node(1, 0)
    f1_01 = b.add_instruction_node('FLUSH', 1, 0, var1, 64, 'f1_01')
    e1_02 = b.add_epoch_node(1, 2)
    e1_03 = b.add_epoch_node(1, 3)
    w1_04 = b.add_instruction_node('WRITE', 1, 0, var1, 8, 'w1_04')
    e1_05 = b.add_epoch_node(1, 5)
    
    # No edges

    hbg = b.build(filter_volatile_nodes=False)
    pdg = generate_mock_pdg_v2(hbg)

    prd = PersistencyRaceDetector(hbg, pdg)

    assert set(prd.run()) == {PersistencyRace(r0_03, w0_00, w0_06), PersistencyRace(r0_03, w1_04, w0_06)}
