from buggy import find_max

def test_positive():
    assert find_max([3, 9, 2]) == 9

def test_all_negative():
    assert find_max([-5, -2, -9]) == -2
