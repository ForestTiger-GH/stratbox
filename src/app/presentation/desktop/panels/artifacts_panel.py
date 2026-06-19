from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from app.application.artifacts.store import ArtifactStore
from app.platform.desktop.services import PlatformServices


class ArtifactsPanel(QWidget):
    def __init__(self, store: ArtifactStore, platform: PlatformServices, parent=None) -> None:
        super().__init__(parent)
        self._store = store
        self._platform = platform
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        title = QLabel('Артефакты')
        title.setObjectName('leftPanelTitle')
        layout.addWidget(title)
        self.list = QListWidget()
        self.list.setObjectName('artifactList')
        self.list.itemDoubleClicked.connect(lambda *_: self._open_current())
        layout.addWidget(self.list, 1)
        self.open_button = QPushButton('Открыть / показать в папке')
        self.open_button.setObjectName('secondaryActionButton')
        self.open_button.clicked.connect(self._open_current)
        layout.addWidget(self.open_button)
        self.copy_button = QPushButton('Скопировать путь')
        self.copy_button.setObjectName('secondaryActionButton')
        self.copy_button.clicked.connect(self._copy_current)
        layout.addWidget(self.copy_button)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for artifact in self._store.all():
            item = QListWidgetItem(f'{artifact.kind.upper()} · {artifact.name}\n{artifact.timestamp_label} · {artifact.path}')
            item.setData(Qt.UserRole, artifact.path)
            item.setToolTip(artifact.path)
            self.list.addItem(item)
        if self.list.count() == 0:
            self.list.addItem(QListWidgetItem('Артефакты появятся после запуска сценария.'))

    def _current_path(self) -> str | None:
        item = self.list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _open_current(self) -> None:
        path = self._current_path()
        if path:
            self._platform.open_path(path)

    def _copy_current(self) -> None:
        path = self._current_path()
        if path:
            self._platform.copy_text(path)
