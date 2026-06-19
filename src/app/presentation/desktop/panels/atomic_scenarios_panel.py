from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from app.application.scenarios.models import ScenarioRegistry


class AtomicScenariosPanel(QWidget):
    scenario_selected = Signal(str)

    def __init__(self, registry: ScenarioRegistry, parent=None) -> None:
        super().__init__(parent)
        self._registry = registry
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 14, 18)
        layout.setSpacing(12)
        title = QLabel('Отдельные сценарии')
        title.setObjectName('leftPanelTitle')
        layout.addWidget(title)
        hint = QLabel('Атомарные действия. Каждый пункт запускает один рабочий сценарий.')
        hint.setObjectName('leftPanelHint')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setItemsExpandable(False)
        self.tree.setIndentation(0)
        self.tree.setObjectName('operationTree')
        self.tree.itemSelectionChanged.connect(self._selection_changed)
        layout.addWidget(self.tree, 1)
        self.refresh()

    def refresh(self) -> None:
        self.tree.clear()
        grouped: dict[str, list] = {}
        for scenario in self._registry.enabled():
            if scenario.kind != 'atomic':
                continue
            grouped.setdefault(scenario.group, []).append(scenario)
        for group_name, scenarios in grouped.items():
            group_item = QTreeWidgetItem([group_name])
            group_item.setData(0, Qt.UserRole, None)
            group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)
            self.tree.addTopLevelItem(group_item)
            for scenario in scenarios:
                item = QTreeWidgetItem([scenario.title])
                item.setData(0, Qt.UserRole, scenario.id)
                item.setToolTip(0, scenario.description)
                group_item.addChild(item)
            group_item.setExpanded(True)

    def select_scenario(self, scenario_id: str) -> None:
        matches = self.tree.findItems('', Qt.MatchContains | Qt.MatchRecursive, 0)
        for item in matches:
            if item.data(0, Qt.UserRole) == scenario_id:
                self.tree.setCurrentItem(item)
                return

    def _selection_changed(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        scenario_id = item.data(0, Qt.UserRole)
        if scenario_id:
            self.scenario_selected.emit(str(scenario_id))
