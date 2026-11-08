def count_lines(path):
    with open(path) as f:
        return len(f.read().splitlines())
