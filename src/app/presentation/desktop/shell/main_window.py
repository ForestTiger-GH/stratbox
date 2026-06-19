from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QMessageBox, QVBoxLayout, QWidget

from app.application.assignments.models import AssignmentRecord
from app.application.events.models import OperationalEvent
from app.application.system.commands import build_diagnostics_text
from app.runtime.bootstrap import AppRuntime
from .body import ShellBodyWidget
from .mode_rail import ShellMode
from .top_bar import TopBar
from app.presentation.desktop.dialogs.diagnostics_dialog import DiagnosticsDialog
from app.presentation.desktop.dialogs.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, runtime: AppRuntime):
        super().__init__()
        self.runtime = runtime
        self.context = runtime.context
        self._selected_scenario_id: str | None = runtime.context.user_config.last_scenario_id
        self._build_ui()
        self._connect_runtime()
        self._seed_initial_state()
        self._select_initial_mode()
        self._select_initial_scenario()

    def _build_ui(self) -> None:
        self.setWindowTitle('Strategy Box')
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.top_bar = TopBar(self.runtime)
        self.body = ShellBodyWidget(self.runtime)
        outer.addWidget(self.top_bar)
        outer.addWidget(self.body, 1)

    def _connect_runtime(self) -> None:
        self.top_bar.diagnostics_requested.connect(self._show_diagnostics)
        self.top_bar.settings_requested.connect(self._show_settings)
        self.top_bar.refresh_requested.connect(self._refresh_context_views)
        self.top_bar.exit_requested.connect(self.close)
        self.body.mode_rail.mode_changed.connect(self._set_mode)
        self.body.left_panel.scenario_selected.connect(self._select_scenario)
        self.body.left_panel.path_open_requested.connect(self.runtime.platform.open_path)
        self.body.left_panel.path_copy_requested.connect(self.runtime.platform.copy_text)
        self.body.left_panel.background_process_toggled.connect(self._toggle_background_process)
        self.body.left_panel.participant_selected.connect(self._select_participant)
        self.body.left_panel.assignment_selected.connect(self._assignment_changed)
        self.body.left_panel.assignment_case_selected.connect(self._select_case)
        self.body.center_panel.run_requested.connect(self._run_selected_scenario)
        self.body.center_panel.parameters_requested.connect(lambda: self.body.open_right_drawer('parameters'))
        self.body.center_panel.artifact_open_requested.connect(self.runtime.platform.open_path)
        self.body.center_panel.case_selected.connect(self._select_case)
        self.body.center_panel.background_process_selected.connect(self._show_background_process)
        self.body.center_panel.filter_changed.connect(lambda *_: self._refresh_context_views())
        self.body.right_drawer.params_changed.connect(self._on_params_changed)
        self.runtime.scenario_coordinator.case_created.connect(self._on_case_created)
        self.runtime.scenario_coordinator.case_updated.connect(lambda *_: self._refresh_context_views())
        self.runtime.scenario_coordinator.event_appended.connect(lambda *_: self._persist_and_refresh())
        self.runtime.scenario_coordinator.artifacts_created.connect(lambda *_: self._persist_and_refresh())
        self.runtime.scenario_coordinator.log_created.connect(lambda *_: self._persist_and_refresh())
        self.runtime.scenario_coordinator.run_finished.connect(self._on_case_finished)

    def _seed_initial_state(self) -> None:
        runtime_state = self.context.session_snapshot.runtime_state if self.context.session_snapshot else None
        if runtime_state and runtime_state.last_scenario_title:
            body = f'Последний сценарий: {runtime_state.last_scenario_title}'
        elif runtime_state and runtime_state.last_operation_title:
            body = f'Последняя операция: {runtime_state.last_operation_title}'
        else:
            body = 'Выберите сценарий слева или откройте проводник. Правая панель содержит кейс, логи, артефакты, параметры и состояние узла.'
        if not self.runtime.event_store.all():
            self.runtime.event_store.add(OperationalEvent.create(
                kind='system_notice',
                status='info',
                title='Рабочая поверхность готова',
                body=body,
                actor_kind='system',
                author_id=self.context.user_id,
                author_label=self.context.account_name or 'Пользователь',
            ))
        self._refresh_context_views()

    def _select_initial_mode(self) -> None:
        mode = self.context.user_config.shell.selected_mode or ShellMode.WORKSPACE
        self._set_mode(mode)
        self.body.mode_rail.set_mode(mode)

    def _select_initial_scenario(self) -> None:
        scenario_id = self._selected_scenario_id
        if not scenario_id or not self.runtime.scenario_registry.has(scenario_id):
            scenario_id = self.runtime.scenario_registry.items[0].id if self.runtime.scenario_registry.items else None
        if scenario_id:
            self._select_scenario(scenario_id)

    def _set_mode(self, mode: str) -> None:
        self.body.left_panel.set_mode(mode)
        self.body.mode_rail.set_mode(mode)
        self.runtime.preferences.save(selected_mode=mode)

    def _select_scenario(self, scenario_id: str) -> None:
        if not self.runtime.scenario_registry.has(scenario_id):
            return
        self._selected_scenario_id = scenario_id
        scenario = self.runtime.scenario_registry.get(scenario_id)
        self.body.right_drawer.set_scenario(scenario)
        self.body.center_panel.set_scenario(scenario, self._params_summary())
        self.runtime.preferences.save(last_scenario_id=scenario_id)
        self.runtime.surface_state.update_runtime(
            active_view='scenario_chat',
            selected_object=scenario_id,
            last_scenario_id=scenario_id,
            last_scenario_title=scenario.title,
            recent_artifacts=tuple(item.path for item in self.runtime.artifact_store.all()[:12]),
        )

    def _select_case(self, case_id: str) -> None:
        if not case_id or not self.runtime.case_store.has(case_id):
            return
        self.body.right_drawer.set_selected_case(case_id)
        self.body.open_right_drawer('case')
        self.runtime.surface_state.update_runtime(
            active_view='scenario_chat',
            selected_object=case_id,
            active_job=None,
            last_case_id=case_id,
            last_case_status=self.runtime.case_store.get(case_id).status,
            recent_artifacts=tuple(item.path for item in self.runtime.artifact_store.all()[:12]),
        )

    def _selected_scenario(self):
        if not self._selected_scenario_id:
            return None
        if not self.runtime.scenario_registry.has(self._selected_scenario_id):
            return None
        return self.runtime.scenario_registry.get(self._selected_scenario_id)

    def _params_summary(self) -> str:
        try:
            params = self.body.right_drawer.collect_params()
        except Exception:
            return 'проверьте параметры'
        parts = []
        for key, value in params.items():
            if value in (None, '', False):
                continue
            parts.append(f'{key}={value}')
        return ', '.join(parts) if parts else 'параметры по умолчанию'

    def _on_params_changed(self, params: dict) -> None:
        scenario = self._selected_scenario()
        if scenario is not None:
            self.body.center_panel.set_scenario(scenario, self._params_summary())

    def _run_selected_scenario(self) -> None:
        scenario = self._selected_scenario()
        if scenario is None:
            return
        if self.runtime.scenario_coordinator.is_busy:
            QMessageBox.information(self, 'Strategy Box', 'Сначала дождитесь завершения текущего сценария.')
            return
        try:
            params = self.body.right_drawer.collect_params()
        except Exception as exc:
            self.body.open_right_drawer('parameters')
            QMessageBox.warning(self, 'Strategy Box', str(exc))
            return
        self.runtime.surface_state.update_runtime(
            active_view='scenario_chat',
            selected_object=scenario.id,
            active_job=scenario.id,
            last_scenario_id=scenario.id,
            last_scenario_title=scenario.title,
            recent_artifacts=tuple(item.path for item in self.runtime.artifact_store.all()[:12]),
        )
        case = self.runtime.scenario_coordinator.submit(scenario, params)
        self.runtime.surface_state.update_runtime(
            active_view='scenario_chat',
            selected_object=case.case_id,
            active_job=case.case_id,
            last_scenario_id=scenario.id,
            last_scenario_title=scenario.title,
            last_case_id=case.case_id,
            last_case_status=case.status,
        )
        self.body.right_drawer.set_selected_case(case.case_id)
        self.body.center_panel.set_busy(True)
        self._persist_and_refresh()

    def _on_case_created(self, case) -> None:
        if case.author_id and not self.runtime.assignment_store.by_case(case.case_id):
            self.runtime.assignment_store.add(AssignmentRecord.create(
                title=f'Проверить результат: {case.scenario_title}',
                assignee_id=case.author_id,
                author_id=case.author_id,
                description='Автоматически созданное локальное поручение по запущенному кейсу.',
                scenario_id=case.scenario_id,
                case_id=case.case_id,
            ))
        self._persist_and_refresh()

    def _on_case_finished(self, case) -> None:
        self.runtime.presence_service.register_case(case)
        self.body.center_panel.set_busy(False)
        self.runtime.surface_state.update_runtime(
            active_view='scenario_chat',
            selected_object=case.case_id,
            active_job=None,
            last_scenario_id=case.scenario_id,
            last_scenario_title=case.scenario_title,
            last_case_id=case.case_id,
            last_case_status=case.status,
            last_outputs=case.outputs,
            recent_artifacts=tuple(item.path for item in self.runtime.artifact_store.all()[:12]),
        )
        self._persist_and_refresh()

    def _toggle_background_process(self, process_id: str, enabled: bool) -> None:
        self.runtime.background_store.set_enabled(process_id, enabled)
        spec = self.runtime.background_store.spec(process_id)
        state = self.runtime.background_store.state(process_id)
        self.runtime.event_store.add(OperationalEvent.create(
            kind='background_notice',
            status='info',
            title='Фоновый процесс обновлён',
            body=f'{spec.title}: {state.status_label}',
            actor_kind='background',
            meta={'process_id': process_id},
        ))
        self._persist_and_refresh()

    def _show_background_process(self, process_id: str) -> None:
        self._set_mode(ShellMode.BACKGROUND)
        self.body.mode_rail.set_mode(ShellMode.BACKGROUND)

    def _select_participant(self, participant_id) -> None:
        self.context.user_config.chat.selected_author_id = participant_id
        self.runtime.preferences.save(selected_author_id=participant_id)
        self._refresh_context_views()

    def _assignment_changed(self, assignment_id: str) -> None:
        try:
            assignment = self.runtime.assignment_store.get(assignment_id)
        except KeyError:
            return
        self.runtime.event_store.add(OperationalEvent.create(
            kind='assignment_notice',
            status='success' if assignment.status == 'completed' else 'info',
            title='Поручение обновлено',
            body=f'{assignment.title}: {assignment.status}',
            actor_kind='system',
            author_id=assignment.author_id,
            case_id=assignment.case_id,
            scenario_id=assignment.scenario_id,
        ))
        self._persist_and_refresh()

    def _persist_and_refresh(self) -> None:
        self.runtime.history_persistence.save_from(
            case_store=self.runtime.case_store,
            event_store=self.runtime.event_store,
            artifact_store=self.runtime.artifact_store,
            log_store=self.runtime.log_store,
            assignment_store=self.runtime.assignment_store,
        )
        self._refresh_context_views()

    def _refresh_context_views(self) -> None:
        self.runtime.presence_service.mark_refreshed()
        self.top_bar.refresh_context()
        self.body.center_panel.refresh()
        self.body.right_drawer.refresh()
        self.body.left_panel.refresh()

    def _show_diagnostics(self) -> None:
        DiagnosticsDialog(build_diagnostics_text(self.context), self).exec()

    def _show_settings(self) -> None:
        SettingsDialog(self.runtime, self).exec()
        self._refresh_context_views()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.runtime.preferences.save(width=self.width(), height=self.height())
        self.runtime.history_persistence.save_from(
            case_store=self.runtime.case_store,
            event_store=self.runtime.event_store,
            artifact_store=self.runtime.artifact_store,
            log_store=self.runtime.log_store,
            assignment_store=self.runtime.assignment_store,
        )
        super().closeEvent(event)
