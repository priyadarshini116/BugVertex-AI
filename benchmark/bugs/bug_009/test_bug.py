from buggy import count_down

def test_three():
    assert count_down(3) == [3, 2, 1]

def test_zero():
    assert count_down(0) == []
