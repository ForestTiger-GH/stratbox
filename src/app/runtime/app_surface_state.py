from __future__ import annotations

from app.runtime.context import AppContext


class AppSurfaceStateService:
    def __init__(self, context: AppContext) -> None:
        self._context = context

    def mark_running(self) -> None:
        if self._context.session_client is not None:
            self._context.session_client.mark_running(active_view='timeline')

    def mark_closed(self, *, clean_shutdown: bool) -> None:
        if self._context.session_client is not None:
            self._context.session_client.mark_ended(clean_shutdown=clean_shutdown, active_view='closed')

    def update_runtime(
        self,
        *,
        active_view: str,
        selected_object: str | None = None,
        active_job: str | None = None,
        last_operation_id: str | None = None,
        last_operation_title: str | None = None,
        last_operation_ok: bool | None = None,
        last_outputs: tuple[str, ...] = tuple(),
        last_operation_log: str | None = None,
        recent_artifacts: tuple[str, ...] = tuple(),
    ) -> None:
        if self._context.session_client is None:
            return
        self._context.session_client.update_runtime_state(
            active_view=active_view,
            selected_object=selected_object,
            active_job=active_job,
            last_operation_id=last_operation_id,
            last_operation_title=last_operation_title,
            last_operation_ok=last_operation_ok,
            last_outputs=last_outputs,
            last_operation_log=last_operation_log,
            recent_artifacts=recent_artifacts,
            workspace_schema_id=self._context.workspace_schema.id,
            effective_workspace_root=(str(self._context.workspace_root_path) if self._context.workspace_root_path else None),
            selected_data_root_path=(str(self._context.data_root_selector_path) if self._context.data_root_selector_path else None),
            surface_state={
                'selected_data_root_path': (str(self._context.data_root_selector_path) if self._context.data_root_selector_path else None),
                'workspace_root_path': (str(self._context.workspace_root_path) if self._context.workspace_root_path else None),
            },
        )
