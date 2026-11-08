from buggy import sorted_copy

def test_sorted_result():
    assert sorted_copy([3, 1, 2]) == [1, 2, 3]

def test_original_unchanged():
    original = [3, 1, 2]
    sorted_copy(original)
    assert original == [3, 1, 2]
