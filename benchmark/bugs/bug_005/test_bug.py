from buggy import sum_first_n

def test_three():
    assert sum_first_n([1, 2, 3, 4], 3) == 6

def test_all():
    assert sum_first_n([5, 5], 2) == 10
