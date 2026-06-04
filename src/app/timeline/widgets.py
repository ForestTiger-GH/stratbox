from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.timeline.models import FeedAction, FeedEntry


def _status_property(entry: FeedEntry) -> str:
    return entry.status


class FeedCard(QFrame):
    def __init__(
        self,
        entry: FeedEntry,
        *,
        on_action: Callable[[FeedEntry, FeedAction], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.entry = entry
        self.setObjectName('feedCard')
        self.setProperty('feedStatus', _status_property(entry))
        self.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)
        title = QLabel(entry.title)
        title.setObjectName('feedCardTitle')
        title.setWordWrap(True)
        top.addWidget(title, 1)

        ts = QLabel(entry.timestamp_label)
        ts.setObjectName('feedCardTimestamp')
        top.addWidget(ts, 0, Qt.AlignRight)
        layout.addLayout(top)

        if entry.author_label:
            author = QLabel(entry.author_label)
            author.setObjectName('feedCardAuthor')
            layout.addWidget(author)

        body = QLabel(entry.body)
        body.setObjectName('feedCardBody')
        body.setWordWrap(True)
        layout.addWidget(body)

        if entry.meta:
            meta_text = ' · '.join(f'{key}: {value}' for key, value in entry.meta.items() if value)
            if meta_text:
                meta = QLabel(meta_text)
                meta.setObjectName('feedCardMeta')
                meta.setWordWrap(True)
                layout.addWidget(meta)

        if entry.outputs:
            outputs = QLabel('\n'.join(str(Path(item).name) for item in entry.outputs))
            outputs.setObjectName('feedCardOutputs')
            outputs.setWordWrap(True)
            layout.addWidget(outputs)

        if entry.actions:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addStretch(1)
            for action in entry.actions:
                button = QPushButton(action.title)
                button.setObjectName('feedActionButton')
                button.clicked.connect(lambda _checked=False, a=action: on_action(entry, a))
                row.addWidget(button)
            layout.addLayout(row)
