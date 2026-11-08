from buggy import count_lines

def test_existing_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("a\nb\nc\n")
    assert count_lines(str(p)) == 3

def test_missing_file(tmp_path):
    assert count_lines(str(tmp_path / "nope.txt")) == 0
