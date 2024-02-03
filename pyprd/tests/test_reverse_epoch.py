from epoch import ReverseEpoch


def test_compare():
    assert not (ReverseEpoch(0) == ReverseEpoch(1))
    assert     (ReverseEpoch(0) != ReverseEpoch(1))
    assert not (ReverseEpoch(0) <  ReverseEpoch(1))
    assert not (ReverseEpoch(0) <= ReverseEpoch(1))
    assert     (ReverseEpoch(0) >  ReverseEpoch(1))
    assert     (ReverseEpoch(0) >= ReverseEpoch(1))


def test_compare_same():
    assert     (ReverseEpoch(0) == ReverseEpoch(0))
    assert not (ReverseEpoch(0) != ReverseEpoch(0))
    assert not (ReverseEpoch(0) <  ReverseEpoch(0))
    assert     (ReverseEpoch(0) <= ReverseEpoch(0))
    assert not (ReverseEpoch(0) >  ReverseEpoch(0))
    assert     (ReverseEpoch(0) >= ReverseEpoch(0))


def test_compare_none():
    assert not (ReverseEpoch(0) == ReverseEpoch())
    assert     (ReverseEpoch(0) != ReverseEpoch())
    assert     (ReverseEpoch(0) <  ReverseEpoch())
    assert     (ReverseEpoch(0) <= ReverseEpoch())
    assert not (ReverseEpoch(0) >  ReverseEpoch())
    assert not (ReverseEpoch(0) >= ReverseEpoch())


def test_compare_none_left():
    assert not (ReverseEpoch() == ReverseEpoch(0))
    assert     (ReverseEpoch() != ReverseEpoch(0))
    assert not (ReverseEpoch() <  ReverseEpoch(0))
    assert not (ReverseEpoch() <= ReverseEpoch(0))
    assert     (ReverseEpoch() >  ReverseEpoch(0))
    assert     (ReverseEpoch() >= ReverseEpoch(0))
