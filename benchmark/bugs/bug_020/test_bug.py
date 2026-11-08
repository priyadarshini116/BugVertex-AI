from buggy import parse_int_list

def test_normal():
    assert parse_int_list("1,2,3") == [1, 2, 3]

def test_empty_items():
    assert parse_int_list("1,2,,3") == [1, 2, 3]
