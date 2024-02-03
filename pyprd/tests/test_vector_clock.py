import pytest
from vector_clock import VectorClock, PersistencyVectorClock


def test_sanity():
    vc = VectorClock(0)

    assert vc.get_epoch(0) == None
    assert vc.get_epoch(1) == None

    vc.add_epoch(11)

    assert vc.get_epoch(0) == 11
    assert vc.get_epoch(1) == None

    vc1 = VectorClock(1)
    vc1.add_epoch(22)

    assert vc.get_epoch(0) == 11
    assert vc.get_epoch(1) == None

    vc.merge(vc1)

    assert vc.get_epoch(0) == 11
    assert vc.get_epoch(1) == 22

    with pytest.raises(AssertionError, match="Can't change epoch"):
        vc.add_epoch(10)

    assert vc.get_epoch(0) == 11
    assert vc.get_epoch(1) == 22


def test_flush():
    vc = PersistencyVectorClock(0)
    assert vc.is_persisted()
    assert vc.get_persisted_epoch(0) == None

    vc.add_epoch(0)
    assert not vc.is_persisted()
    assert vc.get_persisted_epoch(0) == None

    vc.flush()
    assert vc.is_persisted()
    assert vc.get_persisted_epoch(0) == 0

    vc.add_epoch(5)
    assert not vc.is_persisted()
    assert vc.get_persisted_epoch(0) == 0

    vc.flush()
    assert vc.is_persisted()
    assert vc.get_persisted_epoch(0) == 5


def test_merge():
    vc0 = PersistencyVectorClock(0)
    vc1 = PersistencyVectorClock(1)

    assert vc0.is_persisted()
    assert vc1.is_persisted()

    vc0.add_epoch(0)
    vc1.add_epoch(0)

    assert not vc0.is_persisted()
    assert not vc1.is_persisted()

    vc1.merge(vc0)

    assert not vc0.is_persisted()
    assert not vc1.is_persisted()

    vc1.flush()

    assert not vc0.is_persisted()
    assert vc1.is_persisted()

    vc0.add_epoch(1)

    assert not vc0.is_persisted()
    assert vc1.is_persisted()

    vc0.merge(vc1)

    assert not vc0.is_persisted()
    assert vc1.is_persisted()

    vc1.merge(vc0)

    assert not vc0.is_persisted()
    assert not vc1.is_persisted()

