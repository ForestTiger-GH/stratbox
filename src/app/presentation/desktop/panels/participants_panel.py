from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from app.application.presence.service import PresenceService


class ParticipantsPanel(QWidget):
    participant_selected = Signal(object)

    def __init__(self, presence: PresenceService, parent=None) -> None:
        super().__init__(parent)
        self._presence = presence
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 14, 18)
        layout.setSpacing(12)
        title = QLabel('Участники')
        title.setObjectName('leftPanelTitle')
        layout.addWidget(title)
        hint = QLabel('Пользователи, host, будущие AI-акторы и системные участники рабочей поверхности.')
        hint.setObjectName('leftPanelHint')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.list = QListWidget()
        self.list.setObjectName('artifactList')
        self.list.itemSelectionChanged.connect(self._selection_changed)
        layout.addWidget(self.list, 1)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for participant in self._presence.participants():
            text = participant.display_name
            if participant.is_online:
                text += ' · online'
            if participant.last_seen_label:
                text += f' · {participant.last_seen_label}'
            if participant.run_count:
                text += f' · запусков: {participant.run_count}'
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, participant.participant_id)
            self.list.addItem(item)

    def _selection_changed(self) -> None:
        item = self.list.currentItem()
        if item is None:
            self.participant_selected.emit(None)
            return
        self.participant_selected.emit(str(item.data(Qt.UserRole)))
