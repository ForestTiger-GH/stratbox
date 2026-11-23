"""Presentation choices independent of source layouts and financial calculation."""
from types import MappingProxyType

FORM_VIEW_PROFILES = MappingProxyType({code: "hierarchical_statement" if code == "802" else "standard"
    for code in ("101", "102", "123", "135", "802", "805")})
