from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from app.application.system.commands import build_diagnostics_text
from app.runtime.bootstrap import AppRuntime


class NodeOverviewPanel(QWidget):
    def __init__(self, runtime: AppRuntime, parent=None) -> None:
        super().__init__(parent)
        self._runtime = runtime
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        title = QLabel('Узел')
        title.setObjectName('leftPanelTitle')
        layout.addWidget(title)
        self.body = QLabel('')
        self.body.setObjectName('composerPlaceholder')
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.body, 1)
        self.copy_button = QPushButton('Скопировать диагностику')
        self.copy_button.setObjectName('secondaryActionButton')
        self.copy_button.clicked.connect(self._copy_diagnostics)
        layout.addWidget(self.copy_button)
        self.refresh()

    def refresh(self) -> None:
        ctx = self._runtime.context
        health = ctx.health_snapshot
        version = ctx.version
        lines = [
            f'Режим: {ctx.run_mode}',
            f'Запуск: {ctx.launch_origin}',
            f'Пользователь: {ctx.account_name or ctx.user_id or "локальный"}',
            f'Хост: {ctx.host_name or "-"}',
            f'Node: {ctx.node_id or "local"}',
            f'Session: {ctx.session_id or "-"}',
            f'Workspace: {ctx.workspace_root_path or "не выбран"}',
            f'Data root: {ctx.data_root_selector_path or "-"}',
            f'Commit: {version.commit_short or version.commit or "-"}',
        ]
        if health is not None:
            lines.extend([
                '',
                f'Health: {health.overall_status}',
                f'Install: {health.install_status}',
                f'Source: {health.source_status}',
                f'Runtime: {health.runtime_status}',
                f'Venv: {health.venv_status}',
                f'Data: {health.data_status}',
            ])
        self.body.setText('\n'.join(lines))

    def _copy_diagnostics(self) -> None:
        self._runtime.platform.copy_text(build_diagnostics_text(self._runtime.context))
