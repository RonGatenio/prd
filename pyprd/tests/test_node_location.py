import pytest
from pyprd.hbg import NodeLocation


def test_compare_none():
    assert not (NodeLocation(0, 0) == None)
    assert     (NodeLocation(0, 0) != None)
    assert not (NodeLocation(0, 0) <  None)
    assert not (NodeLocation(0, 0) <= None)
    assert     (NodeLocation(0, 0) >  None)
    assert     (NodeLocation(0, 0) >= None)


def test_compare_left_none():
    assert not (None == NodeLocation(0, 0))
    assert     (None != NodeLocation(0, 0))
    assert     (None <  NodeLocation(0, 0))
    assert     (None <= NodeLocation(0, 0))
    assert not (None >  NodeLocation(0, 0))
    assert not (None >= NodeLocation(0, 0))


def test_compare_same_loc():
    assert     (NodeLocation(0, 0) == NodeLocation(0, 0))
    assert not (NodeLocation(0, 0) != NodeLocation(0, 0))
    assert not (NodeLocation(0, 0) <  NodeLocation(0, 0))
    assert     (NodeLocation(0, 0) <= NodeLocation(0, 0))
    assert not (NodeLocation(0, 0) >  NodeLocation(0, 0))
    assert     (NodeLocation(0, 0) >= NodeLocation(0, 0))


def test_compare_same_thread():
    assert not (NodeLocation(0, 0) == NodeLocation(0, 1))
    assert     (NodeLocation(0, 0) != NodeLocation(0, 1))
    assert     (NodeLocation(0, 0) <  NodeLocation(0, 1))
    assert     (NodeLocation(0, 0) <= NodeLocation(0, 1))
    assert not (NodeLocation(0, 0) >  NodeLocation(0, 1))
    assert not (NodeLocation(0, 0) >= NodeLocation(0, 1))


def test_compare_different_thread():
    with pytest.raises(NodeLocation.DifferentThreadsException):
        NodeLocation(0, 0) == NodeLocation(1, 0)
    with pytest.raises(NodeLocation.DifferentThreadsException):
        NodeLocation(0, 0) != NodeLocation(1, 0)
    with pytest.raises(NodeLocation.DifferentThreadsException):
        NodeLocation(0, 0) <  NodeLocation(1, 0)
    with pytest.raises(NodeLocation.DifferentThreadsException):
        NodeLocation(0, 0) <= NodeLocation(1, 0)
    with pytest.raises(NodeLocation.DifferentThreadsException):
        NodeLocation(0, 0) >  NodeLocation(1, 0)
    with pytest.raises(NodeLocation.DifferentThreadsException):
        NodeLocation(0, 0) >= NodeLocation(1, 0)


def test_compare_different_type():
    with pytest.raises(TypeError):
        NodeLocation(0, 0) == 0
    with pytest.raises(TypeError):
        NodeLocation(0, 0) != 0
    with pytest.raises(TypeError):
        NodeLocation(0, 0) <  0
    with pytest.raises(TypeError):
        NodeLocation(0, 0) <= 0
    with pytest.raises(TypeError):
        NodeLocation(0, 0) >  0
    with pytest.raises(TypeError):
        NodeLocation(0, 0) >= 0


def test_compare_left_different_type():
    with pytest.raises(TypeError):
        0 == NodeLocation(0, 0)
    with pytest.raises(TypeError):
        0 != NodeLocation(0, 0)
    with pytest.raises(TypeError):
        0 <  NodeLocation(0, 0)
    with pytest.raises(TypeError):
        0 <= NodeLocation(0, 0)
    with pytest.raises(TypeError):
        0 >  NodeLocation(0, 0)
    with pytest.raises(TypeError):
        0 >= NodeLocation(0, 0)
