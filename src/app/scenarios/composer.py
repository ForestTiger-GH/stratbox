from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QWidget,
)

from app.scenarios.models import ScenarioParamSpec, ScenarioSpec


class ScenarioComposer(QWidget):
    submitted = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._spec: ScenarioSpec | None = None
        self._widgets: dict[str, QWidget] = {}
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(16, 12, 16, 12)
        self._row.setSpacing(10)
        self._placeholder = QLabel('Выберите сценарий слева')
        self._placeholder.setObjectName('composerPlaceholder')
        self._row.addWidget(self._placeholder)
        self._row.addStretch(1)

    @property
    def current_spec(self) -> ScenarioSpec | None:
        return self._spec

    def set_scenario(self, spec: ScenarioSpec | None) -> None:
        self._spec = spec
        self._reset()
        if spec is None:
            self._placeholder = QLabel('Выберите сценарий слева')
            self._placeholder.setObjectName('composerPlaceholder')
            self._row.addWidget(self._placeholder)
            self._row.addStretch(1)
            return

        title = QLabel(spec.title)
        title.setObjectName('composerScenarioTitle')
        self._row.addWidget(title)

        for param in spec.params:
            widget = self._build_param_widget(param)
            self._widgets[param.name] = widget
            self._row.addWidget(widget)

        self._row.addStretch(1)

    def _reset(self) -> None:
        while self._row.count():
            item = self._row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._widgets.clear()

    def _build_param_widget(self, spec: ScenarioParamSpec) -> QWidget:
        if spec.type == 'bool':
            widget = QCheckBox(spec.title)
            widget.setChecked(bool(spec.default))
            widget.setObjectName('composerCheckBox')
            return widget
        if spec.type == 'select':
            combo = QComboBox()
            combo.setObjectName('composerComboBox')
            combo.setMinimumWidth(180)
            for option in spec.options:
                combo.addItem(option, option)
            default_value = str(spec.default) if spec.default is not None else None
            if default_value:
                idx = combo.findData(default_value)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.setToolTip(spec.description)
            return combo

        line = QLineEdit()
        line.setObjectName('composerLineEdit')
        line.setPlaceholderText(spec.title)
        if spec.default not in (None, ''):
            line.setText(str(spec.default))
        line.setToolTip(spec.description)
        line.setMinimumWidth(180)
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.returnPressed.connect(self.submitted.emit)
        return line

    def collect_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self._spec is None:
            return params
        for param in self._spec.params:
            widget = self._widgets.get(param.name)
            if widget is None:
                continue
            if isinstance(widget, QCheckBox):
                params[param.name] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                params[param.name] = widget.currentData() or widget.currentText()
            elif isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if param.type == 'int':
                    params[param.name] = int(text) if text else int(param.default or 0)
                elif param.type == 'float':
                    params[param.name] = float(text) if text else float(param.default or 0)
                else:
                    params[param.name] = text or param.default
        return params
