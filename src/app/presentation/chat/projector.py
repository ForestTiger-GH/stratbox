from __future__ import annotations

from pathlib import Path

from app.presentation.chat.models import ChatAction, ChatMessage, ChatTextBlock
from app.runtime.context import AppContext
from app.application.presence.service import PresenceService
from app.application.timeline.models import FeedEntry


class ChatProjector:
    def __init__(self, *, context: AppContext, presence_service: PresenceService) -> None:
        self._context = context
        self._presence = presence_service

    def project(self, entry: FeedEntry) -> ChatMessage:
        role = self._project_role(entry)
        tone = self._project_tone(entry)
        author_label = self._project_author_label(entry, role)
        author_accent = self._project_author_accent(entry, author_label)
        blocks = self._project_blocks(entry)
        actions = tuple(ChatAction(source=item) for item in entry.actions)
        return ChatMessage(
            message_id=entry.entry_id,
            role=role,
            tone=tone,
            author_label=author_label,
            author_accent=author_accent,
            timestamp_label=entry.timestamp_label,
            blocks=blocks,
            actions=actions,
            source_entry=entry,
        )

    def _project_role(self, entry: FeedEntry) -> str:
        current_id = self._context.user_id or 'local-user'
        if entry.kind == 'run_submitted' and (entry.author_id or current_id) == current_id:
            return 'outgoing_right'
        return 'incoming_left'

    def _project_tone(self, entry: FeedEntry) -> str:
        if entry.kind == 'system_notice':
            return 'system'
        if entry.kind == 'run_submitted':
            return 'outgoing' if self._project_role(entry) == 'outgoing_right' else 'neutral'
        if entry.kind == 'run_started':
            return 'running'
        if entry.kind == 'run_completed':
            return 'success'
        if entry.kind == 'run_failed':
            return 'error'
        return 'neutral'

    def _project_author_label(self, entry: FeedEntry, role: str) -> str:
        current_id = self._context.user_id or 'local-user'
        fallback_user = self._context.account_name or self._context.user_id or 'Пользователь'
        if entry.kind == 'system_notice':
            return 'Система'
        if role == 'outgoing_right':
            return entry.author_label or fallback_user
        if entry.kind in {'run_started', 'run_completed', 'run_failed'} and (entry.author_id or current_id) == current_id:
            return 'Strategy Box'
        return entry.author_label or fallback_user

    def _project_author_accent(self, entry: FeedEntry, author_label: str) -> str | None:
        if author_label in {'Strategy Box', 'Система'}:
            return '#6b7280'
        return self._presence.color_for_participant(entry.author_id)

    def _project_blocks(self, entry: FeedEntry) -> tuple[ChatTextBlock, ...]:
        blocks: list[ChatTextBlock] = []
        headline = entry.title.strip()
        if headline:
            blocks.append(ChatTextBlock(kind='headline', text=headline))

        summary = self._normalize_summary(entry)
        if summary:
            blocks.append(ChatTextBlock(kind='summary', text=summary))

        meta_text = self._normalize_meta(entry)
        if meta_text:
            blocks.append(ChatTextBlock(kind='meta', text=meta_text))

        outputs_text = self._normalize_outputs(entry)
        if outputs_text:
            blocks.append(ChatTextBlock(kind='outputs', text=outputs_text))

        return tuple(blocks)

    def _normalize_summary(self, entry: FeedEntry) -> str:
        body = (entry.body or '').strip()
        if not body:
            return ''
        if entry.kind == 'run_submitted' and body.startswith('Запуск подготовлен: '):
            return body.replace('Запуск подготовлен: ', '', 1)
        return body

    def _normalize_meta(self, entry: FeedEntry) -> str:
        parts: list[str] = []
        if entry.kind in {'run_started', 'run_completed', 'run_failed'} and entry.author_label and (entry.author_label != 'Strategy Box'):
            current_id = self._context.user_id or 'local-user'
            if (entry.author_id or current_id) != current_id:
                parts.append(f'инициатор: {entry.author_label}')
        for key, value in entry.meta.items():
            if not value:
                continue
            parts.append(f'{key}: {value}')
        return ' · '.join(parts)

    def _normalize_outputs(self, entry: FeedEntry) -> str:
        if not entry.outputs:
            return ''
        visible = [Path(item).name for item in entry.outputs[:4]]
        if len(entry.outputs) > 4:
            visible.append(f'ещё {len(entry.outputs) - 4} файлов')
        return '\n'.join(visible)
