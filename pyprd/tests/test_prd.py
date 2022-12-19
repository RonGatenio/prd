import pytest
import prd
import groups
from utils import timeit


def setup_prd():
    pass


@pytest.mark.parametrize('p', setup_prd())
def fw_fr_tests(p: prd.PersistencyRaceDetector):
    hbg = p.hbg

    print(f'{" FW FR Tests ":*^30}')

    # op00
    with timeit('opt00 - delta groups -  using cahclines instead of vars'):
        delta_fw_op00, delta_fr_op00 = p.build_delta_fw_groups_opt00()

    # op0
    with timeit('opt0  - delta groups'):
        delta_fw_op0, delta_fr_op0 = p.build_delta_fw_groups_opt0()

    with timeit('opt0  - full groups (from the delta groups)'):
        fw_op0 = groups.build_fwr_groups_per_node(hbg, delta_fw_op0)
        fr_op0 = groups.build_fwr_groups_per_node(hbg, delta_fr_op0)

    # op1
    with timeit('opt1  - delta groups'):
        delta_fw_op1, delta_fr_op1 = p.build_delta_fw_groups_opt1()

    with timeit('opt1  - full groups (from the delta groups)'):
        fw_op1 = groups.build_fwr_groups_per_node(hbg, delta_fw_op1)
        fr_op1 = groups.build_fwr_groups_per_node(hbg, delta_fr_op1)

    # op2
    with timeit('opt2  - full groups'):
        fw_op2, fr_op2 = p.build_fw_groups_opt2()
        
    # op3
    with timeit('opt3  - delta groups'):
        delta_fw_op3, delta_fr_op3 = p.build_delta_fw_groups_opt3()

    with timeit('opt3  - full groups (from the delta groups)'):
        fw_op3 = groups.build_fwr_groups_per_node(hbg, delta_fw_op3)
        fr_op3 = groups.build_fwr_groups_per_node(hbg, delta_fr_op3)

    # assert compare(hbg, fw_op0, fw_op1)
    # assert compare(hbg, fw_op0, fw_op2)
    assert groups.compare(hbg, fw_op0, fw_op3)
    # assert compare(hbg, fr_op0, fr_op1)
    # assert compare(hbg, fr_op0, fr_op2)
    assert groups.compare(hbg, fr_op0, fr_op3)

    print(f'{"":*^30}')


def ha_tests(p: prd.PersistencyRaceDetector):
    hbg = p.hbg

    print(f'{" HA Tests ":*^30}')

    ## op1
    with timeit('opt1 - delta groups'):
        dop1 = p.build_delta_ha_groups_opt1()

    with timeit('opt1 - full groups (from the delta groups)'):
        op1 = build_ha_groups(hbg, dop1)

    with timeit('opt1 - the top full group per thread (from the delta groups)'):
        top1 = build_ha_groups_per_thread(hbg, dop1)

    for tid in hbg.tids:
        for n in hbg.get_thread_nodes(tid):
            if n.itype == 'READ':
                break
        if not compare(hbg, top1[tid], op1[n]):
            print('NOT EQUAL')

    ## op2
    with timeit('opt2 - delta groups'):
        dop2 = p.build_delta_ha_groups_opt2()

    with timeit('opt2 - full groups (from the delta groups)'):
        op2 = build_ha_groups(hbg, dop2)

    ## op3
    with timeit('opt3 - full groups'):
        op3 = p.build_ha_groups_opt3()

    # op4
    with timeit('opt4 - full groups - BFS from each READ'):
        op4 = p.build_ha_groups_opt4()

    assert compare(hbg, op1, op2)
    assert compare(hbg, op1, op3)
    assert compare(hbg, op1, op4)

    print(f'{"":*^30}')


def simple_test():
    b = HBGBuilder()
    r00 = b.add_instruction_node('READ', 0, 0, 0x1000, 8)
    f01 = b.add_instruction_node('FLUSH', 0, 0, 0x1000, 64)
    b.add_epoch_node(0, 0)
    w02 = b.add_instruction_node('WRITE', 0, 0, 0x2000, 8)
    b.add_epoch_node(1, 0)
    f10 = b.add_instruction_node('FLUSH', 1, 0, 0x1000, 64)
    w11 = b.add_instruction_node('WRITE', 1, 0, 0x1000, 8)
    b.add_epoch_node(1, 1)
    w20 = b.add_instruction_node('WRITE', 2, 0, 0x1000, 8)
    b.add_epoch_node(2, 0)
    b.add_happens_before_edge(2, 0, 1, 0)
    b.add_happens_before_edge(1, 1, 0, 0)

    hbg = b.build(False)
    pdg = generate_mock_pdg(hbg)
    p = prd.PersistencyRaceDetector(hbg, pdg)
    fw, fr = p.build_fw_groups_opt2()

    assert w11 not in fw[w02][w11.interval]
    assert w20 in fw[w02][w11.interval]
    assert r00 in fr[w02][w11.interval]


