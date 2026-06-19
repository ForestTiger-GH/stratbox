from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BackgroundProcessSpec:
    id: str
    title: str
    description: str
    enabled_by_default: bool = False
    status: str = 'disabled'
    last_run_label: str | None = None
    next_run_label: str | None = None
