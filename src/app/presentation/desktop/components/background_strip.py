from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.application.background.store import BackgroundProcessStore


class ActiveBackgroundStrip(QWidget):
    process_selected = Signal(str)

    def __init__(self, store: BackgroundProcessStore, parent=None) -> None:
        super().__init__(parent)
        self._store = store
        self.setObjectName('activeBackgroundStrip')
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self.refresh()

    def refresh(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        active = self._store.enabled_states()
        if not active:
            label = QLabel('Фоновые процессы не включены')
            label.setObjectName('chatMeta')
            self._layout.addWidget(label)
        for state in active:
            spec = self._store.spec(state.process_id)
            button = QPushButton(f'● {spec.title} · {state.status_label}')
            button.setObjectName('backgroundProcessChip')
            button.clicked.connect(lambda checked=False, pid=state.process_id: self.process_selected.emit(pid))
            self._layout.addWidget(button)
        self._layout.addStretch(1)
