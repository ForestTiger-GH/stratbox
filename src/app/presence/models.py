from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ParticipantRecord:
    participant_id: str
    display_name: str
    is_online: bool
    host_name: str | None = None
    last_seen_label: str | None = None
    run_count: int = 0
    accent_color: str = '#3b82f6'