def test2(dbg=True):
    if dbg:
        print(f'{"Test 2":*^30}')
        
    b = HBGBuilder(dbg)
    
    v1 = 0x1000
    v2 = 0x2000
    v3 = 0x3000
    
    w11 = b.add_instruction_node('WRITE', 1, 0, v1, 8, 'w11')
    b.add_instruction_node('FLUSH', 1, 0, v1, 64)
    b.add_epoch_node(1, 0)
    w12 = b.add_instruction_node('WRITE', 1, 0, v1, 8, 'w12')
    b.add_instruction_node('FLUSH', 1, 0, v1, 64)
    b.add_epoch_node(1, 1)
    w13 = b.add_instruction_node('WRITE', 1, 0, v2, 8, 'w13')
    
    r21 = b.add_instruction_node('READ', 2, 0, v1, 8, 'r21')
    r22 = b.add_instruction_node('READ', 2, 0, v2, 8, 'r22')
    b.add_instruction_node('FLUSH', 2, 0, v2, 64)
    b.add_epoch_node(2, 0)
    w21 = b.add_instruction_node('WRITE', 2, 0, v1, 8, 'w21')
    b.add_epoch_node(2, 1)
    w22 = b.add_instruction_node('WRITE', 2, 0, v3, 8, 'w22')
    b.add_epoch_node(2, 2)
    w23 = b.add_instruction_node('WRITE', 2, 0, v2, 8, 'w23')
    
    w31 = b.add_instruction_node('WRITE', 3, 0, v1, 8, 'w31')
    w32 = b.add_instruction_node('WRITE', 3, 0, v2, 8, 'w32')
    b.add_instruction_node('FLUSH', 3, 0, v1, 64)
    b.add_epoch_node(3, 0)
    b.add_epoch_node(3, 1)
    w33 = b.add_instruction_node('WRITE', 3, 0, v1, 8, 'w33')
    b.add_instruction_node('FLUSH', 3, 0, v3, 64)
    
    b.add_happens_before_edge(1, 0, 2, 1)
    b.add_happens_before_edge(1, 1, 2, 2)
    b.add_happens_before_edge(2, 0, 1, 1)
    b.add_happens_before_edge(2, 0, 3, 1)
    b.add_happens_before_edge(3, 0, 2, 0)
    
    hbg = b.build()
    pdg = generate_mock_pdg(hbg)
    p = prd.PersistencyRaceDetector(hbg, pdg)
    
    delta_ha_groups = p.build_delta_ha_groups_opt1()
    delta_fw_groups, delta_fr_groups = p.build_delta_fw_groups_opt0()
    races = list(p.finale(delta_ha_groups, delta_fw_groups, delta_fr_groups))
        
    if dbg:
        print(races_to_str(p, races))
    
    assert len(races) == 1
    race, = races
    assert race.read_node == r21
    assert race.write_node == w22


def test3(dbg=True):
    if dbg:
        print(f'{"Test 3":*^30}')
        
    b = HBGBuilder(dbg)
    
    X = 0x1000
    Y = 0x2000
    Z = 0x3000
    
    w11 = b.add_instruction_node('WRITE', 1, 0, Z, 8, 'w11')
    w12 = b.add_instruction_node('WRITE', 1, 0, X, 8, 'w12')
    b.add_epoch_node(1, 0)
    b.add_instruction_node('FLUSH', 1, 0, X, 64)
    b.add_epoch_node(1, 1)
    w13 = b.add_instruction_node('WRITE', 1, 0, X, 8, 'w13')
    
    r21 = b.add_instruction_node('READ', 2, 0, X, 8, 'r21')
    r22 = b.add_instruction_node('READ', 2, 0, Z, 8, 'r22')
    b.add_instruction_node('FLUSH', 2, 0, Z, 64)
    b.add_epoch_node(2, 0)
    w21 = b.add_instruction_node('WRITE', 2, 0, Y, 8, 'w21')
    
    w31 = b.add_instruction_node('WRITE', 3, 0, X, 8, 'w31')
    b.add_instruction_node('FLUSH', 3, 0, X, 64)
    b.add_epoch_node(3, 0)
    w32 = b.add_instruction_node('WRITE', 3, 0, X, 8, 'w32')
    r31 = b.add_instruction_node('READ', 3, 0, Y, 8, 'r31')
    w33 = b.add_instruction_node('WRITE', 3, 0, Z, 8, 'w33')
    
    b.add_happens_before_edge(1, 0, 2, 0)
    b.add_happens_before_edge(2, 0, 1, 1)
    b.add_happens_before_edge(3, 0, 2, 0)
    
    hbg = b.build(False)
    pdg = generate_mock_pdg(hbg)
    p = prd.PersistencyRaceDetector(hbg, pdg)
    
    delta_ha_groups = p.build_delta_ha_groups_opt1()
    delta_fw_groups, delta_fr_groups = p.build_delta_fw_groups_opt0()
    races = list(p.finale(delta_ha_groups, delta_fw_groups, delta_fr_groups))
        
    if dbg:
        print(races_to_str(p, races))
    
    assert len(races) == 2
    
    races = {r.tid: r for r in races}
    
    assert races[2].read_node == r21
    assert races[2].write_node == w21
    
    assert races[3].read_node == r31
    assert races[3].write_node == w33
