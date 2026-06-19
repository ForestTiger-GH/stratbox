from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from app.application.events.models import OperationalEvent
from app.presentation.desktop.chat_scene import ChatSceneHost
from app.presentation.desktop.components.scenario_composer import BottomScenarioComposer
from app.presentation.scenario_chat.projector import project_case, project_event
from app.presentation.scenario_chat.widgets import ScenarioChatView
from app.runtime.bootstrap import AppRuntime


def _chat_background_image_path():
    from pathlib import Path
    return Path(__file__).resolve().parents[3] / 'resources' / 'images' / 'chat_history_background.png'


class CenterScenarioPanel(ChatSceneHost):
    filter_changed = Signal(str)
    run_requested = Signal()
    parameters_requested = Signal()
    artifact_open_requested = Signal(str)
    case_selected = Signal(str)

    def __init__(self, runtime: AppRuntime, parent=None) -> None:
        super().__init__(_chat_background_image_path(), parent)
        self.setObjectName('centerPanel')
        self._runtime = runtime
        self._filter_mode = runtime.context.user_config.chat.filter_mode
        self.filter_buttons: dict[str, QPushButton] = {}
        filters = QHBoxLayout()
        filters.setSpacing(8)
        for mode, title in [('all', 'Все'), ('mine', 'Мои'), ('running', 'В работе'), ('success', 'Успешные'), ('errors', 'Ошибки'), ('unread', 'Непрочитанные')]:
            button = QPushButton(title)
            button.setCheckable(True)
            button.setObjectName('scenarioFilterPill')
            button.clicked.connect(lambda checked=False, value=mode: self.set_filter_mode(value, emit=True))
            self.filter_buttons[mode] = button
            filters.addWidget(button)
        filters.addStretch(1)
        self.content_layout.addLayout(filters)
        self.chat = ScenarioChatView()
        self.chat.case_selected.connect(self.case_selected.emit)
        self.chat.artifact_open_requested.connect(self.artifact_open_requested.emit)
        self.content_layout.addWidget(self.chat, 1)
        self.composer = BottomScenarioComposer()
        self.composer.run_requested.connect(self.run_requested.emit)
        self.composer.parameters_requested.connect(self.parameters_requested.emit)
        self.content_layout.addWidget(self.composer)
        self.set_filter_mode(self._filter_mode)
        self.refresh()

    def set_filter_mode(self, mode: str, *, emit: bool = False) -> None:
        self._filter_mode = mode
        for key, button in self.filter_buttons.items():
            active = key == mode
            button.setChecked(active)
            button.setProperty('active', active)
            button.style().unpolish(button)
            button.style().polish(button)
        if emit:
            self.filter_changed.emit(mode)
        self.refresh()

    def set_scenario(self, scenario, params_summary: str = '') -> None:
        self.composer.set_scenario(scenario, params_summary=params_summary)

    def set_busy(self, busy: bool) -> None:
        self.composer.set_busy(busy)

    def refresh(self) -> None:
        author_id = self._runtime.context.user_id if self._filter_mode == 'mine' else self._runtime.context.user_config.chat.selected_author_id
        cases = self._runtime.case_store.visible(mode=self._filter_mode, author_id=author_id)
        messages = [project_case(case, self._runtime.artifact_store) for case in cases]
        if not messages:
            events = self._runtime.event_store.recent(20)
            important = [event for event in events if event.kind in {'system_notice', 'background_notice'}]
            messages.extend(project_event(event) for event in important)
        self.chat.set_messages(tuple(messages))
