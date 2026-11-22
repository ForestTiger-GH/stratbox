"""Select report periods while preserving unresolved same-period candidates."""
from __future__ import annotations

from .contracts import Inventory, Selection


def select_latest(inventory: Inventory, *, source_ids: tuple[str, ...]) -> tuple[Selection, ...]:
    """Select one latest period per source; filenames never resolve byte revisions."""
    if not isinstance(source_ids, tuple) or len(set(source_ids)) != len(source_ids):
        raise ValueError("frg.selection.invalid_sources")
    if len({item.entry.path for item in inventory.assets}) != len(inventory.assets):
        raise ValueError("frg.index.duplicate_path")
    selections = []
    for source_id in source_ids:
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("frg.selection.invalid_sources")
        candidates = [item for item in inventory.assets if item.source_id == source_id
                      and item.valid and item.period is not None
                      and item.recognition in {"supplier", "canonical"}]
        if not candidates:
            selections.append(Selection(source_id, "missing", None))
            continue
        latest = max(item.period.rank for item in candidates)
        selected = tuple(sorted((item for item in candidates if item.period.rank == latest),
                                key=lambda item: item.entry.path))
        if len(selected) != 1:
            selections.append(Selection(source_id, "ambiguous", None, selected))
        else:
            selections.append(Selection(source_id, "selected", selected[0], selected))
    return tuple(selections)


__all__ = ("select_latest",)
