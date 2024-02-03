from epoch import ReversedEpoch


def test_compare():
    assert not (ReversedEpoch(0) == ReversedEpoch(1))
    assert     (ReversedEpoch(0) != ReversedEpoch(1))
    assert not (ReversedEpoch(0) <  ReversedEpoch(1))
    assert not (ReversedEpoch(0) <= ReversedEpoch(1))
    assert     (ReversedEpoch(0) >  ReversedEpoch(1))
    assert     (ReversedEpoch(0) >= ReversedEpoch(1))


def test_compare_same():
    assert     (ReversedEpoch(0) == ReversedEpoch(0))
    assert not (ReversedEpoch(0) != ReversedEpoch(0))
    assert not (ReversedEpoch(0) <  ReversedEpoch(0))
    assert     (ReversedEpoch(0) <= ReversedEpoch(0))
    assert not (ReversedEpoch(0) >  ReversedEpoch(0))
    assert     (ReversedEpoch(0) >= ReversedEpoch(0))


def test_compare_min():
    assert not (ReversedEpoch(0) == ReversedEpoch())
    assert     (ReversedEpoch(0) != ReversedEpoch())
    assert not (ReversedEpoch(0) <  ReversedEpoch())
    assert not (ReversedEpoch(0) <= ReversedEpoch())
    assert     (ReversedEpoch(0) >  ReversedEpoch())
    assert     (ReversedEpoch(0) >= ReversedEpoch())


def test_compare_none():
    assert not (ReversedEpoch(0) == None)
    assert     (ReversedEpoch(0) != None)
    assert not (ReversedEpoch(0) <  None)
    assert not (ReversedEpoch(0) <= None)
    assert     (ReversedEpoch(0) >  None)
    assert     (ReversedEpoch(0) >= None)


def test_compare_min_left():
    assert not (ReversedEpoch() == ReversedEpoch(0))
    assert     (ReversedEpoch() != ReversedEpoch(0))
    assert     (ReversedEpoch() <  ReversedEpoch(0))
    assert     (ReversedEpoch() <= ReversedEpoch(0))
    assert not (ReversedEpoch() >  ReversedEpoch(0))
    assert not (ReversedEpoch() >= ReversedEpoch(0))


def test_compare_none_left():
    assert not (None == ReversedEpoch(0))
    assert     (None != ReversedEpoch(0))
    assert     (None <  ReversedEpoch(0))
    assert     (None <= ReversedEpoch(0))
    assert not (None >  ReversedEpoch(0))
    assert not (None >= ReversedEpoch(0))
