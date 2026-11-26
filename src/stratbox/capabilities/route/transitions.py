"""Supported role transitions; rendering and calculations have short entrances."""
TRANSITIONS = frozenset({('originals','readable'),('originals','extracts'),('extracts','integrated'),('extracts','products'),('integrated','products'),('products','products')})
