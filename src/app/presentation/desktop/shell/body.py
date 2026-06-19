from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QRect, QVariantAnimation
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from app.runtime.bootstrap import AppRuntime
from .center_panel import CenterScenarioPanel
from .left_panel import LeftPanel
from .mode_rail import ModeRail
from .right_drawer import RightInspectorDrawer


class ShellBodyWidget(QWidget):
    def __init__(self, runtime: AppRuntime, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('shellRoot')
        self.runtime = runtime
        self.drawer_width = runtime.context.user_config.shell.right_inspector_width
        self._drawer_progress = 1.0 if runtime.context.user_config.shell.right_inspector_open else 0.0
        self.main_region = QWidget(self)
        self.main_layout = QHBoxLayout(self.main_region)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.mode_rail = ModeRail()
        self.left_panel = LeftPanel(runtime)
        self.center_panel = CenterScenarioPanel(runtime)
        self.left_panel.setFixedWidth(runtime.context.user_config.shell.left_panel_width)
        self.main_layout.addWidget(self.mode_rail)
        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(self.center_panel, 1)
        self.right_drawer = RightInspectorDrawer(runtime, self)
        self.right_drawer.setFixedWidth(self.drawer_width)
        self.drawer_handle = QPushButton('‹', self)
        self.drawer_handle.setObjectName('rightDrawerHandle')
        self.drawer_handle.setToolTip('Показать / скрыть детали')
        self.drawer_handle.clicked.connect(self.toggle_right_drawer)
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(220)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.valueChanged.connect(lambda value: self.set_drawer_progress(float(value)))
        self.right_drawer.close_requested.connect(lambda: self.set_right_drawer_open(False))
        self._connect_state_persistence()
        self._sync_geometry()

    def _connect_state_persistence(self) -> None:
        self.mode_rail.mode_changed.connect(lambda mode: self.runtime.preferences.save(selected_mode=mode))
        self.center_panel.filter_changed.connect(lambda mode: self.runtime.preferences.save(filter_mode=mode))
        self.right_drawer.tab_changed.connect(lambda tab: self.runtime.preferences.save(right_inspector_tab=tab))

    def set_drawer_progress(self, value: float) -> None:
        self._drawer_progress = max(0.0, min(1.0, value))
        self._sync_geometry()

    def is_right_drawer_open(self) -> bool:
        return self._drawer_progress >= 0.5

    def toggle_right_drawer(self) -> None:
        self.set_right_drawer_open(not self.is_right_drawer_open())

    def set_right_drawer_open(self, open_: bool) -> None:
        target = 1.0 if open_ else 0.0
        self._animation.stop()
        self._animation.setStartValue(self._drawer_progress)
        self._animation.setEndValue(target)
        self._animation.start()
        self.runtime.preferences.save(right_inspector_open=open_)

    def open_right_drawer(self, tab: str | None = None) -> None:
        if tab:
            self.right_drawer.set_active_tab(tab, emit=True)
        self.set_right_drawer_open(True)

    def resizeEvent(self, event) -> None:
        self._sync_geometry()
        super().resizeEvent(event)

    def _sync_geometry(self) -> None:
        w = self.width()
        h = self.height()
        reserved = int(self.drawer_width * self._drawer_progress)
        self.main_region.setGeometry(QRect(0, 0, max(1, w - reserved), h))
        drawer_x = w - reserved
        self.right_drawer.setGeometry(QRect(drawer_x, 0, self.drawer_width, h))
        handle_w = 30
        handle_h = 64
        if self._drawer_progress < 0.05:
            handle_x = max(4, w - handle_w - 6)
        else:
            handle_x = max(0, w - reserved - handle_w // 2)
        self.drawer_handle.setGeometry(QRect(handle_x, 24, handle_w, handle_h))
        self.drawer_handle.setText('›' if self.is_right_drawer_open() else '‹')
