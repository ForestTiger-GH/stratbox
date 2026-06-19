from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.application.scenarios.models import ScenarioSpec


class BottomScenarioComposer(QFrame):
    run_requested = Signal()
    parameters_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('bottomScenarioComposer')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        self.title = QLabel('Сценарий не выбран')
        self.title.setObjectName('composerOperationTitle')
        self.title.setWordWrap(True)
        self.summary = QLabel('Выберите сценарий слева или откройте проводник.')
        self.summary.setObjectName('composerPlaceholder')
        self.summary.setWordWrap(True)
        text_col.addWidget(self.title)
        text_col.addWidget(self.summary)
        layout.addLayout(text_col, 1)
        self.params_button = QPushButton('Параметры')
        self.params_button.setObjectName('secondaryActionButton')
        self.params_button.clicked.connect(self.parameters_requested.emit)
        layout.addWidget(self.params_button, 0, Qt.AlignVCenter)
        self.run_button = QPushButton('Запустить')
        self.run_button.setObjectName('primaryRunButton')
        self.run_button.clicked.connect(self.run_requested.emit)
        layout.addWidget(self.run_button, 0, Qt.AlignVCenter)

    def set_scenario(self, scenario: ScenarioSpec | None, params_summary: str = '') -> None:
        if scenario is None:
            self.title.setText('Сценарий не выбран')
            self.summary.setText('Выберите сценарий слева или откройте проводник.')
            self.run_button.setText('Запустить')
            self.run_button.setEnabled(False)
            return
        self.title.setText(scenario.title)
        steps_count = len(scenario.steps)
        params_hint = params_summary or 'параметры по умолчанию'
        self.summary.setText(f'{steps_count} шаг(ов) · {params_hint}')
        self.run_button.setText(scenario.submit_label)
        self.run_button.setEnabled(True)

    def set_busy(self, busy: bool) -> None:
        self.run_button.setEnabled(not busy)
        self.params_button.setEnabled(not busy)
