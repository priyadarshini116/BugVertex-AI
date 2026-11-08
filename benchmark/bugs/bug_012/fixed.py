def count_lines(path):
    try:
        with open(path) as f:
            return len(f.read().splitlines())
    except FileNotFoundError:
        return 0
