from __future__ import annotations

from collections import OrderedDict
from datetime import datetime

from app.core.context import AppContext
from app.presence.models import ParticipantRecord
from app.timeline.models import FeedEntry


class PresenceService:
    def __init__(self, context: AppContext) -> None:
        self._context = context
        self._participants: 'OrderedDict[str, ParticipantRecord]' = OrderedDict()
        self._seed_from_context()

    def _seed_from_context(self) -> None:
        display_name = self._context.account_name or self._context.user_id or 'Текущий пользователь'
        participant_id = self._context.user_id or 'local-user'
        self._participants[participant_id] = ParticipantRecord(
            participant_id=participant_id,
            display_name=display_name,
            is_online=True,
            host_name=self._context.host_name,
            last_seen_label='сейчас',
            run_count=0,
        )

    def register_feed_entry(self, entry: FeedEntry) -> None:
        participant_id = entry.author_id or 'unknown'
        display_name = entry.author_label or participant_id
        record = self._participants.get(participant_id)
        if record is None:
            record = ParticipantRecord(
                participant_id=participant_id,
                display_name=display_name,
                is_online=False,
                host_name=None,
                last_seen_label=entry.timestamp_label,
                run_count=0,
            )
            self._participants[participant_id] = record
        record.display_name = display_name
        record.last_seen_label = entry.timestamp_label
        if entry.kind in {'run_submitted', 'run_started', 'run_completed', 'run_failed'}:
            record.run_count += 1
        if participant_id == (self._context.user_id or 'local-user'):
            record.is_online = True
            record.host_name = self._context.host_name

    def online_count(self) -> int:
        return sum(1 for item in self._participants.values() if item.is_online)

    def participants(self) -> tuple[ParticipantRecord, ...]:
        return tuple(self._participants.values())

    def participant_by_id(self, participant_id: str | None) -> ParticipantRecord | None:
        if participant_id is None:
            return None
        return self._participants.get(participant_id)

    def mark_refreshed(self) -> None:
        current = self._participants.get(self._context.user_id or 'local-user')
        if current is not None:
            current.last_seen_label = datetime.now().strftime('%H:%M')
            current.is_online = True
