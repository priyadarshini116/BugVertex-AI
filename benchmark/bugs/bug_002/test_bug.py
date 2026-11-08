from buggy import add_ages

def test_ints():
    assert add_ages(2, 3) == 5

def test_string_and_int():
    assert add_ages("5", 3) == 8
