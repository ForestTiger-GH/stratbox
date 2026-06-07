from __future__ import annotations

from app.runtime.context import AppContext
from app.application.workspace import run_workspace_diagnostics, resolve_workspace_root


def build_diagnostics_text(context: AppContext) -> str:
    resolution = resolve_workspace_root(
        context.workspace_schema,
        context.data_root_selector_path,
        run_mode=context.run_mode,
        create_missing=False,
    )
    report = run_workspace_diagnostics(context.workspace_schema, resolution)
    lines = [
        'Application: Strategy Box',
        f'Launch mode: {context.run_mode}',
        f'Launch origin: {context.launch_origin}',
        f'Node id: {context.node_id or "-"}',
        f'Session id: {context.session_id or "-"}',
        f'User: {context.account_name or context.user_id or "-"}',
        f'Host: {context.host_name or "-"}',
        f'Workspace schema: {context.workspace_schema.title}',
        f'Selector: {context.data_root_selector_path or "-"}',
        f'Workspace root: {context.workspace_root_path or "-"}',
        f'Degraded launch: {context.degraded_launch}',
        f'Source commit: {context.version.commit_short}',
        '',
        'Workspace diagnostics:',
    ]
    for item in report.items:
        marker = 'OK' if item.ok else item.severity.upper()
        lines.append(f'- [{marker}] {item.title}: {item.details}')
    if context.health_snapshot is not None:
        lines.extend(
            [
                '',
                'Health snapshot:',
                f'- overall: {context.health_snapshot.overall_status}',
                f'- install: {context.health_snapshot.install_status}',
                f'- runtime: {context.health_snapshot.runtime_status}',
                f'- source: {context.health_snapshot.source_status}',
                f'- data: {context.health_snapshot.data_status}',
            ]
        )
    return '\n'.join(lines)
