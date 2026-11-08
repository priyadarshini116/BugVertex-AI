from buggy import remove_negatives

def test_removes_negatives():
    assert remove_negatives({"a": 1, "b": -2, "c": 3}) == {"a": 1, "c": 3}

def test_no_negatives():
    assert remove_negatives({"a": 1}) == {"a": 1}
