from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from app.application.artifacts.store import ArtifactStore
from app.application.cases.store import ScenarioCaseStore
from app.application.events.store import OperationalEventStore
from app.application.logs.store import LogStore
from app.platform.desktop.services import PlatformServices


class CasePanel(QWidget):
    def __init__(
        self,
        *,
        case_store: ScenarioCaseStore,
        event_store: OperationalEventStore,
        artifact_store: ArtifactStore,
        log_store: LogStore,
        platform: PlatformServices,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._case_store = case_store
        self._event_store = event_store
        self._artifact_store = artifact_store
        self._log_store = log_store
        self._platform = platform
        self._case_id: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        title = QLabel('Кейс')
        title.setObjectName('leftPanelTitle')
        layout.addWidget(title)
        self.summary = QLabel('Кейс не выбран. Выберите карточку запуска в центральной истории.')
        self.summary.setObjectName('composerPlaceholder')
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.summary)
        self.steps = QListWidget()
        self.steps.setObjectName('artifactList')
        layout.addWidget(self.steps, 1)
        self.open_log_button = QPushButton('Открыть первый лог кейса')
        self.open_log_button.setObjectName('secondaryActionButton')
        self.open_log_button.clicked.connect(self._open_first_log)
        layout.addWidget(self.open_log_button)
        self.open_artifact_button = QPushButton('Открыть первый артефакт')
        self.open_artifact_button.setObjectName('secondaryActionButton')
        self.open_artifact_button.clicked.connect(self._open_first_artifact)
        layout.addWidget(self.open_artifact_button)
        self.refresh()

    def set_case_id(self, case_id: str | None) -> None:
        self._case_id = case_id or None
        self.refresh()

    def refresh(self) -> None:
        self.steps.clear()
        if not self._case_id or not self._case_store.has(self._case_id):
            self.summary.setText('Кейс не выбран. Выберите карточку запуска в центральной истории.')
            self.open_log_button.setEnabled(False)
            self.open_artifact_button.setEnabled(False)
            return
        case = self._case_store.get(self._case_id)
        artifacts = self._artifact_store.by_case(case.case_id)
        logs = self._log_store.by_case(case.case_id)
        events = self._event_store.by_case(case.case_id)
        duration = f' · {case.duration_label()}' if case.duration_label() else ''
        self.summary.setText(
            f'{case.scenario_title}\n'
            f'Статус: {case.status}{duration}\n'
            f'Автор: {case.author_label or "Пользователь"}\n'
            f'Параметры: {case.short_params_text()}\n'
            f'Артефакты: {len(artifacts)} · Логи: {len(logs)} · События: {len(events)}'
        )
        for step in case.steps:
            item = QListWidgetItem(f'{step.status.upper()} · {step.title}\n{step.message or step.log_path or ""}')
            item.setToolTip(step.log_path or step.message)
            self.steps.addItem(item)
        self.open_log_button.setEnabled(bool(logs))
        self.open_artifact_button.setEnabled(bool(artifacts))

    def _open_first_log(self) -> None:
        if not self._case_id:
            return
        logs = self._log_store.by_case(self._case_id)
        if logs:
            self._platform.open_path(logs[0].path)

    def _open_first_artifact(self) -> None:
        if not self._case_id:
            return
        artifacts = self._artifact_store.by_case(self._case_id)
        if artifacts:
            self._platform.open_path(artifacts[0].path)
