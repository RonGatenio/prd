import pytest
from pyprd.epoch import Epoch


def test_compare():
    assert not (Epoch(0) == Epoch(1))
    assert     (Epoch(0) != Epoch(1))
    assert     (Epoch(0) <  Epoch(1))
    assert     (Epoch(0) <= Epoch(1))
    assert not (Epoch(0) >  Epoch(1))
    assert not (Epoch(0) >= Epoch(1))


def test_compare_same():
    assert     (Epoch(0) == Epoch(0))
    assert not (Epoch(0) != Epoch(0))
    assert not (Epoch(0) <  Epoch(0))
    assert     (Epoch(0) <= Epoch(0))
    assert not (Epoch(0) >  Epoch(0))
    assert     (Epoch(0) >= Epoch(0))


def test_compare_min():
    assert not (Epoch(0) == Epoch())
    assert     (Epoch(0) != Epoch())
    assert not (Epoch(0) <  Epoch())
    assert not (Epoch(0) <= Epoch())
    assert     (Epoch(0) >  Epoch())
    assert     (Epoch(0) >= Epoch())


def test_compare_none():
    assert not (Epoch(0) == None)
    assert     (Epoch(0) != None)
    assert not (Epoch(0) <  None)
    assert not (Epoch(0) <= None)
    assert     (Epoch(0) >  None)
    assert     (Epoch(0) >= None)


def test_compare_min_left():
    assert not (Epoch() == Epoch(0))
    assert     (Epoch() != Epoch(0))
    assert     (Epoch() <  Epoch(0))
    assert     (Epoch() <= Epoch(0))
    assert not (Epoch() >  Epoch(0))
    assert not (Epoch() >= Epoch(0))


def test_compare_none_left():
    assert not (None == Epoch(0))
    assert     (None != Epoch(0))
    assert     (None <  Epoch(0))
    assert     (None <= Epoch(0))
    assert not (None >  Epoch(0))
    assert not (None >= Epoch(0))


def test_copy():
    e1 = Epoch()
    e2 = Epoch(e1)

    assert e1 == e2
    assert e1 < Epoch(-1) < Epoch(0) < Epoch(1)
    assert e2 < Epoch(-1) < Epoch(0) < Epoch(1)


def test_order():
    assert Epoch() == None < Epoch(-1) == -1 < Epoch(0) == 0 < Epoch(1) == 1 < Epoch(2) < 3 <= Epoch(3)


def test_convert():
    with pytest.raises(TypeError):
        int(Epoch())
    
    assert int(Epoch(0))  == 0
    assert int(Epoch(1))  == 1
    assert int(Epoch(-1)) == -1

