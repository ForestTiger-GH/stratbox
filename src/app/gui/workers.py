"""Совместимый re-export run worker.

Фактическая реализация worker теперь живёт в ``app.runs.workers``.
"""

from app.runs.workers import ScenarioWorker

__all__ = ["ScenarioWorker"]
