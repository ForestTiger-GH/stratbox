from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class Section(QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('section')
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        label = QLabel(title)
        label.setObjectName('sectionTitle')
        self.layout.addWidget(label)

    def add(self, widget: QWidget) -> None:
        self.layout.addWidget(widget)
