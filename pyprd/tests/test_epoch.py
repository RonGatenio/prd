from epoch import Epoch


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
