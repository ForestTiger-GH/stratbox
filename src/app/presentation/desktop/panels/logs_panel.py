from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from app.application.logs.store import LogStore
from app.application.logs.tail import read_log_tail
from app.platform.desktop.services import PlatformServices


class LogsPanel(QWidget):
    def __init__(self, store: LogStore, platform: PlatformServices, parent=None) -> None:
        super().__init__(parent)
        self._store = store
        self._platform = platform
        self._case_id: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        self.title = QLabel('Логи')
        self.title.setObjectName('leftPanelTitle')
        layout.addWidget(self.title)
        self.list = QListWidget()
        self.list.setObjectName('artifactList')
        self.list.itemSelectionChanged.connect(self._selection_changed)
        layout.addWidget(self.list, 1)
        self.viewer = QPlainTextEdit()
        self.viewer.setObjectName('logViewer')
        self.viewer.setReadOnly(True)
        self.viewer.setMaximumHeight(220)
        layout.addWidget(self.viewer)
        self.open_button = QPushButton('Показать лог в папке')
        self.open_button.setObjectName('secondaryActionButton')
        self.open_button.clicked.connect(self._open_current)
        layout.addWidget(self.open_button)
        self.refresh()

    def set_case_filter(self, case_id: str | None) -> None:
        self._case_id = case_id or None
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        logs = self._store.by_case(self._case_id) if self._case_id else self._store.all()
        self.title.setText('Логи выбранного кейса' if self._case_id else 'Все логи')
        for log in logs:
            item = QListWidgetItem(f'{log.timestamp_label} · {log.title}\n{log.status} · {log.path}')
            item.setData(Qt.UserRole, log.path)
            item.setToolTip(log.path)
            self.list.addItem(item)
        if self.list.count() == 0:
            self.viewer.setPlainText('Логи выбранного кейса появятся после запуска.' if self._case_id else 'Логи появятся после запуска сценария.')

    def _selection_changed(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        path = str(item.data(Qt.UserRole))
        self.viewer.setPlainText(read_log_tail(path))

    def _open_current(self) -> None:
        item = self.list.currentItem()
        if item is not None:
            self._platform.open_path(str(item.data(Qt.UserRole)))
