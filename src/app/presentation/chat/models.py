from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.application.timeline.models import FeedAction, FeedEntry

ChatMessageRole = Literal['incoming_left', 'outgoing_right', 'notice_center']
ChatMessageTone = Literal['outgoing', 'neutral', 'running', 'success', 'error', 'system', 'presence']
ChatBlockKind = Literal['headline', 'summary', 'meta', 'outputs', 'error_detail', 'notice']


@dataclass(slots=True)
class ChatTextBlock:
    kind: ChatBlockKind
    text: str


@dataclass(slots=True)
class ChatAction:
    source: FeedAction


@dataclass(slots=True)
class ChatMessage:
    message_id: str
    role: ChatMessageRole
    tone: ChatMessageTone
    author_label: str
    author_accent: str | None
    timestamp_label: str
    blocks: tuple[ChatTextBlock, ...]
    actions: tuple[ChatAction, ...]
    source_entry: FeedEntry
