from buggy import add_tag

def test_independent_calls():
    assert add_tag("a") == ["a"]
    assert add_tag("b") == ["b"]

def test_given_list():
    assert add_tag("x", ["y"]) == ["y", "x"]
