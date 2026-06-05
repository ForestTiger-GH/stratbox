from __future__ import annotations

from app.core.context import AppContext


class AppDockBridge:
    def __init__(self, context: AppContext) -> None:
        self.context = context

    def online_label(self) -> str:
        if self.context.run_mode != 'appdock_managed':
            return 'локальный режим'
        if self.context.active_session is not None:
            return 'активная AppDock-сессия'
        return 'управляемая AppDock-сессия'

    def host_mode_label(self) -> str:
        return 'через AppDock' if self.context.run_mode == 'appdock_managed' else 'локально'
