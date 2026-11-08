from buggy import is_palindrome

def test_simple():
    assert is_palindrome("level") is True

def test_case_and_space():
    assert is_palindrome("Race car") is True

def test_not_palindrome():
    assert is_palindrome("hello") is False
