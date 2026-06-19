from __future__ import annotations

from PySide6.QtWidgets import QDialog, QPlainTextEdit, QVBoxLayout


class DiagnosticsDialog(QDialog):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Диагностика')
        self.resize(920, 620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        viewer = QPlainTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(text)
        layout.addWidget(viewer)
