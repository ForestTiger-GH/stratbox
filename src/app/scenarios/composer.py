from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.scenarios.models import ScenarioParamSpec, ScenarioSpec


class ScenarioComposer(QWidget):
    submitted = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._spec: ScenarioSpec | None = None
        self._widgets: dict[str, QWidget] = {}
        self._column = QVBoxLayout(self)
        self._column.setContentsMargins(16, 12, 16, 12)
        self._column.setSpacing(10)
        self._render_placeholder()

    @property
    def current_spec(self) -> ScenarioSpec | None:
        return self._spec

    def set_scenario(self, spec: ScenarioSpec | None) -> None:
        self._spec = spec
        self._reset()
        if spec is None:
            self._render_placeholder()
            return

        title = QLabel(spec.title)
        title.setObjectName('composerScenarioTitle')
        title.setWordWrap(True)
        self._column.addWidget(title)

        for param in spec.params:
            block = self._build_param_block(param)
            self._column.addWidget(block)

        self._column.addStretch(1)

    def _render_placeholder(self) -> None:
        placeholder = QLabel('Выберите сценарий слева')
        placeholder.setObjectName('composerPlaceholder')
        self._column.addWidget(placeholder)
        self._column.addStretch(1)

    def _reset(self) -> None:
        while self._column.count():
            item = self._column.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._widgets.clear()

    def _build_param_block(self, spec: ScenarioParamSpec) -> QWidget:
        block = QWidget()
        block.setObjectName('composerParamBlock')
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        if spec.type == 'bool':
            widget = QCheckBox(spec.title)
            widget.setChecked(bool(spec.default))
            widget.setObjectName('composerCheckBox')
            self._widgets[spec.name] = widget
            layout.addWidget(widget)
            return block

        label = QLabel(spec.title)
        label.setObjectName('composerParamLabel')
        layout.addWidget(label)

        widget = self._build_param_widget(spec)
        self._widgets[spec.name] = widget
        layout.addWidget(widget)
        return block

    def _build_param_widget(self, spec: ScenarioParamSpec) -> QWidget:
        if spec.type == 'select':
            combo = QComboBox()
            combo.setObjectName('composerComboBox')
            combo.setMinimumWidth(220)
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        line.setMinimumWidth(220)
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
                    params[param.name] = float(text) if text else float(param.default or 0.0)
                else:
                    params[param.name] = text or str(param.default or '')
        return params
