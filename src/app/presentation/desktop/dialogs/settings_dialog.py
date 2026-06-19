from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget

from app.application.system.commands import build_diagnostics_text
from app.runtime.bootstrap import AppRuntime


class SettingsDialog(QDialog):
    def __init__(self, runtime: AppRuntime, parent=None) -> None:
        super().__init__(parent)
        self._runtime = runtime
        self.setWindowTitle('Настройки Strategy Box')
        self.resize(760, 560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        tabs = QTabWidget()
        tabs.addTab(self._user_page(), 'Пользовательские')
        tabs.addTab(self._workspace_page(), 'Рабочие')
        tabs.addTab(self._system_page(), 'Системные')
        layout.addWidget(tabs)

    def _title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName('leftPanelTitle')
        return label

    def _text(self, body: str) -> QLabel:
        label = QLabel(body)
        label.setObjectName('composerPlaceholder')
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return label

    def _user_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addWidget(self._title('Поведение интерфейса'))
        self.open_right = QCheckBox('Открывать правую панель при запуске')
        self.open_right.setChecked(self._runtime.context.user_config.shell.right_inspector_open)
        self.open_right.toggled.connect(lambda checked: self._runtime.preferences.save(right_inspector_open=bool(checked)))
        layout.addWidget(self.open_right)
        layout.addWidget(QLabel('Стартовый режим слева'))
        self.mode_box = QComboBox()
        modes = [
            ('workspace', 'Проводник'),
            ('atomic_scenarios', 'Отдельные сценарии'),
            ('scenario_blocks', 'Сценарные блоки'),
            ('background', 'Фоновые процессы'),
            ('people', 'Участники'),
            ('assignments', 'Поручения'),
        ]
        for value, label in modes:
            self.mode_box.addItem(label, value)
        current_mode = self._runtime.context.user_config.shell.selected_mode
        index = max(0, self.mode_box.findData(current_mode))
        self.mode_box.setCurrentIndex(index)
        self.mode_box.currentIndexChanged.connect(lambda _: self._runtime.preferences.save(selected_mode=str(self.mode_box.currentData())))
        layout.addWidget(self.mode_box)
        layout.addWidget(QLabel('Стартовая вкладка правой панели'))
        self.tab_box = QComboBox()
        for value, label in [('case', 'Кейс'), ('logs', 'Логи'), ('artifacts', 'Артефакты'), ('parameters', 'Параметры'), ('node', 'Узел')]:
            self.tab_box.addItem(label, value)
        self.tab_box.setCurrentIndex(max(0, self.tab_box.findData(self._runtime.context.user_config.shell.right_inspector_tab)))
        self.tab_box.currentIndexChanged.connect(lambda _: self._runtime.preferences.save(right_inspector_tab=str(self.tab_box.currentData())))
        layout.addWidget(self.tab_box)
        layout.addStretch(1)
        return page

    def _workspace_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        ctx = self._runtime.context
        layout.addWidget(self._title('Рабочая среда'))
        layout.addWidget(self._text(
            f'Workspace schema: {ctx.workspace_schema.id} · {ctx.workspace_schema.title}\n'
            f'Workspace root: {ctx.workspace_root_path or "не выбран"}\n'
            f'Data root selector: {ctx.data_root_selector_path or "-"}\n'
            f'Status: {ctx.workspace_status.message}'
        ))
        open_button = QPushButton('Открыть workspace')
        open_button.setObjectName('secondaryActionButton')
        open_button.clicked.connect(lambda: ctx.workspace_root_path and self._runtime.platform.open_path(str(ctx.workspace_root_path)))
        layout.addWidget(open_button)
        copy_button = QPushButton('Скопировать путь workspace')
        copy_button.setObjectName('secondaryActionButton')
        copy_button.clicked.connect(lambda: ctx.workspace_root_path and self._runtime.platform.copy_text(str(ctx.workspace_root_path)))
        layout.addWidget(copy_button)
        layout.addStretch(1)
        return page

    def _system_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        ctx = self._runtime.context
        layout.addWidget(self._title('Системное состояние'))
        layout.addWidget(self._text(
            f'Run mode: {ctx.run_mode}\n'
            f'Launch origin: {ctx.launch_origin}\n'
            f'Node: {ctx.node_id or "local"}\n'
            f'Session: {ctx.session_id or "-"}\n'
            f'User: {ctx.account_name or ctx.user_id or "-"}\n'
            f'Host: {ctx.host_name or "-"}\n'
            f'Source commit: {ctx.version.commit_short or ctx.version.commit or "-"}'
        ))
        copy_diag = QPushButton('Скопировать диагностику')
        copy_diag.setObjectName('secondaryActionButton')
        copy_diag.clicked.connect(lambda: self._runtime.platform.copy_text(build_diagnostics_text(ctx)))
        layout.addWidget(copy_diag)
        layout.addStretch(1)
        return page
