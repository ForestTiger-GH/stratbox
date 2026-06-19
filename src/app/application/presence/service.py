from __future__ import annotations

from collections import OrderedDict
from datetime import datetime

from app.runtime.context import AppContext
from app.application.presence.models import ParticipantRecord


class PresenceService:
    _PALETTE = (
        '#2563eb',
        '#7c3aed',
        '#db2777',
        '#0f766e',
        '#ea580c',
        '#059669',
        '#9333ea',
        '#dc2626',
    )

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
            accent_color=self.color_for_participant(participant_id),
        )

    def color_for_participant(self, participant_id: str | None) -> str:
        key = participant_id or 'unknown'
        idx = sum(ord(ch) for ch in key) % len(self._PALETTE)
        return self._PALETTE[idx]

    def register_case(self, case) -> None:
        participant_id = case.author_id or 'unknown'
        display_name = case.author_label or participant_id
        timestamp = getattr(case, 'timestamp_label', datetime.now().strftime('%H:%M'))
        record = self._participants.get(participant_id)
        if record is None:
            record = ParticipantRecord(
                participant_id=participant_id,
                display_name=display_name,
                is_online=False,
                host_name=None,
                last_seen_label=timestamp,
                run_count=0,
                accent_color=self.color_for_participant(participant_id),
            )
            self._participants[participant_id] = record
        record.display_name = display_name
        record.last_seen_label = timestamp
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

    def other_online_participants(self) -> tuple[ParticipantRecord, ...]:
        current_id = self._context.user_id or 'local-user'
        return tuple(
            item for item in self._participants.values()
            if item.is_online and item.participant_id != current_id
        )

    def other_online_html(self) -> str:
        participants = self.other_online_participants()
        if not participants:
            return ''
        chunks = [
            f'<span style="color:{item.accent_color};">{item.display_name}</span>'
            for item in participants
        ]
        return ' · '.join(chunks)
