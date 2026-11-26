"""Prepared workbook content is checked independently of its rendering."""
import re
from stratbox.domains.cbr.products.corporate_lending.sors.results import SorsViewPack


def validate_view_pack(value, *, require_seal=False):
    if not isinstance(value, SorsViewPack) or not value.tables:
        raise ValueError("sors.views_invalid")
    names = [name for name, frame in value.tables]
    if any(not isinstance(name, str) or not 1 <= len(name) <= 31 or re.search(r"[:\\/?*\[\]]", name)
           for name in names) or len({name.casefold() for name in names}) != len(names):
        raise ValueError("sors.view_sheet_invalid")
    if require_seal and value.source_identity is None:
        raise ValueError("sors.view_source_identity_required")
