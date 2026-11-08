import sqlite3
from buggy import find_user

def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE users (name TEXT)")
    conn.executemany("INSERT INTO users VALUES (?)", [("asha",), ("ravi",)])
    return conn

def test_normal_lookup():
    assert find_user(make_conn(), "asha") == ["asha"]

def test_injection_is_blocked():
    assert find_user(make_conn(), "x' OR '1'='1") == []
