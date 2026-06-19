from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QTabWidget, QVBoxLayout, QWidget

from app.runtime.bootstrap import AppRuntime


class SettingsDialog(QDialog):
    def __init__(self, runtime: AppRuntime, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Настройки Strategy Box')
        self.resize(720, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        tabs = QTabWidget()
        tabs.addTab(self._page('Пользовательские настройки', 'Плотность интерфейса, уведомления, последний режим и поведение правой панели будут расширяться здесь.'), 'Пользовательские')
        tabs.addTab(self._page('Рабочие настройки', f'Workspace: {runtime.context.workspace_root_path or "не выбран"}\nСценарии: {len(runtime.scenario_registry.items)}'), 'Рабочие')
        tabs.addTab(self._page('Системные настройки', f'Node: {runtime.context.node_id or "local"}\nMode: {runtime.appdock_bridge.host_mode_label()}'), 'Системные')
        layout.addWidget(tabs)

    def _page(self, title: str, body: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        title_label = QLabel(title)
        title_label.setObjectName('leftPanelTitle')
        layout.addWidget(title_label)
        body_label = QLabel(body)
        body_label.setObjectName('composerPlaceholder')
        body_label.setWordWrap(True)
        body_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(body_label)
        layout.addStretch(1)
        return page
