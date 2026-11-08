from buggy import title_words

def test_sentence():
    assert title_words("hello big world") == "Hello Big World"

def test_single():
    assert title_words("python") == "Python"
