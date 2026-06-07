from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from app.application.product.forms.models import ProductParamSpec


def build_widget_for_param(parent: QWidget, spec: ProductParamSpec) -> QWidget:
    if spec.type == 'bool':
        widget = QCheckBox(parent)
        widget.setObjectName('composerCheckBox')
        widget.setChecked(bool(spec.default))
        return widget
    if spec.type == 'select':
        widget = QComboBox(parent)
        widget.setObjectName('composerComboBox')
        for label, value in spec.options:
            widget.addItem(label, value)
        selected_index = max(0, widget.findData(spec.default))
        widget.setCurrentIndex(selected_index)
        return widget
    if spec.type == 'int':
        widget = QSpinBox(parent)
        widget.setObjectName('composerSpinBox')
        widget.setRange(spec.min_value if spec.min_value is not None else -1_000_000, spec.max_value if spec.max_value is not None else 1_000_000)
        if spec.default is not None:
            widget.setValue(int(spec.default))
        return widget
    if spec.type in {'path_dir', 'path_file'}:
        host = QWidget(parent)
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        edit = QLineEdit(host)
        edit.setObjectName('composerLineEdit')
        if spec.default not in (None, ''):
            edit.setText(str(spec.default))
        if spec.placeholder:
            edit.setPlaceholderText(spec.placeholder)
        button = QPushButton('Обзор…', host)
        button.setObjectName('feedActionButton')

        def _choose() -> None:
            if spec.type == 'path_dir':
                value = QFileDialog.getExistingDirectory(host, spec.title, edit.text() or '')
            else:
                value, _ = QFileDialog.getSaveFileName(host, spec.title, edit.text() or '')
            if value:
                edit.setText(value)

        button.clicked.connect(_choose)
        row.addWidget(edit, 1)
        row.addWidget(button)
        host._composer_edit = edit  # type: ignore[attr-defined]
        return host
    widget = QLineEdit(parent)
    widget.setObjectName('composerLineEdit')
    if spec.default not in (None, ''):
        widget.setText(str(spec.default))
    if spec.placeholder:
        widget.setPlaceholderText(spec.placeholder)
    return widget
