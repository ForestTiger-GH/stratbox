from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.product.models import ProductOperationSpec, ProductParamSpec


class OperationComposer(QWidget):
    submitted = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._spec: ProductOperationSpec | None = None
        self._widgets: dict[str, QWidget] = {}
        self._column = QVBoxLayout(self)
        self._column.setContentsMargins(16, 12, 16, 12)
        self._column.setSpacing(10)
        self._render_placeholder()

    def set_operation(self, spec: ProductOperationSpec | None) -> None:
        self._spec = spec
        self._reset()
        if spec is None:
            self._render_placeholder()
            return

        title = QLabel(spec.title)
        title.setObjectName('composerScenarioTitle')
        title.setWordWrap(True)
        self._column.addWidget(title)

        if spec.description:
            description = QLabel(spec.description)
            description.setWordWrap(True)
            description.setObjectName('composerPlaceholder')
            self._column.addWidget(description)

        basic_params = [param for param in spec.params if param.section == 'basic']
        advanced_params = [param for param in spec.params if param.section == 'advanced']

        if basic_params:
            self._column.addWidget(self._section_label('Основные параметры'))
            for param in basic_params:
                self._column.addWidget(self._build_param_block(param))

        if advanced_params:
            self._column.addWidget(self._section_label('Дополнительно'))
            for param in advanced_params:
                self._column.addWidget(self._build_param_block(param))

        self._column.addStretch(1)

    def collect_params(self) -> dict[str, Any]:
        if self._spec is None:
            return {}
        params: dict[str, Any] = {}
        for param in self._spec.params:
            widget = self._widgets[param.name]
            if param.type == 'bool':
                value = bool(widget.isChecked())  # type: ignore[attr-defined]
            elif param.type == 'select':
                value = str(widget.currentData())  # type: ignore[attr-defined]
            elif param.type == 'int':
                value = int(widget.value())  # type: ignore[attr-defined]
            else:
                value = str(widget.text()).strip()  # type: ignore[attr-defined]

            if param.required and value in ('', None):
                raise ValueError(f'Параметр «{param.title}» обязателен.')
            params[param.name] = value
        return params

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName('sidebarSectionTitle')
        return label

    def _render_placeholder(self) -> None:
        placeholder = QLabel('Выберите операцию слева')
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

    def _build_param_block(self, spec: ProductParamSpec) -> QWidget:
        block = QFrame()
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
            if spec.description:
                helper = QLabel(spec.description)
                helper.setWordWrap(True)
                helper.setObjectName('composerPlaceholder')
                layout.addWidget(helper)
            return block

        label = QLabel(spec.title)
        label.setObjectName('composerParamLabel')
        layout.addWidget(label)

        widget = self._build_param_widget(spec)
        self._widgets[spec.name] = getattr(widget, '_value_widget', widget)
        layout.addWidget(widget)

        if spec.description:
            helper = QLabel(spec.description)
            helper.setWordWrap(True)
            helper.setObjectName('composerPlaceholder')
            layout.addWidget(helper)
        return block

    def _build_param_widget(self, spec: ProductParamSpec) -> QWidget:
        if spec.type == 'select':
            combo = QComboBox()
            combo.setObjectName('composerField')
            for label, value in spec.options:
                combo.addItem(label, value)
            current_value = str(spec.default) if spec.default is not None else None
            if current_value is not None:
                index = combo.findData(current_value)
                if index >= 0:
                    combo.setCurrentIndex(index)
            return combo

        if spec.type == 'int':
            spin = QSpinBox()
            spin.setObjectName('composerField')
            spin.setMinimum(spec.min_value if spec.min_value is not None else -999999)
            spin.setMaximum(spec.max_value if spec.max_value is not None else 999999)
            if spec.default is not None:
                try:
                    spin.setValue(int(spec.default))
                except Exception:
                    pass
            return spin

        if spec.type in {'path_dir', 'path_file'}:
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            line = QLineEdit(str(spec.default or ''))
            line.setObjectName('composerField')
            if spec.placeholder:
                line.setPlaceholderText(spec.placeholder)
            button = QPushButton('Обзор')
            button.setObjectName('filterPill')

            def _pick() -> None:
                if spec.type == 'path_dir':
                    selected = QFileDialog.getExistingDirectory(self, spec.title, line.text() or str(spec.default or ''))
                else:
                    selected, _ = QFileDialog.getSaveFileName(self, spec.title, line.text() or str(spec.default or ''))
                if selected:
                    line.setText(selected)

            button.clicked.connect(_pick)
            row.addWidget(line, 1)
            row.addWidget(button)
            container._value_widget = line  # type: ignore[attr-defined]
            return container

        line = QLineEdit(str(spec.default or ''))
        line.setObjectName('composerField')
        if spec.placeholder:
            line.setPlaceholderText(spec.placeholder)
        return line
