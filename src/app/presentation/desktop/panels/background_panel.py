from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWidget

from app.application.background.store import BackgroundProcessStore


class BackgroundPanel(QWidget):
    process_toggled = Signal(str, bool)

    def __init__(self, store: BackgroundProcessStore, parent=None) -> None:
        super().__init__(parent)
        self._store = store
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 14, 18)
        layout.setSpacing(12)
        title = QLabel('Фоновые процессы')
        title.setObjectName('leftPanelTitle')
        layout.addWidget(title)
        hint = QLabel('Автоматизации, которые создают события в сценарном чате и логах.')
        hint.setObjectName('leftPanelHint')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        for process in self._store.all():
            box = QCheckBox(process.title)
            box.setObjectName('composerCheckBox')
            box.setToolTip(process.description)
            box.setChecked(self._store.is_enabled(process.id))
            box.toggled.connect(lambda checked, pid=process.id: self.process_toggled.emit(pid, bool(checked)))
            layout.addWidget(box)
        layout.addStretch(1)
