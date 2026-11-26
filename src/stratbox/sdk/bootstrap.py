"""Explicit assembly of the standard catalog and static domain records."""
from __future__ import annotations

from stratbox.shared.build import implementation_identity


def default_catalog():
    from stratbox.capabilities.catalog import standard_catalog
    return standard_catalog()


def default_domains():
    from stratbox.capabilities.catalog.domains import load_domains
    return load_domains()
