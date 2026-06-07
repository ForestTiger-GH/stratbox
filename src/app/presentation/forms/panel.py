from __future__ import annotations

from html import escape
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.runtime.user_preferences import PreferencesService
from app.application.product.catalog.models import ProductOperationSpec
from app.application.product.forms.models import ProductParamSpec
from app.application.product.forms.validators import validate_field_value
from app.presentation.forms.widgets import build_widget_for_param


class OperationFormPanel(QWidget):
    submitted = Signal()

    def __init__(self, *, preferences: PreferencesService | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._preferences = preferences
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
        title.setObjectName('composerOperationTitle')
        title.setWordWrap(True)
        self._column.addWidget(title)
        if spec.description:
            description = QLabel(spec.description)
            description.setWordWrap(True)
            description.setObjectName('composerPlaceholder')
            self._column.addWidget(description)

        remembered = self._preferences.load_operation_values(spec.id) if self._preferences is not None else {}
        visible_params = spec.visible_params()
        basic_params = [param for param in visible_params if getattr(param, 'section', 'basic') == 'basic']
        advanced_params = [param for param in visible_params if getattr(param, 'section', 'basic') == 'advanced']
        if basic_params:
            self._column.addWidget(self._section_label('Основные параметры'))
            for param in basic_params:
                self._column.addWidget(self._build_param_block(param, remembered.get(param.name)))
        if advanced_params:
            self._column.addWidget(self._section_label('Дополнительно'))
            for param in advanced_params:
                self._column.addWidget(self._build_param_block(param, remembered.get(param.name)))
        self._column.addStretch(1)

    def collect_params(self) -> dict[str, Any]:
        if self._spec is None:
            return {}
        params: dict[str, Any] = {}
        for param in self._spec.visible_params():
            widget = self._widgets[param.name]
            if param.type == 'bool':
                value = bool(widget.isChecked())  # type: ignore[attr-defined]
            elif param.type == 'select':
                value = str(widget.currentData())  # type: ignore[attr-defined]
            elif param.type == 'int':
                value = int(widget.value())  # type: ignore[attr-defined]
            elif param.type in {'path_dir', 'path_file'}:
                value = str(widget._composer_edit.text()).strip()  # type: ignore[attr-defined]
            else:
                value = str(widget.text()).strip()  # type: ignore[attr-defined]
            validate_field_value(param, value)
            params[param.name] = value
        if self._preferences is not None and self._spec is not None:
            self._preferences.save_operation_values(self._spec.id, params)
        return params

    def _build_param_block(self, param: ProductParamSpec, remembered_value: Any = None) -> QWidget:
        host = QWidget(self)
        box = QVBoxLayout(host)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(6)
        label = self._build_param_label(param)
        box.addWidget(label)
        widget = build_widget_for_param(self, param)
        box.addWidget(widget)
        if remembered_value not in (None, ''):
            self._apply_value(widget, param, remembered_value)
        self._widgets[param.name] = widget
        return host

    def _build_param_label(self, param: ProductParamSpec) -> QLabel:
        label = QLabel(param.title)
        label.setWordWrap(True)
        if param.description:
            label.setObjectName('composerFieldLabelHinted')
            label.setToolTip(param.description)
            label.setCursor(Qt.WhatsThisCursor)
            label.setTextFormat(Qt.RichText)
            label.setText(f"<span style='text-decoration: underline;'>{escape(param.title)}</span>")
        else:
            label.setObjectName('composerFieldLabel')
        return label

    def _apply_value(self, widget: QWidget, param: ProductParamSpec, value: Any) -> None:
        if param.type == 'bool':
            widget.setChecked(bool(value))  # type: ignore[attr-defined]
        elif param.type == 'select':
            idx = widget.findData(value)  # type: ignore[attr-defined]
            if idx >= 0:
                widget.setCurrentIndex(idx)  # type: ignore[attr-defined]
        elif param.type == 'int':
            widget.setValue(int(value))  # type: ignore[attr-defined]
        elif param.type in {'path_dir', 'path_file'}:
            widget._composer_edit.setText(str(value))  # type: ignore[attr-defined]
        else:
            widget.setText(str(value))  # type: ignore[attr-defined]

    def _reset(self) -> None:
        self._widgets.clear()
        while self._column.count():
            item = self._column.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_placeholder(self) -> None:
        title = QLabel('Операция не выбрана')
        title.setObjectName('composerPlaceholderTitle')
        body = QLabel('Выберите операцию слева, чтобы увидеть параметры запуска.')
        body.setObjectName('composerPlaceholder')
        body.setWordWrap(True)
        self._column.addWidget(title)
        self._column.addWidget(body)
        self._column.addStretch(1)

    def _section_label(self, title_text: str) -> QLabel:
        label = QLabel(title_text)
        label.setObjectName('composerSectionTitle')
        return label
