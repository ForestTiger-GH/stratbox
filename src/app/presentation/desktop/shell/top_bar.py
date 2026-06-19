from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.runtime.bootstrap import AppRuntime


class TopBar(QWidget):
    diagnostics_requested = Signal()
    settings_requested = Signal()
    refresh_requested = Signal()
    exit_requested = Signal()

    def __init__(self, runtime: AppRuntime, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('topBar')
        self._runtime = runtime
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel('Strategy Box')
        title.setObjectName('topBarTitle')
        title_col.addWidget(title)
        self.subtitle = QLabel(self._build_subtitle())
        self.subtitle.setObjectName('topBarSubtle')
        title_col.addWidget(self.subtitle)
        layout.addLayout(title_col)
        layout.addStretch(1)
        self.user_button = QPushButton(runtime.context.account_name or 'Пользователь')
        self.user_button.setObjectName('userMenuButton')
        self.user_button.setToolTip('Меню пользователя: настройки, диагностика, обновление состояния')
        self.user_button.clicked.connect(self._show_menu)
        layout.addWidget(self.user_button)

    def _build_subtitle(self) -> str:
        ctx = self._runtime.context
        node = ctx.node_id or 'local node'
        mode = self._runtime.appdock_bridge.host_mode_label()
        workspace = str(ctx.workspace_root_path) if ctx.workspace_root_path else 'workspace не выбран'
        return f'{mode} · {node} · {workspace}'

    def refresh_context(self) -> None:
        self.subtitle.setText(self._build_subtitle())
        self.user_button.setText(self._runtime.context.account_name or 'Пользователь')

    def _show_menu(self) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        settings = menu.addAction('Настройки')
        refresh = menu.addAction('Обновить состояние')
        diagnostics = menu.addAction('Диагностика')
        menu.addSeparator()
        exit_action = menu.addAction('Выход')
        selected = menu.exec(self.user_button.mapToGlobal(self.user_button.rect().bottomLeft()))
        if selected == settings:
            self.settings_requested.emit()
        elif selected == refresh:
            self.refresh_requested.emit()
        elif selected == diagnostics:
            self.diagnostics_requested.emit()
        elif selected == exit_action:
            self.exit_requested.emit()
