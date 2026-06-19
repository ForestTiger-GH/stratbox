from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from app.application.scenarios.models import ScenarioRegistry


class ScenarioBlocksPanel(QWidget):
    scenario_selected = Signal(str)

    def __init__(self, registry: ScenarioRegistry, parent=None) -> None:
        super().__init__(parent)
        self._registry = registry
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 14, 18)
        layout.setSpacing(12)
        title = QLabel('Сценарные блоки')
        title.setObjectName('leftPanelTitle')
        layout.addWidget(title)
        hint = QLabel('Составные сценарии из нескольких операций. Это будущая основная форма работы.')
        hint.setObjectName('leftPanelHint')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.list = QListWidget()
        self.list.setObjectName('artifactList')
        self.list.itemSelectionChanged.connect(self._selection_changed)
        layout.addWidget(self.list, 1)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for scenario in self._registry.enabled():
            if scenario.kind != 'composite':
                continue
            item = QListWidgetItem(f'{scenario.title}\n{len(scenario.steps)} шаг(ов)')
            item.setData(Qt.UserRole, scenario.id)
            item.setToolTip(scenario.description)
            self.list.addItem(item)

    def _selection_changed(self) -> None:
        item = self.list.currentItem()
        if item is not None:
            self.scenario_selected.emit(str(item.data(Qt.UserRole)))
