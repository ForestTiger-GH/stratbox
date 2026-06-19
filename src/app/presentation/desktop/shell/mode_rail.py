from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout


class ShellMode:
    WORKSPACE = 'workspace'
    ATOMIC_SCENARIOS = 'atomic_scenarios'
    SCENARIO_BLOCKS = 'scenario_blocks'
    BACKGROUND = 'background'
    PEOPLE = 'people'


class ModeRail(QFrame):
    mode_changed = Signal(str)

    _ITEMS = (
        (ShellMode.WORKSPACE, '📁', 'Проводник'),
        (ShellMode.ATOMIC_SCENARIOS, '⚙', 'Отдельные сценарии'),
        (ShellMode.SCENARIO_BLOCKS, '🧩', 'Сценарные блоки'),
        (ShellMode.BACKGROUND, '◷', 'Фоновые процессы'),
        (ShellMode.PEOPLE, '👥', 'Пользователи'),
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('modeRail')
        self._buttons: dict[str, QPushButton] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(10)
        for mode, icon, tooltip in self._ITEMS:
            button = QPushButton(icon)
            button.setObjectName('modeRailButton')
            button.setCheckable(True)
            button.setFixedSize(44, 44)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda checked=False, value=mode: self.set_mode(value, emit=True))
            self._buttons[mode] = button
            layout.addWidget(button)
        layout.addStretch(1)

    def set_mode(self, mode: str, *, emit: bool = False) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == mode)
            button.setProperty('active', key == mode)
            button.style().unpolish(button)
            button.style().polish(button)
        if emit:
            self.mode_changed.emit(mode)
