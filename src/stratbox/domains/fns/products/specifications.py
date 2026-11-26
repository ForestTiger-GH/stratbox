"""Source-local products reference generic view and render actions."""
from stratbox.capabilities.model.domains import ProductSpec

SME_REGIONAL = ProductSpec("fns.sme.regional", commands={},
    settings={"format": "csv", "filters": {"geographic_level": (0, 1, 2)}})
LEGAL_ENTITIES_REGIONAL = ProductSpec("fns.1yur.regional", commands={},
    settings={"format": "csv"}, semantics={"scope": "reviewed_part_i"})
