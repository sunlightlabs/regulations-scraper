def exclude(d, exc):
    return dict([(key, value) for (key, value) in d.items() if key not in exc])
