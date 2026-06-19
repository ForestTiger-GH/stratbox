from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.presentation.desktop.components.status_chip import StatusChip
from .models import ScenarioChatMessage


class ScenarioCaseBubble(QFrame):
    clicked = Signal(str)
    artifact_open_requested = Signal(str)

    def __init__(self, message: ScenarioChatMessage, parent=None) -> None:
        super().__init__(parent)
        self._case_id = message.source_case_id
        self.setObjectName('scenarioCaseBubble')
        self.setProperty('tone', message.tone)
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        meta = QHBoxLayout()
        author = QLabel(f'{message.author_label} · {message.timestamp_label}')
        author.setObjectName('chatMeta')
        meta.addWidget(author)
        meta.addStretch(1)
        meta.addWidget(StatusChip(message.status))
        layout.addLayout(meta)
        title = QLabel(message.title)
        title.setObjectName('chatMessageTitle')
        title.setWordWrap(True)
        layout.addWidget(title)
        summary = QLabel(message.summary)
        summary.setObjectName('chatMessageBody')
        summary.setWordWrap(True)
        layout.addWidget(summary)
        if message.stage_label:
            stage = QLabel(f'Текущий этап: {message.stage_label}')
            stage.setObjectName('chatStage')
            stage.setWordWrap(True)
            layout.addWidget(stage)
        if message.params_summary:
            params = QLabel(f'Параметры: {message.params_summary}')
            params.setObjectName('chatMeta')
            params.setWordWrap(True)
            layout.addWidget(params)
        if message.steps:
            steps_title = QLabel('Шаги')
            steps_title.setObjectName('composerSectionTitle')
            layout.addWidget(steps_title)
            for step in message.steps:
                row = QLabel(f'• {step.title} · {step.status}' + (f' · {step.message}' if step.message else ''))
                row.setObjectName('chatStepLine')
                row.setWordWrap(True)
                layout.addWidget(row)
        if message.artifacts:
            art_title = QLabel('Артефакты')
            art_title.setObjectName('composerSectionTitle')
            layout.addWidget(art_title)
            for artifact in message.artifacts:
                button = QPushButton(artifact.title)
                button.setObjectName('feedActionButton')
                button.setToolTip(artifact.path)
                button.clicked.connect(lambda checked=False, p=artifact.path: self.artifact_open_requested.emit(p))
                layout.addWidget(button)

    def mousePressEvent(self, event) -> None:
        if self._case_id:
            self.clicked.emit(self._case_id)
        super().mousePressEvent(event)


class ScenarioNoticeBubble(QFrame):
    def __init__(self, message: ScenarioChatMessage, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('scenarioNoticeBubble')
        self.setProperty('tone', message.tone)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        title = QLabel(f'{message.title} · {message.timestamp_label}')
        title.setObjectName('chatMeta')
        title.setWordWrap(True)
        layout.addWidget(title)
        body = QLabel(message.summary)
        body.setObjectName('chatMessageBody')
        body.setWordWrap(True)
        layout.addWidget(body)


class ScenarioChatView(QScrollArea):
    case_selected = Signal(str)
    artifact_open_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('scenarioChatView')
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._had_messages = False
        self._host = QWidget()
        self._layout = QVBoxLayout(self._host)
        self._layout.setContentsMargins(28, 24, 28, 24)
        self._layout.setSpacing(12)
        self._layout.addStretch(1)
        self.setWidget(self._host)

    def set_messages(self, messages: tuple[ScenarioChatMessage, ...]) -> None:
        bar = self.verticalScrollBar()
        was_at_bottom = (not self._had_messages) or bar.value() >= bar.maximum() - 12
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not messages:
            empty = ScenarioNoticeBubble(ScenarioChatMessage(
                message_id='empty', message_kind='notice', tone='info', title='Strategy Box готов',
                summary='Выберите сценарий слева или откройте проводник.', status_label='Инфо', status='info',
                author_label='Система', timestamp_label='', sort_key='',
            ))
            self._layout.addWidget(empty)
        for message in messages:
            if message.message_kind == 'case':
                bubble = ScenarioCaseBubble(message)
                bubble.clicked.connect(self.case_selected.emit)
                bubble.artifact_open_requested.connect(self.artifact_open_requested.emit)
                self._layout.addWidget(bubble)
            else:
                self._layout.addWidget(ScenarioNoticeBubble(message))
        self._layout.addStretch(1)
        self._had_messages = bool(messages)
        if was_at_bottom:
            bar.setValue(bar.maximum())
