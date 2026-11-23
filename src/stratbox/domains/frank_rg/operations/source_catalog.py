"""Project this publisher's canonical source declarations into source cards."""
from stratbox.core.registry.sources import source_cards as _source_cards


def source_cards():
    return _source_cards('frank_rg')
