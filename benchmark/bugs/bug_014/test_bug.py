from buggy import percentage

def test_quarter():
    assert percentage(1, 4) == 25.0

def test_full():
    assert percentage(5, 5) == 100.0
