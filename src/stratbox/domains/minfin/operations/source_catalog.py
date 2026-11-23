"""Project this publisher's canonical source declarations into source cards."""
from stratbox.domains.registry.declarations import source_cards as _source_cards


def source_cards():
    return _source_cards('minfin')
