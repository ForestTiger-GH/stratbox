from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWidget

from app.application.background.store import BackgroundProcessStore


class BackgroundPanel(QWidget):
    process_toggled = Signal(str, bool)

    def __init__(self, store: BackgroundProcessStore, parent=None) -> None:
        super().__init__(parent)
        self._store = store
        self._boxes: dict[str, QCheckBox] = {}
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 18, 14, 18)
        self._layout.setSpacing(12)
        title = QLabel('Фоновые процессы')
        title.setObjectName('leftPanelTitle')
        self._layout.addWidget(title)
        hint = QLabel('Автоматизации, которые создают события в сценарном чате и логах.')
        hint.setObjectName('leftPanelHint')
        hint.setWordWrap(True)
        self._layout.addWidget(hint)
        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(10)
        self._layout.addWidget(self._cards_container, 1)
        self.refresh()

    def refresh(self) -> None:
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._boxes.clear()
        for process in self._store.all():
            state = self._store.state(process.id)
            box = QCheckBox(f'{process.title}\n{state.status_label} · последняя проверка: {state.last_run_label} · следующая: {state.next_run_label}')
            box.setObjectName('composerCheckBox')
            box.setToolTip((process.description or '') + (f'\n{state.last_result}' if state.last_result else ''))
            box.setChecked(state.enabled)
            box.toggled.connect(lambda checked, pid=process.id: self.process_toggled.emit(pid, bool(checked)))
            self._boxes[process.id] = box
            self._cards_layout.addWidget(box)
        self._cards_layout.addStretch(1)
