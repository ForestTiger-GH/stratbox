from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

BackgroundProcessStatus = Literal['disabled', 'idle', 'running', 'warning', 'error']


@dataclass(frozen=True, slots=True)
class BackgroundProcessSpec:
    id: str
    title: str
    description: str
    enabled_by_default: bool = False
    schedule_label: str | None = None


@dataclass(slots=True)
class BackgroundProcessState:
    process_id: str
    enabled: bool = False
    status: BackgroundProcessStatus = 'disabled'
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_result: str = ''
    last_error: str = ''

    @property
    def status_label(self) -> str:
        if not self.enabled:
            return 'выключен'
        return {
            'idle': 'включён',
            'running': 'выполняется',
            'warning': 'с замечаниями',
            'error': 'ошибка',
            'disabled': 'выключен',
        }.get(self.status, self.status)

    @property
    def last_run_label(self) -> str:
        return self.last_run_at.strftime('%H:%M') if self.last_run_at else 'ещё не запускался'

    @property
    def next_run_label(self) -> str:
        return self.next_run_at.strftime('%H:%M') if self.next_run_at else 'не запланирован'
