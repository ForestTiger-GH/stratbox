from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QMenu, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from app.runtime.context import AppContext


class WorkspacePanel(QWidget):
    path_selected = Signal(str)
    open_path_requested = Signal(str)
    copy_path_requested = Signal(str)

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self._context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 14, 18)
        layout.setSpacing(12)
        title = QLabel('Проводник')
        title.setObjectName('leftPanelTitle')
        layout.addWidget(title)
        hint = QLabel('Рабочий каталог, входные данные, кэш, результаты, логи и архивы.')
        hint.setObjectName('leftPanelHint')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setObjectName('workspaceTree')
        self.tree.itemDoubleClicked.connect(self._open_current)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_menu)
        layout.addWidget(self.tree, 1)
        self.refresh()

    def refresh(self) -> None:
        self.tree.clear()
        root = self._context.workspace_root_path
        if root is None:
            item = QTreeWidgetItem(['Workspace недоступен'])
            self.tree.addTopLevelItem(item)
            return
        root_item = QTreeWidgetItem([str(root)])
        root_item.setData(0, Qt.UserRole, str(root))
        self.tree.addTopLevelItem(root_item)
        for name in ('input', 'cache', 'output', 'logs', 'archives'):
            path = root / name
            child = QTreeWidgetItem([name])
            child.setData(0, Qt.UserRole, str(path))
            root_item.addChild(child)
            if path.exists() and path.is_dir():
                for nested in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:80]:
                    nested_item = QTreeWidgetItem([nested.name])
                    nested_item.setData(0, Qt.UserRole, str(nested))
                    child.addChild(nested_item)
        root_item.setExpanded(True)

    def _current_path(self) -> str | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        value = item.data(0, Qt.UserRole)
        return str(value) if value else None

    def _open_current(self) -> None:
        path = self._current_path()
        if path:
            self.open_path_requested.emit(path)

    def _show_menu(self, pos) -> None:
        path = self._current_path()
        if not path:
            return
        menu = QMenu(self)
        open_action = menu.addAction('Открыть')
        copy_action = menu.addAction('Скопировать путь')
        selected = menu.exec(self.tree.mapToGlobal(pos))
        if selected == open_action:
            self.open_path_requested.emit(path)
        elif selected == copy_action:
            self.copy_path_requested.emit(path)
