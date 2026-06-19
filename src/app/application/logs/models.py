from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

LogStatus = Literal["info", "running", "success", "warning", "error"]


@dataclass(slots=True)
class LogRecord:
    log_id: str
    title: str
    path: str
    created_at: datetime
    status: LogStatus = "info"
    case_id: str | None = None
    scenario_id: str | None = None
    operation_id: str | None = None
    step_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        title: str,
        path: str,
        status: LogStatus = "info",
        case_id: str | None = None,
        scenario_id: str | None = None,
        operation_id: str | None = None,
        step_id: str | None = None,
    ) -> "LogRecord":
        return cls(
            log_id=uuid4().hex,
            title=title,
            path=str(Path(path)),
            created_at=datetime.now(),
            status=status,
            case_id=case_id,
            scenario_id=scenario_id,
            operation_id=operation_id,
            step_id=step_id,
        )

    @property
    def timestamp_label(self) -> str:
        return self.created_at.strftime("%H:%M")
