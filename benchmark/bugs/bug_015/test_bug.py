from buggy import factorial

def test_five():
    assert factorial(5) == 120

def test_zero():
    assert factorial(0) == 1
