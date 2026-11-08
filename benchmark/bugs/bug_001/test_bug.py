from buggy import get_user_name

def test_valid_user():
    assert get_user_name({"name": "  Asha  "}) == "Asha"

def test_user_is_none():
    assert get_user_name(None) == ""

def test_missing_name():
    assert get_user_name({}) == ""
