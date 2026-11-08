from buggy import fetch

class FakeClient:
    def __init__(self):
        self.timeout = None
    def get(self, url, timeout=None):
        self.timeout = timeout
        return "ok"

def test_returns_response():
    assert fetch(FakeClient(), "http://x") == "ok"

def test_timeout_is_set():
    c = FakeClient()
    fetch(c, "http://x")
    assert c.timeout is not None
