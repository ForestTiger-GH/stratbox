from __future__ import annotations

from typing import Callable, Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.chat.models import ChatAction, ChatMessage, ChatTextBlock
from app.chat.smooth_scroll import SmoothScrollArea
from app.chat.width_policy import BubbleWidthPolicy
from app.timeline.models import FeedAction, FeedEntry


class ChatBubbleWidget(QFrame):
    def __init__(
        self,
        message: ChatMessage,
        *,
        on_action: Callable[[FeedEntry, FeedAction], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.message = message
        self._width_policy = BubbleWidthPolicy()
        self._on_action = on_action
        self.setObjectName('chatBubble')
        self.setProperty('chatRole', 'outgoing' if message.role == 'outgoing_right' else 'incoming')
        self.setProperty('chatTone', message.tone)
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        self.author_label = QLabel(message.author_label)
        self.author_label.setObjectName('chatAuthor')
        if message.author_accent:
            self.author_label.setStyleSheet(f'color: {message.author_accent};')
        header.addWidget(self.author_label, 0, Qt.AlignLeft)
        header.addStretch(1)
        self.timestamp_label = QLabel(message.timestamp_label)
        self.timestamp_label.setObjectName('chatTimestamp')
        header.addWidget(self.timestamp_label, 0, Qt.AlignRight)
        layout.addLayout(header)

        for block in message.blocks:
            layout.addWidget(self._build_text_block(block))

        if message.actions:
            row = QHBoxLayout()
            row.setSpacing(8)
            if message.role == 'incoming_left':
                row.addStretch(1)
            for action in message.actions:
                button = QPushButton(action.source.title)
                button.setObjectName('chatActionButton')
                button.clicked.connect(lambda _checked=False, a=action.source: self._on_action(message.source_entry, a))
                row.addWidget(button)
            if message.role == 'outgoing_right':
                row.insertStretch(0, 1)
            layout.addLayout(row)

    def _build_text_block(self, block: ChatTextBlock) -> QWidget:
        label = QLabel(block.text)
        label.setWordWrap(True)
        if block.kind == 'headline':
            label.setObjectName('chatHeadline')
        elif block.kind == 'summary':
            label.setObjectName('chatSummary')
        elif block.kind == 'meta':
            label.setObjectName('chatMeta')
        elif block.kind == 'outputs':
            label.setObjectName('chatOutputs')
        elif block.kind == 'error_detail':
            label.setObjectName('chatErrorDetail')
        else:
            label.setObjectName('chatSummary')
        return label

    def apply_viewport_width(self, viewport_width: int) -> None:
        target_width = self._width_policy.resolve_width(
            viewport_width=viewport_width,
            message=self.message,
            metrics=self.fontMetrics(),
        )
        self.setFixedWidth(target_width)
        self.updateGeometry()


class ChatMessageRow(QWidget):
    def __init__(
        self,
        message: ChatMessage,
        *,
        on_action: Callable[[FeedEntry, FeedAction], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.message = message
        self.setObjectName('chatMessageRow')
        self.setProperty('chatRowRole', message.role)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 2, 14, 2)
        layout.setSpacing(0)

        self.bubble = ChatBubbleWidget(message, on_action=on_action)

        if message.role == 'outgoing_right':
            layout.addStretch(1)
            layout.addWidget(self.bubble, 0, Qt.AlignRight | Qt.AlignTop)
        elif message.role == 'notice_center':
            layout.addStretch(1)
            layout.addWidget(self.bubble, 0, Qt.AlignHCenter | Qt.AlignTop)
            layout.addStretch(1)
        else:
            layout.addWidget(self.bubble, 0, Qt.AlignLeft | Qt.AlignTop)
            layout.addStretch(1)

    def apply_viewport_width(self, viewport_width: int) -> None:
        self.bubble.apply_viewport_width(viewport_width)
        self.updateGeometry()


class ChatThreadWidget(QWidget):
    def __init__(self, *, on_action: Callable[[FeedEntry, FeedAction], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_action = on_action
        self._rows: list[ChatMessageRow] = []
        self.setObjectName('chatThread')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 4, 0, 4)
        self._layout.setSpacing(8)
        self._layout.addStretch(1)

    def set_messages(self, messages: Iterable[ChatMessage], *, viewport_width: int) -> None:
        self._clear_rows()
        insert_at = max(0, self._layout.count() - 1)
        for message in messages:
            row = ChatMessageRow(message, on_action=self._on_action)
            row.apply_viewport_width(viewport_width)
            self._layout.insertWidget(insert_at, row)
            insert_at += 1
            self._rows.append(row)
        self.updateGeometry()

    def relayout_for_width(self, viewport_width: int) -> None:
        for row in self._rows:
            row.apply_viewport_width(viewport_width)
        self.updateGeometry()

    def _clear_rows(self) -> None:
        while self._rows:
            row = self._rows.pop()
            self._layout.removeWidget(row)
            row.deleteLater()


class ChatThreadView(SmoothScrollArea):
    def __init__(self, *, on_action: Callable[[FeedEntry, FeedAction], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName('chatThreadView')
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.thread = ChatThreadWidget(on_action=on_action)
        self.setWidget(self.thread)

    def set_messages(self, messages: Iterable[ChatMessage]) -> None:
        self.thread.set_messages(messages, viewport_width=self.viewport().width())

    def is_near_bottom(self) -> bool:
        bar = self.verticalScrollBar()
        return bar.maximum() - bar.value() <= max(28, bar.singleStep() * 2)

    def scroll_to_bottom(self) -> None:
        bar: QScrollBar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
