from __future__ import annotations

from datetime import datetime

from .models import BackgroundProcessSpec, BackgroundProcessState


class BackgroundProcessStore:
    def __init__(self, items: tuple[BackgroundProcessSpec, ...]):
        self._specs = {item.id: item for item in items}
        self._states: dict[str, BackgroundProcessState] = {
            item.id: BackgroundProcessState(
                process_id=item.id,
                enabled=item.enabled_by_default,
                status=('idle' if item.enabled_by_default else 'disabled'),
            )
            for item in items
        }

    def all(self) -> tuple[BackgroundProcessSpec, ...]:
        return tuple(self._specs.values())

    def spec(self, process_id: str) -> BackgroundProcessSpec:
        return self._specs[process_id]

    def state(self, process_id: str) -> BackgroundProcessState:
        return self._states[process_id]

    def states(self) -> tuple[BackgroundProcessState, ...]:
        return tuple(self._states[item.id] for item in self.all())

    def enabled_ids(self) -> tuple[str, ...]:
        return tuple(sorted(pid for pid, state in self._states.items() if state.enabled))

    def enabled_states(self) -> tuple[BackgroundProcessState, ...]:
        return tuple(state for state in self.states() if state.enabled)

    def active_states(self) -> tuple[BackgroundProcessState, ...]:
        return tuple(state for state in self.states() if state.status in {'running', 'warning', 'error'})

    def is_enabled(self, process_id: str) -> bool:
        return self._states.get(process_id, BackgroundProcessState(process_id)).enabled

    def set_enabled(self, process_id: str, enabled: bool) -> None:
        if process_id not in self._states:
            return
        state = self._states[process_id]
        state.enabled = enabled
        state.status = 'idle' if enabled else 'disabled'
        state.last_result = 'Процесс включён.' if enabled else 'Процесс выключен.'
        state.last_error = ''

    def mark_running(self, process_id: str) -> None:
        state = self._states[process_id]
        state.enabled = True
        state.status = 'running'
        state.last_run_at = datetime.now()

    def mark_result(self, process_id: str, *, result: str, warning: bool = False) -> None:
        state = self._states[process_id]
        state.enabled = True
        state.status = 'warning' if warning else 'idle'
        state.last_run_at = datetime.now()
        state.last_result = result
        state.last_error = ''

    def mark_error(self, process_id: str, *, error: str) -> None:
        state = self._states[process_id]
        state.enabled = True
        state.status = 'error'
        state.last_run_at = datetime.now()
        state.last_error = error
