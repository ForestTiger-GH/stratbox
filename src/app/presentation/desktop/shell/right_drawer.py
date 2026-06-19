from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout

from app.runtime.bootstrap import AppRuntime
from app.presentation.desktop.panels.artifacts_panel import ArtifactsPanel
from app.presentation.desktop.panels.logs_panel import LogsPanel
from app.presentation.desktop.panels.parameters_panel import ScenarioParametersPanel


class RightInspectorDrawer(QFrame):
    close_requested = Signal()
    tab_changed = Signal(str)
    params_changed = Signal(dict)
    submitted = Signal()

    def __init__(self, runtime: AppRuntime, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('rightInspectorDrawer')
        self._runtime = runtime
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(16, 14, 12, 10)
        title = QLabel('Детали')
        title.setObjectName('rightInspectorTitle')
        header.addWidget(title)
        header.addStretch(1)
        close = QPushButton('→')
        close.setObjectName('rightInspectorCloseButton')
        close.setToolTip('Свернуть панель')
        close.clicked.connect(self.close_requested.emit)
        header.addWidget(close)
        layout.addLayout(header)
        tabs = QHBoxLayout()
        tabs.setContentsMargins(12, 0, 12, 10)
        tabs.setSpacing(8)
        self._tab_buttons: dict[str, QPushButton] = {}
        for tab_id, label in (('logs', 'Логи'), ('artifacts', 'Артефакты'), ('parameters', 'Параметры')):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setObjectName('rightInspectorTab')
            button.clicked.connect(lambda checked=False, value=tab_id: self.set_active_tab(value, emit=True))
            self._tab_buttons[tab_id] = button
            tabs.addWidget(button)
        layout.addLayout(tabs)
        self.stack = QStackedWidget()
        self.logs_panel = LogsPanel(runtime.log_store, runtime.platform)
        self.artifacts_panel = ArtifactsPanel(runtime.artifact_store, runtime.platform)
        self.parameters_panel = ScenarioParametersPanel(preferences=runtime.preferences)
        self.parameters_panel.params_changed.connect(self.params_changed.emit)
        self.parameters_panel.submitted.connect(self.submitted.emit)
        self._panels = {
            'logs': self.logs_panel,
            'artifacts': self.artifacts_panel,
            'parameters': self.parameters_panel,
        }
        for panel in self._panels.values():
            self.stack.addWidget(panel)
        layout.addWidget(self.stack, 1)
        self.set_active_tab(runtime.context.user_config.shell.right_inspector_tab)

    def set_active_tab(self, tab_id: str, *, emit: bool = False) -> None:
        if tab_id not in self._panels:
            tab_id = 'logs'
        panel = self._panels[tab_id]
        self.stack.setCurrentWidget(panel)
        for key, button in self._tab_buttons.items():
            active = key == tab_id
            button.setChecked(active)
            button.setProperty('active', active)
            button.style().unpolish(button)
            button.style().polish(button)
        if emit:
            self.tab_changed.emit(tab_id)

    def set_scenario(self, scenario) -> None:
        self.parameters_panel.set_scenario(scenario)

    def collect_params(self) -> dict:
        return self.parameters_panel.collect_params()

    def refresh(self) -> None:
        self.logs_panel.refresh()
        self.artifacts_panel.refresh()
