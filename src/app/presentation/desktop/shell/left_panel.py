from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QStackedWidget, QVBoxLayout

from app.runtime.bootstrap import AppRuntime
from app.presentation.desktop.panels.assignments_panel import AssignmentsPanel
from app.presentation.desktop.panels.atomic_scenarios_panel import AtomicScenariosPanel
from app.presentation.desktop.panels.background_panel import BackgroundPanel
from app.presentation.desktop.panels.participants_panel import ParticipantsPanel
from app.presentation.desktop.panels.scenario_blocks_panel import ScenarioBlocksPanel
from app.presentation.desktop.panels.workspace_panel import WorkspacePanel
from .mode_rail import ShellMode


class LeftPanel(QFrame):
    scenario_selected = Signal(str)
    participant_selected = Signal(object)
    path_open_requested = Signal(str)
    path_copy_requested = Signal(str)
    background_process_toggled = Signal(str, bool)
    assignment_selected = Signal(str)
    assignment_case_selected = Signal(str)

    def __init__(self, runtime: AppRuntime, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('leftPanel')
        self._runtime = runtime
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        self.workspace_panel = WorkspacePanel(runtime.context)
        self.atomic_panel = AtomicScenariosPanel(runtime.scenario_registry)
        self.blocks_panel = ScenarioBlocksPanel(runtime.scenario_registry)
        self.background_panel = BackgroundPanel(runtime.background_store)
        self.people_panel = ParticipantsPanel(runtime.presence_service)
        self.assignments_panel = AssignmentsPanel(runtime.assignment_store)
        self._map = {
            ShellMode.WORKSPACE: self.workspace_panel,
            ShellMode.ATOMIC_SCENARIOS: self.atomic_panel,
            ShellMode.SCENARIO_BLOCKS: self.blocks_panel,
            ShellMode.BACKGROUND: self.background_panel,
            ShellMode.PEOPLE: self.people_panel,
            ShellMode.ASSIGNMENTS: self.assignments_panel,
        }
        for widget in self._map.values():
            self.stack.addWidget(widget)
        self.workspace_panel.open_path_requested.connect(self.path_open_requested.emit)
        self.workspace_panel.copy_path_requested.connect(self.path_copy_requested.emit)
        self.atomic_panel.scenario_selected.connect(self.scenario_selected.emit)
        self.blocks_panel.scenario_selected.connect(self.scenario_selected.emit)
        self.background_panel.process_toggled.connect(self.background_process_toggled.emit)
        self.people_panel.participant_selected.connect(self.participant_selected.emit)
        self.assignments_panel.assignment_selected.connect(self.assignment_selected.emit)
        self.assignments_panel.case_selected.connect(self.assignment_case_selected.emit)

    def set_mode(self, mode: str) -> None:
        widget = self._map.get(mode) or self.workspace_panel
        self.stack.setCurrentWidget(widget)

    def select_scenario(self, scenario_id: str) -> None:
        self.atomic_panel.select_scenario(scenario_id)

    def refresh(self) -> None:
        self.workspace_panel.refresh()
        self.background_panel.refresh()
        self.people_panel.refresh()
        self.assignments_panel.refresh()
