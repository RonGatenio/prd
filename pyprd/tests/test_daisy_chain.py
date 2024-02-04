import pytest
from hbg import DaisyChain, DaisyChains
from nodes import WriteNode, ReadNode


def test_daisy_chain():
    d = DaisyChain()
    assert list(d.get_chain()) == []
    with pytest.raises(IndexError): list(d.get_chain(0))

    d.add_write_node(0)
    assert list(d.get_chain())  == [0]
    assert list(d.get_chain(0)) == [0]
    with pytest.raises(IndexError): list(d.get_chain(1))

    d.add_write_node(1)
    assert list(d.get_chain())  == [0, 1]
    assert list(d.get_chain(0)) == [0, 1]
    assert list(d.get_chain(1)) == [1]
    with pytest.raises(IndexError): list(d.get_chain(2))

    d.add_write_node(2)
    assert list(d.get_chain())  == [0, 1, 2]
    assert list(d.get_chain(0)) == [0, 1, 2]
    assert list(d.get_chain(1)) == [1, 2]
    assert list(d.get_chain(2)) == [2]
    with pytest.raises(IndexError): list(d.get_chain(3))

    d.add_write_node(10)
    d.add_write_node(-20)
    d.add_write_node(30)
    assert list(d.get_chain())    == [0, 1, 2, 10, -20, 30]
    assert list(d.get_chain(0))   == [0, 1, 2, 10, -20, 30]
    assert list(d.get_chain(1))   == [1, 2, 10, -20, 30]
    assert list(d.get_chain(2))   == [2, 10, -20, 30]
    assert list(d.get_chain(10))  == [10, -20, 30]
    assert list(d.get_chain(-20)) == [-20, 30]
    assert list(d.get_chain(30))  == [30]
    with pytest.raises(IndexError): list(d.get_chain(40))


def test_daisy_chain_reads():
    d = DaisyChain()

    d.add_read_node(10)
    d.add_read_node(11)
    d.add_write_node(0)
    d.add_write_node(1)
    d.add_read_node(12)
    d.add_write_node(2)
    d.add_read_node(13)
    d.add_write_node(3)
    d.add_read_node(14)
    d.add_read_node(15)
    d.add_read_node(16)
    d.add_write_node(4)
    d.add_read_node(17)

    assert list(d.get_chain())    == [0, 1, 2, 3, 4]
    assert list(d.get_chain(10))  == [0, 1, 2, 3, 4]
    assert list(d.get_chain(11))  == [0, 1, 2, 3, 4]
    assert list(d.get_chain(0))   == [0, 1, 2, 3, 4]
    assert list(d.get_chain(1))   == [1, 2, 3, 4]
    assert list(d.get_chain(12))  == [2, 3, 4]
    assert list(d.get_chain(2))   == [2, 3, 4]
    assert list(d.get_chain(13))  == [3, 4]
    assert list(d.get_chain(3))   == [3, 4]
    assert list(d.get_chain(14))  == [4]
    assert list(d.get_chain(15))  == [4]
    assert list(d.get_chain(16))  == [4]
    assert list(d.get_chain(4))   == [4]
    assert list(d.get_chain(17))  == []
    with pytest.raises(IndexError): list(d.get_chain(18))


def test_daisy_chains():
    d = DaisyChains()
    assert list(d.get_chain_by_thread(0, 0x1000)) == []

    n00 = d.add_write_node(WriteNode(0, 0, 0x1000, 8))
    assert list(d.get_chain_by_thread(0, 0x1000)) == [n00]
    assert list(d.get_chain_by_node(n00)) == [n00]

    n01 = d.add_write_node(WriteNode(0, 0, 0x1000, 8))
    assert list(d.get_chain_by_thread(0, 0x1000)) == [n00, n01]
    assert list(d.get_chain_by_node(n00)) == [n00, n01]
    assert list(d.get_chain_by_node(n01)) == [n01]

    n10 = d.add_write_node(WriteNode(1, 0, 0x1000, 8))
    assert list(d.get_chain_by_thread(0, 0x1000)) == [n00, n01]
    assert list(d.get_chain_by_thread(1, 0x1000)) == [n10]
    assert list(d.get_chain_by_thread(2, 0x1000)) == []
    assert list(d.get_chain_by_node(n00)) == [n00, n01]
    assert list(d.get_chain_by_node(n01)) == [n01]
    assert list(d.get_chain_by_node(n10)) == [n10]

    m02 = d.add_write_node(WriteNode(0, 0, 0x2000, 8))
    assert list(d.get_chain_by_thread(0, 0x1000)) == [n00, n01]
    assert list(d.get_chain_by_thread(0, 0x2000)) == [m02]
    assert list(d.get_chain_by_thread(1, 0x1000)) == [n10]
    assert list(d.get_chain_by_thread(1, 0x2000)) == []
    assert list(d.get_chain_by_thread(2, 0x1000)) == []
    assert list(d.get_chain_by_thread(2, 0x2000)) == []
    assert list(d.get_chain_by_node(n00)) == [n00, n01]
    assert list(d.get_chain_by_node(n01)) == [n01]
    assert list(d.get_chain_by_node(n10)) == [n10]
    assert list(d.get_chain_by_node(m02)) == [m02]


def test_daisy_chains_interleaving():
    d = DaisyChains()

    n00 = d.add_write_node(WriteNode(0, 0, 0x1000, 8))
    m01 = d.add_write_node(WriteNode(0, 0, 0x2000, 8))
    n02 = d.add_write_node(WriteNode(0, 0, 0x1000, 8))
    m03 = d.add_write_node(WriteNode(0, 0, 0x2000, 8))
    n04 = d.add_write_node(WriteNode(0, 0, 0x1000, 8))
    m05 = d.add_write_node(WriteNode(0, 0, 0x2000, 8))

    assert list(d.get_chain_by_thread(0, 0x1000)) == [n00, n02, n04]
    assert list(d.get_chain_by_thread(0, 0x2000)) == [m01, m03, m05]
    assert list(d.get_chain_by_node(n00)) == [n00, n02, n04]
    assert list(d.get_chain_by_node(n02)) == [n02, n04]
    assert list(d.get_chain_by_node(n04)) == [n04]
    assert list(d.get_chain_by_node(m01)) == [m01, m03, m05]
    assert list(d.get_chain_by_node(m03)) == [m03, m05]
    assert list(d.get_chain_by_node(m05)) == [m05]

