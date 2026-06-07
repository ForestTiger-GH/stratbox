from __future__ import annotations

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation, Qt
from PySide6.QtGui import QGuiApplication, QWheelEvent
from PySide6.QtWidgets import QScrollArea


class SmoothScrollArea(QScrollArea):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._animated_scroll_value = self.verticalScrollBar().value()
        self._scroll_animation = QPropertyAnimation(self, b'animatedScrollValue', self)
        self._scroll_animation.setDuration(160)
        self._scroll_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.verticalScrollBar().rangeChanged.connect(self._sync_animation_range)
        self.verticalScrollBar().valueChanged.connect(self._sync_animation_value)
        self._apply_scroll_tuning()

    def _apply_scroll_tuning(self) -> None:
        line_height = max(24, self.fontMetrics().lineSpacing() * 2)
        self.verticalScrollBar().setSingleStep(line_height // 2)
        self.verticalScrollBar().setPageStep(max(1, self.viewport().height() - 48))

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_scroll_tuning()
        widget = self.widget()
        if widget is not None and hasattr(widget, 'relayout_for_width'):
            widget.relayout_for_width(self.viewport().width())

    def wheelEvent(self, event: QWheelEvent) -> None:  # type: ignore[override]
        if event.modifiers() & Qt.ControlModifier:
            super().wheelEvent(event)
            return

        pixel_delta = event.pixelDelta().y()
        if pixel_delta:
            self._scroll_animation.stop()
            self.animatedScrollValue = self.verticalScrollBar().value() - pixel_delta
            event.accept()
            return

        angle_delta = event.angleDelta().y()
        if angle_delta:
            step_lines = self._wheel_scroll_lines()
            line_height = max(24, self.fontMetrics().lineSpacing() * 2)
            steps = angle_delta / 120.0
            pixel_step = line_height * step_lines
            self._animate_scroll_to(self.verticalScrollBar().value() - (steps * pixel_step))
            event.accept()
            return

        super().wheelEvent(event)

    def _wheel_scroll_lines(self) -> int:
        style_hints = QGuiApplication.styleHints()
        try:
            lines = style_hints.wheelScrollLines()
        except AttributeError:
            lines = 3
        return max(1, int(lines or 3))

    def _animate_scroll_to(self, value: float) -> None:
        bar = self.verticalScrollBar()
        target = self._bounded_value(value)
        current = bar.value()
        if current == target:
            self._scroll_animation.stop()
            return
        self._scroll_animation.stop()
        self._scroll_animation.setStartValue(current)
        self._scroll_animation.setEndValue(target)
        self._scroll_animation.start()

    def _sync_animation_range(self, _min_value: int, _max_value: int) -> None:
        self._animated_scroll_value = self.verticalScrollBar().value()

    def _sync_animation_value(self, value: int) -> None:
        self._animated_scroll_value = value

    def _get_animated_scroll_value(self) -> int:
        return self._animated_scroll_value

    def _set_animated_scroll_value(self, value: float) -> None:
        bounded = self._bounded_value(value)
        self._animated_scroll_value = bounded
        self.verticalScrollBar().setValue(bounded)

    def _bounded_value(self, value: float) -> int:
        bar = self.verticalScrollBar()
        return max(bar.minimum(), min(bar.maximum(), int(round(value))))

    animatedScrollValue = Property(int, _get_animated_scroll_value, _set_animated_scroll_value)
