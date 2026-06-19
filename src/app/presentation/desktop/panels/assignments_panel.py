from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from app.application.assignments.store import AssignmentStore


class AssignmentsPanel(QWidget):
    assignment_selected = Signal(str)
    case_selected = Signal(str)

    def __init__(self, store: AssignmentStore, parent=None) -> None:
        super().__init__(parent)
        self._store = store
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 14, 18)
        layout.setSpacing(12)
        title = QLabel('Поручения')
        title.setObjectName('leftPanelTitle')
        layout.addWidget(title)
        hint = QLabel('Поручения связывают пользователей, сценарии, кейсы и артефакты. Пока слой работает локально, но уже живёт как отдельная модель.')
        hint.setObjectName('leftPanelHint')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.active_list = QListWidget()
        self.active_list.setObjectName('artifactList')
        self.active_list.itemDoubleClicked.connect(self._open_assignment)
        layout.addWidget(QLabel('Активные'))
        layout.addWidget(self.active_list, 1)
        self.completed_list = QListWidget()
        self.completed_list.setObjectName('artifactList')
        layout.addWidget(QLabel('Завершённые'))
        layout.addWidget(self.completed_list, 1)
        self.complete_button = QPushButton('Завершить выбранное')
        self.complete_button.setObjectName('secondaryActionButton')
        self.complete_button.clicked.connect(self._complete_current)
        layout.addWidget(self.complete_button)
        self.refresh()

    def refresh(self) -> None:
        self.active_list.clear()
        self.completed_list.clear()
        for assignment in self._store.active():
            item = QListWidgetItem(f'{assignment.title}\nисполнитель: {assignment.assignee_id or "-"} · автор: {assignment.author_id or "-"}')
            item.setData(Qt.UserRole, assignment.assignment_id)
            item.setToolTip(assignment.description)
            self.active_list.addItem(item)
        if self.active_list.count() == 0:
            self.active_list.addItem(QListWidgetItem('Активных поручений пока нет.'))
        for assignment in self._store.completed():
            item = QListWidgetItem(f'{assignment.title}\nзавершено: {assignment.timestamp_label}')
            item.setData(Qt.UserRole, assignment.assignment_id)
            self.completed_list.addItem(item)
        if self.completed_list.count() == 0:
            self.completed_list.addItem(QListWidgetItem('Завершённых поручений пока нет.'))

    def _current_assignment_id(self) -> str | None:
        item = self.active_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _complete_current(self) -> None:
        assignment_id = self._current_assignment_id()
        if assignment_id:
            self._store.complete(assignment_id)
            self.refresh()
            self.assignment_selected.emit(assignment_id)

    def _open_assignment(self) -> None:
        assignment_id = self._current_assignment_id()
        if not assignment_id:
            return
        self.assignment_selected.emit(assignment_id)
        assignment = self._store.get(assignment_id)
        if assignment.case_id:
            self.case_selected.emit(assignment.case_id)
