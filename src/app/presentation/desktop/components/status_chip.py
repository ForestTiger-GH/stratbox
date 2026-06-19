from __future__ import annotations

from PySide6.QtWidgets import QLabel


_STATUS_LABELS = {
    'prepared': 'Подготовлено',
    'queued': 'В очереди',
    'running': 'Выполняется',
    'success': 'Завершено',
    'warning': 'С замечаниями',
    'failed': 'Ошибка',
    'cancelled': 'Отменено',
    'info': 'Инфо',
    'error': 'Ошибка',
    'disabled': 'Отключено',
    'enabled': 'Включено',
}


class StatusChip(QLabel):
    def __init__(self, status: str = 'info', parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('statusChip')
        self.set_status(status)

    def set_status(self, status: str, text: str | None = None) -> None:
        self.setProperty('status', status)
        self.setText(text or _STATUS_LABELS.get(status, status))
        self.style().unpolish(self)
        self.style().polish(self)
