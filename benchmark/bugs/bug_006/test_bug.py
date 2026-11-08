from buggy import get_price

def test_present():
    assert get_price({"tea": 10}, "tea") == 10

def test_missing():
    assert get_price({"tea": 10}, "milk") == 0
