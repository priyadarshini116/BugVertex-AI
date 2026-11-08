from buggy import last_item

def test_normal():
    assert last_item([1, 2, 3]) == 3

def test_empty():
    assert last_item([]) is None
