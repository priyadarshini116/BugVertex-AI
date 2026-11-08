from buggy import is_adult

def test_adult():
    assert is_adult(30) is True

def test_exactly_18():
    assert is_adult(18) is True

def test_child():
    assert is_adult(10) is False
