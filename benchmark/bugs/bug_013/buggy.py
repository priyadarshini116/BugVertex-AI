def remove_negatives(d):
    for k in d:
        if d[k] < 0:
            del d[k]
    return d
