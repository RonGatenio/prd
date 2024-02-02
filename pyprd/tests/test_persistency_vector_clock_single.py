import pytest
from prd_otf import PersistencyVectorClockSingleEventType, NodeLocation


def test_sanity():
    vc = PersistencyVectorClockSingleEventType(0)

    assert vc.is_persisted()

    with pytest.raises(AssertionError):
        vc.add_event(NodeLocation(1, 1))

    assert vc.is_persisted()

    vc.add_event(NodeLocation(0, 1))

    assert not vc.is_persisted()

    vc.flush()

    assert vc.is_persisted()

    with pytest.raises(AssertionError):
        vc.add_event(NodeLocation(0, 1))

    vc.add_event(NodeLocation(0, 2))

    assert not vc.is_persisted()


def test_flush():
    vc = PersistencyVectorClockSingleEventType(0)

    vc.add_event(NodeLocation(0, 0))
    assert not vc.is_persisted()

    vc.flush()
    assert vc.is_persisted()

    vc.add_event(NodeLocation(0, 5))
    assert not vc.is_persisted()

    vc.flush()
    assert vc.is_persisted()

    with pytest.raises(AssertionError, match='New location is in the past'):
        vc.add_event(NodeLocation(0, 3))

    vc._last_seen[vc.tid] = NodeLocation(0, 3)

    with pytest.raises(AssertionError, match='Persisting a past value'):
        vc.flush()


def test_merge():
    vc0 = PersistencyVectorClockSingleEventType(0)
    vc1 = PersistencyVectorClockSingleEventType(1)

    assert vc0.is_persisted()
    assert vc1.is_persisted()

    vc0.add_event(NodeLocation(0, 0))
    vc1.add_event(NodeLocation(1, 0))

    assert not vc0.is_persisted()
    assert not vc1.is_persisted()

    vc1.merge(vc0)

    assert not vc0.is_persisted()
    assert not vc1.is_persisted()

    vc1.flush()

    assert not vc0.is_persisted()
    assert vc1.is_persisted()

    vc0.add_event(NodeLocation(0, 1))

    assert not vc0.is_persisted()
    assert vc1.is_persisted()

    vc0.merge(vc1)

    assert not vc0.is_persisted()
    assert vc1.is_persisted()

    vc1.merge(vc0)

    assert not vc0.is_persisted()
    assert not vc1.is_persisted()
