def remove_negatives(d):
    return {k: v for k, v in d.items() if v >= 0}
