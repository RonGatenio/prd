from pdg import generate_mock_pdg_v2
from hbg import HBGBuilder


def test_mock_builder():
    # HBG
    b = HBGBuilder()

    var1 = 0x1000
    var2 = 0x2000
    var3 = 0x3000
    
    # thread 0
    w0_00 = b.add_instruction_node('WRITE', 0, 0, var2, 8)
    r0_01 = b.add_instruction_node('READ',  0, 0, var1, 8)
    f0_02 = b.add_instruction_node('FLUSH', 0, 0, var1, 64)
    e0_03 = b.add_epoch_node(0, 0)
    w0_04 = b.add_instruction_node('WRITE', 0, 0, var1, 8)
    w0_05 = b.add_instruction_node('WRITE', 0, 0, var2, 8)
    e0_06 = b.add_epoch_node(0, 1)
    w0_07 = b.add_instruction_node('WRITE', 0, 0, var1, 8)
    r0_08 = b.add_instruction_node('READ',  0, 0, var1, 8)
    w0_09 = b.add_instruction_node('WRITE', 0, 0, var2, 8)
    w0_10 = b.add_instruction_node('WRITE', 0, 0, var1, 8)
    w0_11 = b.add_instruction_node('WRITE', 0, 0, var2, 8)
    r0_12 = b.add_instruction_node('READ',  0, 0, var2, 8)
    w0_13 = b.add_instruction_node('WRITE', 0, 0, var2, 8)
    w0_14 = b.add_instruction_node('WRITE', 0, 0, var1, 8)
    w0_15 = b.add_instruction_node('WRITE', 0, 0, var2, 8)
    w0_16 = b.add_instruction_node('WRITE', 0, 0, var1, 8)
    r0_17 = b.add_instruction_node('READ',  0, 0, var1, 8)
    r0_18 = b.add_instruction_node('READ',  0, 0, var2, 8)
    r0_19 = b.add_instruction_node('READ',  0, 0, var3, 8)
    w0_20 = b.add_instruction_node('WRITE', 0, 0, var1, 8)
    w0_21 = b.add_instruction_node('WRITE', 0, 0, var2, 8)
    w0_22 = b.add_instruction_node('WRITE', 0, 0, var3, 8)
    w0_23 = b.add_instruction_node('WRITE', 0, 0, var1, 8)
    w0_24 = b.add_instruction_node('WRITE', 0, 0, var2, 8)
    w0_25 = b.add_instruction_node('WRITE', 0, 0, var3, 8)
    r0_26 = b.add_instruction_node('READ',  0, 0, var1, 8)

    # thread 1
    e1_00 = b.add_epoch_node(1, 0)
    f1_01 = b.add_instruction_node('FLUSH', 1, 0, var1, 64)
    w1_02 = b.add_instruction_node('WRITE', 1, 0, var1, 8)
    e1_03 = b.add_epoch_node(1, 1)
    r1_04 = b.add_instruction_node('READ',  1, 0, var2, 8)
    w1_05 = b.add_instruction_node('WRITE', 1, 0, var1, 8)
    e1_06 = b.add_epoch_node(1, 2)
    w1_07 = b.add_instruction_node('WRITE', 1, 0, var1, 8)

    # thread 2
    r2_00 = b.add_instruction_node('READ',  2, 0, var2, 8)
    w2_01 = b.add_instruction_node('WRITE', 2, 0, var1, 8)
    e2_02 = b.add_epoch_node(2, 0)
    w2_03 = b.add_instruction_node('WRITE', 2, 0, var1, 8)
    w2_04 = b.add_instruction_node('WRITE', 2, 0, var2, 8)
    w2_05 = b.add_instruction_node('WRITE', 2, 0, var2, 8)
    
    # edges
    b.add_happens_before_edge(2, 0, 1, 0)
    b.add_happens_before_edge(1, 1, 0, 0)
    b.add_happens_before_edge(0, 1, 1, 2)

    hbg = b.build(filter_volatile_nodes=False)

    pdg = generate_mock_pdg_v2(hbg)

    assert set(pdg.get_dependants(r0_01)) == {w0_05}
    assert set(pdg.get_dependants(r0_08)) == {w0_09}
    assert set(pdg.get_dependants(r0_12)) == {w0_14}
    assert set(pdg.get_dependants(r0_17)) == {w0_21}
    assert set(pdg.get_dependants(r0_18)) == {w0_20}
    assert set(pdg.get_dependants(r0_19)) == {w0_20}
    assert set(pdg.get_dependants(r0_26)) == set()

    assert set(pdg.get_dependants(r1_04)) == {w1_05}

    assert set(pdg.get_dependants(r2_00)) == {w2_01}


    assert set(pdg.get_dependencies(w0_00)) == set()
    assert set(pdg.get_dependencies(w0_04)) == set()
    assert set(pdg.get_dependencies(w0_05)) == {r0_01}
    assert set(pdg.get_dependencies(w0_07)) == set()
    assert set(pdg.get_dependencies(w0_09)) == {r0_08}
    assert set(pdg.get_dependencies(w0_10)) == set()
    assert set(pdg.get_dependencies(w0_11)) == set()
    assert set(pdg.get_dependencies(w0_13)) == set()
    assert set(pdg.get_dependencies(w0_14)) == {r0_12}
    assert set(pdg.get_dependencies(w0_15)) == set()
    assert set(pdg.get_dependencies(w0_16)) == set()
    assert set(pdg.get_dependencies(w0_20)) == {r0_18, r0_19}
    assert set(pdg.get_dependencies(w0_21)) == {r0_17}
    assert set(pdg.get_dependencies(w0_22)) == set()
    assert set(pdg.get_dependencies(w0_23)) == set()
    assert set(pdg.get_dependencies(w0_24)) == set()
    assert set(pdg.get_dependencies(w0_25)) == set()

    assert set(pdg.get_dependencies(w1_02)) == set()
    assert set(pdg.get_dependencies(w1_05)) == {r1_04}
    assert set(pdg.get_dependencies(w1_07)) == set()

    assert set(pdg.get_dependencies(w2_01)) == {r2_00}
    assert set(pdg.get_dependencies(w2_03)) == set()
    assert set(pdg.get_dependencies(w2_04)) == set()
    assert set(pdg.get_dependencies(w2_05)) == set()
