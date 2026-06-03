"""Главное окно Strategy Box."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread
from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.context import AppContext, build_app_context
from app.core.user_config import AppUserConfig, save_user_config
from app.gui.workers import ScenarioWorker
from app.scenarios.models import ScenarioParamSpec, ScenarioResult, ScenarioSpec
from app.scenarios.registry import ScenarioRegistry, load_scenario_registry
from app.workspace import resolve_data_root_status, resolve_workspace_root, run_workspace_diagnostics


class MainWindow(QMainWindow):
    """Главное окно приложения Strategy Box."""

    def __init__(self, context: AppContext):
        super().__init__()
        self.context = context
        self.registry: ScenarioRegistry = load_scenario_registry()
        self._param_widgets: dict[str, QWidget] = {}
        self._thread: QThread | None = None
        self._worker: ScenarioWorker | None = None
        self._last_outputs: tuple[str, ...] = tuple()
        self._last_scenario_log: str | None = None
        self._last_result_message: str = "No scenario has been executed yet."
        self._recent_artifacts: list[str] = []
        self._last_diagnostics_text: str = ""

        self.setWindowTitle("Strategy Box")
        self._build_ui()
        self._load_workspace_schemas()
        self._load_scenarios()
        self._restore_window_state()
        self._load_workspace_schemas()
        self._refresh_context_views()
        self._render_selected_scenario()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)

        header = QLabel("Strategy Box")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        main_layout.addWidget(header)

        self.main_splitter = QSplitter()
        main_layout.addWidget(self.main_splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.main_splitter.addWidget(left)

        env_box = QGroupBox("Node and workspace")
        env_layout = QVBoxLayout(env_box)
        self.environment_label = QLabel()
        self.environment_label.setWordWrap(True)
        env_layout.addWidget(self.environment_label)

        schema_row = QHBoxLayout()
        schema_row.addWidget(QLabel("Workspace schema"))
        self.workspace_schema_combo = QComboBox()
        self.workspace_schema_combo.currentIndexChanged.connect(self._workspace_schema_changed)
        schema_row.addWidget(self.workspace_schema_combo, 1)
        env_layout.addLayout(schema_row)

        env_buttons = QHBoxLayout()
        self.check_environment_button = QPushButton("Check diagnostics")
        self.check_environment_button.clicked.connect(self._check_environment)
        env_buttons.addWidget(self.check_environment_button)
        self.copy_diagnostics_button = QPushButton("Copy diagnostics")
        self.copy_diagnostics_button.clicked.connect(self._copy_diagnostics)
        env_buttons.addWidget(self.copy_diagnostics_button)
        self.change_selector_button = QPushButton("Change workspace selector")
        self.change_selector_button.clicked.connect(self._change_workspace_selector)
        env_buttons.addWidget(self.change_selector_button)
        env_layout.addLayout(env_buttons)

        self.environment_summary = QLabel()
        self.environment_summary.setWordWrap(True)
        env_layout.addWidget(self.environment_summary)

        self.environment_status = QPlainTextEdit()
        self.environment_status.setReadOnly(True)
        self.environment_status.setMaximumHeight(240)
        env_layout.addWidget(self.environment_status)
        left_layout.addWidget(env_box)

        scenario_box = QGroupBox("Scenarios")
        scenario_layout = QVBoxLayout(scenario_box)
        self.scenario_list = QListWidget()
        self.scenario_list.currentItemChanged.connect(lambda *_: self._render_selected_scenario())
        scenario_layout.addWidget(self.scenario_list)
        left_layout.addWidget(scenario_box, 1)

        service_box = QGroupBox("Service")
        service_layout = QVBoxLayout(service_box)
        self.open_workspace_button = QPushButton("Open workspace root")
        self.open_workspace_button.clicked.connect(self._open_workspace_root)
        service_layout.addWidget(self.open_workspace_button)
        self.open_logs_button = QPushButton("Open logs")
        self.open_logs_button.clicked.connect(lambda: self._open_path(str(self.context.paths.logs_dir)))
        service_layout.addWidget(self.open_logs_button)
        self.open_repo_button = QPushButton("Open source")
        self.open_repo_button.clicked.connect(lambda: self._open_path(str(self.context.paths.source_root)))
        service_layout.addWidget(self.open_repo_button)
        left_layout.addWidget(service_box)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.main_splitter.addWidget(right)

        overview_box = QGroupBox("Overview")
        overview_layout = QVBoxLayout(overview_box)
        self.overview_label = QLabel()
        self.overview_label.setWordWrap(True)
        overview_layout.addWidget(self.overview_label)
        right_layout.addWidget(overview_box)

        self.scenario_title = QLabel()
        self.scenario_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        right_layout.addWidget(self.scenario_title)

        self.scenario_description = QLabel()
        self.scenario_description.setWordWrap(True)
        right_layout.addWidget(self.scenario_description)

        params_box = QGroupBox("Parameters")
        self.params_layout = QFormLayout(params_box)
        right_layout.addWidget(params_box)

        buttons = QHBoxLayout()
        self.run_button = QPushButton("Run scenario")
        self.run_button.clicked.connect(self._run_selected_scenario)
        buttons.addWidget(self.run_button)
        self.open_primary_artifact_button = QPushButton("Open primary artifact")
        self.open_primary_artifact_button.clicked.connect(self._open_primary_artifact)
        self.open_primary_artifact_button.setEnabled(False)
        buttons.addWidget(self.open_primary_artifact_button)
        right_layout.addLayout(buttons)

        result_box = QGroupBox("Latest result")
        result_layout = QVBoxLayout(result_box)
        self.result_summary = QLabel()
        self.result_summary.setWordWrap(True)
        result_layout.addWidget(self.result_summary)
        right_layout.addWidget(result_box)

        artifacts_box = QGroupBox("Recent artifacts")
        artifacts_layout = QVBoxLayout(artifacts_box)
        self.artifact_list = QListWidget()
        artifacts_layout.addWidget(self.artifact_list)
        artifact_buttons = QHBoxLayout()
        self.open_artifact_button = QPushButton("Open")
        self.open_artifact_button.clicked.connect(self._open_selected_artifact)
        artifact_buttons.addWidget(self.open_artifact_button)
        self.open_artifact_folder_button = QPushButton("Open folder")
        self.open_artifact_folder_button.clicked.connect(self._open_selected_artifact_folder)
        artifact_buttons.addWidget(self.open_artifact_folder_button)
        self.copy_artifact_path_button = QPushButton("Copy path")
        self.copy_artifact_path_button.clicked.connect(self._copy_selected_artifact_path)
        artifact_buttons.addWidget(self.copy_artifact_path_button)
        artifacts_layout.addLayout(artifact_buttons)
        right_layout.addWidget(artifacts_box)

        log_box = QGroupBox("Execution log")
        log_layout = QVBoxLayout(log_box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        right_layout.addWidget(log_box, 1)

    def _load_workspace_schemas(self) -> None:
        self.workspace_schema_combo.blockSignals(True)
        self.workspace_schema_combo.clear()
        selected_index = 0
        for index, schema in enumerate(self.context.workspaces.items):
            self.workspace_schema_combo.addItem(schema.title, schema.id)
            if schema.id == self.context.workspace_schema.id:
                selected_index = index
        self.workspace_schema_combo.setCurrentIndex(selected_index)
        self.workspace_schema_combo.blockSignals(False)

    def _load_scenarios(self) -> None:
        self.scenario_list.clear()
        selected_id = self.context.user_config.last_scenario_id
        selected_index = 0
        for index, spec in enumerate(self.registry.enabled()):
            label = spec.title
            meta = f"{spec.group} · {spec.kind}"
            if spec.tags:
                meta += f" · {', '.join(spec.tags)}"
            item = QListWidgetItem(f"{label}\n{meta}")
            item.setData(1000, spec.id)
            self.scenario_list.addItem(item)
            if spec.id == selected_id:
                selected_index = index
        if self.scenario_list.count():
            self.scenario_list.setCurrentRow(selected_index)

    def _restore_window_state(self) -> None:
        self.resize(self.context.user_config.window.width, self.context.user_config.window.height)
        if self.context.user_config.splitter_sizes:
            self.main_splitter.setSizes(self.context.user_config.splitter_sizes)

    def _selected_scenario(self) -> ScenarioSpec | None:
        item = self.scenario_list.currentItem()
        if not item:
            return None
        return self.registry.get(str(item.data(1000)))

    def _clear_params(self) -> None:
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._param_widgets = {}

    def _render_selected_scenario(self) -> None:
        spec = self._selected_scenario()
        self._clear_params()
        if spec is None:
            self.scenario_title.setText("No scenario selected")
            self.scenario_description.setText("")
            self.run_button.setEnabled(False)
            return

        self.scenario_title.setText(spec.title)
        description = spec.description
        if spec.requires_workspace and not self.context.workspace_status.available:
            description += "\n\nScenario requires available workspace root."
        if spec.tags:
            description += f"\n\nTags: {', '.join(spec.tags)}"
        self.scenario_description.setText(description)
        for param in spec.params:
            widget = self._make_param_widget(param)
            self._param_widgets[param.name] = widget
            self.params_layout.addRow(param.title, widget)
        self.run_button.setEnabled(not (spec.requires_workspace and not self.context.workspace_status.available))
        self._save_user_preferences(last_scenario_id=spec.id)
        if self.context.session_client is not None:
            self.context.session_client.update_app_state(active_view='scenario_details', selected_object=spec.id, last_scenario_id=spec.id)

    def _make_param_widget(self, param: ScenarioParamSpec) -> QWidget:
        if param.type == 'bool':
            widget = QCheckBox()
            widget.setChecked(bool(param.default))
            return widget
        if param.type == 'select':
            widget = QComboBox()
            for option in param.options:
                widget.addItem(option)
            if param.default is not None:
                index = widget.findText(str(param.default))
                if index >= 0:
                    widget.setCurrentIndex(index)
            return widget
        line = QLineEdit()
        if param.default is not None:
            if isinstance(param.default, (list, tuple)):
                line.setText(', '.join(str(x) for x in param.default))
            else:
                line.setText(str(param.default))
        return line

    def _collect_params(self) -> dict[str, Any]:
        spec = self._selected_scenario()
        if spec is None:
            return {}
        out: dict[str, Any] = {}
        by_name = {param.name: param for param in spec.params}
        for name, widget in self._param_widgets.items():
            param = by_name[name]
            if isinstance(widget, QCheckBox):
                out[name] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                out[name] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                text = widget.text()
                if param.type == 'int':
                    out[name] = int(text) if text.strip() else None
                elif param.type == 'float':
                    out[name] = float(text) if text.strip() else None
                elif param.type == 'multiselect':
                    out[name] = [x.strip() for x in text.split(',') if x.strip()]
                else:
                    out[name] = text
        return out

    def _refresh_context_views(self) -> None:
        version = self.context.version
        dirty = ' dirty' if version.dirty else ''
        selector_text = str(self.context.data_root_selector_path) if self.context.data_root_selector_path else '(not set)'
        workspace_text = str(self.context.workspace_root_path) if self.context.workspace_root_path else '(not resolved)'
        world_text = self.context.appdock_handoff.world_id if self.context.appdock_handoff else '(standalone)'
        active_surface = self.context.appdock_handoff.active_app_surface if self.context.appdock_handoff else 'standalone'
        revision = version.commit_short if self.context.appdock_handoff is None else (self.context.appdock_handoff.source_revision.commit or version.commit_short)
        self.overview_label.setText(
            '\n'.join([
                f'World / App surface: {world_text} / {active_surface}',
                f'Source revision: {revision}{dirty} ({version.branch})',
                f'Node / Session: {self.context.node_id or "(unknown)"} / {self.context.session_id or "(unknown)"}',
                f'Attach mode / Launch origin: {self.context.appdock_handoff.attach_mode if self.context.appdock_handoff else self.context.run_mode} / {self.context.launch_origin}',
                f'Workspace schema: {self.context.workspace_schema.title}',
                f'Selector / Workspace root: {selector_text} / {workspace_text}',
            ])
        )
        summary_lines = [
            f'Selected root: {selector_text}',
            f'Workspace root: {workspace_text}',
            f'Schema: {self.context.workspace_schema.title}',
            f'Status: {"available" if self.context.workspace_status.available else "unavailable"}',
        ]
        if self.context.health_snapshot is not None:
            summary_lines.append(f'Node health: {self.context.health_snapshot.overall_status}')
        if self.context.degraded_launch:
            summary_lines.append('Launch mode: degraded')
        self.environment_label.setText('\n'.join(summary_lines))
        self.open_workspace_button.setEnabled(self.context.workspace_status.available and self.context.workspace_root_path is not None)
        self._refresh_latest_result_view()
        self._refresh_recent_artifacts_view()
        self._check_environment(quiet=True)
        if self.context.session_client is not None:
            self.context.session_client.update_app_state(
                active_view='overview',
                workspace_schema_id=self.context.workspace_schema.id,
                effective_workspace_root=(str(self.context.workspace_root_path) if self.context.workspace_root_path else None),
                selected_data_root_path=(str(self.context.data_root_selector_path) if self.context.data_root_selector_path else None),
                recent_artifacts=tuple(self._recent_artifacts),
                workspace_state={
                    'selected_data_root_path': (str(self.context.data_root_selector_path) if self.context.data_root_selector_path else None),
                    'workspace_root_path': (str(self.context.workspace_root_path) if self.context.workspace_root_path else None),
                },
            )

    def _refresh_latest_result_view(self) -> None:
        primary_output = self._last_outputs[0] if self._last_outputs else '(no artifacts yet)'
        lines = [
            self._last_result_message,
            f'Primary artifact: {primary_output}',
            f'Scenario log: {self._last_scenario_log or "(not available)"}',
        ]
        self.result_summary.setText('\n'.join(lines))
        self.open_primary_artifact_button.setEnabled(bool(self._last_outputs))

    def _refresh_recent_artifacts_view(self) -> None:
        self.artifact_list.clear()
        for artifact in self._recent_artifacts:
            self.artifact_list.addItem(artifact)
        self.open_artifact_button.setEnabled(bool(self._recent_artifacts))
        self.open_artifact_folder_button.setEnabled(bool(self._recent_artifacts))
        self.copy_artifact_path_button.setEnabled(bool(self._recent_artifacts))

    def _build_diagnostics_text(self) -> str:
        resolution = resolve_workspace_root(self.context.workspace_schema, self.context.data_root_selector_path, run_mode=self.context.run_mode, create_missing=False)
        report = run_workspace_diagnostics(self.context.workspace_schema, resolution, create_missing=False)
        selector_text = str(self.context.data_root_selector_path) if self.context.data_root_selector_path else '(not set)'
        workspace_text = str(self.context.workspace_root_path) if self.context.workspace_root_path else '(not resolved)'
        lines = [
            report.title,
            f'Attach mode: {self.context.appdock_handoff.attach_mode if self.context.appdock_handoff else self.context.run_mode}',
            f'Launch origin: {self.context.launch_origin}',
            f'Node ID: {self.context.node_id or "(unknown)"}',
            f'Session ID: {self.context.session_id or "(unknown)"}',
            f'User / Host: {(self.context.account_name or "(unknown)")} / {(self.context.host_name or "(unknown)")}',
            f'Workspace schema: {self.context.workspace_schema.id}',
            f'Selector: {selector_text}',
            f'Selector status: {self.context.data_root_status.message}',
            f'Workspace root: {workspace_text}',
            f'Workspace status: {self.context.workspace_status.message}',
            '',
        ]
        if self.context.appdock_handoff is not None:
            lines.extend([
                f'World: {self.context.appdock_handoff.world_id}',
                f'Active app surface: {self.context.appdock_handoff.active_app_surface}',
                f'Bundle profile: {self.context.appdock_handoff.bundle_profile}',
                f'Source revision: {self.context.appdock_handoff.source_revision.commit}',
                f'Source sync mode: {self.context.appdock_handoff.source_revision.sync_mode}',
                '',
            ])
        for item in report.items:
            mark = 'OK' if item.ok else 'FAIL'
            lines.append(f'{mark}: {item.title} — {item.details} [{item.severity}]')
        return '\n'.join(lines)

    def _check_environment(self, quiet: bool = False) -> None:
        self._last_diagnostics_text = self._build_diagnostics_text()
        self.environment_status.setPlainText(self._last_diagnostics_text)
        if not quiet:
            self.log_view.appendPlainText('Diagnostics refreshed')
        if self.context.session_client is not None:
            self.context.session_client.update_app_state(active_view='diagnostics')

    def _copy_diagnostics(self) -> None:
        if not self._last_diagnostics_text:
            self._check_environment(quiet=True)
        QGuiApplication.clipboard().setText(self._last_diagnostics_text)
        self.log_view.appendPlainText('Diagnostics copied to clipboard')

    def _workspace_schema_changed(self) -> None:
        schema_id = str(self.workspace_schema_combo.currentData())
        if not schema_id or schema_id == self.context.workspace_schema.id:
            return
        self._save_user_preferences(last_workspace_schema=schema_id)
        self.context = build_app_context(
            standalone_dev_root=(str(self.context.data_root_selector_path) if self.context.run_mode == 'standalone_dev' and self.context.data_root_selector_path else None),
            override_data_root_path=self.context.data_root_selector_path,
            launch_origin=self.context.launch_origin,
        )
        self._load_workspace_schemas()
        self._refresh_context_views()
        self.log_view.appendPlainText(f'Workspace schema changed to: {self.context.workspace_schema.title}')

    def _change_workspace_selector(self) -> None:
        if self._thread is not None:
            QMessageBox.information(self, 'Strategy Box', 'Finish current scenario before changing workspace selector.')
            return
        initial = str(self.context.data_root_selector_path or self.context.workspace_root_path or Path.home())
        selected = QFileDialog.getExistingDirectory(self, 'Select workspace selector', initial)
        if not selected:
            return
        selected_path = Path(selected).expanduser()
        status = resolve_data_root_status(selected_path)
        data_locator = {'kind': 'local_path', 'value': str(selected_path), 'display_name': str(selected_path)}
        if self.context.run_mode == 'appdock_managed':
            if self.context.session_client is None:
                QMessageBox.warning(self, 'Strategy Box', 'AppDock-managed session misses session client.')
                return
            try:
                self.context.session_client.update_workspace_selector(data_locator=data_locator, selector_path=selected_path, data_root_status=status)
                self.context = build_app_context(launch_origin=self.context.launch_origin)
            except Exception as exc:
                QMessageBox.warning(self, 'Strategy Box', str(exc))
                return
        else:
            self.context = build_app_context(standalone_dev_root=str(selected_path), override_data_root_path=selected_path, launch_origin=self.context.launch_origin)
        self._refresh_context_views()
        self._render_selected_scenario()
        self.log_view.appendPlainText(f'Workspace selector changed to: {selected_path}')

    def _run_selected_scenario(self) -> None:
        spec = self._selected_scenario()
        if spec is None:
            return
        params = self._collect_params()
        self.run_button.setEnabled(False)
        self.log_view.appendPlainText(f'Starting scenario: {spec.title}')
        if self.context.session_client is not None:
            self.context.session_client.update_app_state(
                active_view='scenario_running',
                selected_object=spec.id,
                active_job=spec.id,
                last_scenario_id=spec.id,
                last_scenario_title=spec.title,
                workspace_schema_id=self.context.workspace_schema.id,
                effective_workspace_root=(str(self.context.workspace_root_path) if self.context.workspace_root_path else None),
                selected_data_root_path=(str(self.context.data_root_selector_path) if self.context.data_root_selector_path else None),
                workspace_state={
                    'selected_data_root_path': (str(self.context.data_root_selector_path) if self.context.data_root_selector_path else None),
                    'workspace_root_path': (str(self.context.workspace_root_path) if self.context.workspace_root_path else None),
                },
            )
        self._thread = QThread(self)
        self._worker = ScenarioWorker(spec=spec, context=self.context, params=params)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_scenario_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_scenario_finished(self, result: ScenarioResult) -> None:
        self.run_button.setEnabled(True)
        self._last_outputs = result.outputs
        self._last_scenario_log = next((item for item in result.outputs if item.endswith('.log')), result.details.get('scenario_log') if isinstance(result.details, dict) else None)
        self._last_result_message = result.message + f'\nOK: {result.ok}'
        for output in result.outputs:
            if output not in self._recent_artifacts:
                self._recent_artifacts.insert(0, output)
        self._recent_artifacts = self._recent_artifacts[:10]
        self._refresh_latest_result_view()
        self._refresh_recent_artifacts_view()
        self.log_view.appendPlainText(result.message)
        self.log_view.appendPlainText(f'OK: {result.ok}')
        for output in result.outputs:
            self.log_view.appendPlainText(f'Output: {output}')
        spec = self._selected_scenario()
        if self.context.session_client is not None:
            self.context.session_client.update_app_state(
                active_view='result',
                active_job=None,
                last_scenario_id=(spec.id if spec else None),
                last_scenario_title=(spec.title if spec else None),
                last_scenario_ok=result.ok,
                last_outputs=result.outputs,
                last_scenario_log=self._last_scenario_log,
                recent_artifacts=tuple(self._recent_artifacts),
                workspace_schema_id=self.context.workspace_schema.id,
                effective_workspace_root=(str(self.context.workspace_root_path) if self.context.workspace_root_path else None),
                selected_data_root_path=(str(self.context.data_root_selector_path) if self.context.data_root_selector_path else None),
                workspace_state={
                    'selected_data_root_path': (str(self.context.data_root_selector_path) if self.context.data_root_selector_path else None),
                    'workspace_root_path': (str(self.context.workspace_root_path) if self.context.workspace_root_path else None),
                },
            )
        self._thread = None
        self._worker = None
        self._render_selected_scenario()

    def _open_workspace_root(self) -> None:
        if self.context.workspace_root_path is not None:
            self._open_path(str(self.context.workspace_root_path))

    def _selected_artifact(self) -> str | None:
        item = self.artifact_list.currentItem()
        if item is None:
            return self._recent_artifacts[0] if self._recent_artifacts else None
        return item.text()

    def _open_path(self, path: str) -> None:
        try:
            p = Path(path)
            target = p if p.is_dir() else p.parent
            if os.name == 'nt':
                os.startfile(str(target if target.exists() else p))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(['xdg-open', str(target if target.exists() else p)])
        except Exception as exc:
            QMessageBox.warning(self, 'Open path failed', str(exc))

    def _open_primary_artifact(self) -> None:
        if self._last_outputs:
            self._open_path(self._last_outputs[0])

    def _open_selected_artifact(self) -> None:
        artifact = self._selected_artifact()
        if artifact:
            self._open_path(artifact)

    def _open_selected_artifact_folder(self) -> None:
        artifact = self._selected_artifact()
        if artifact:
            self._open_path(str(Path(artifact).parent))

    def _copy_selected_artifact_path(self) -> None:
        artifact = self._selected_artifact()
        if artifact:
            QGuiApplication.clipboard().setText(artifact)
            self.log_view.appendPlainText(f'Artifact path copied: {artifact}')

    def _save_user_preferences(self, **kwargs: Any) -> None:
        config = AppUserConfig(
            last_workspace_schema=kwargs.get('last_workspace_schema', self.context.user_config.last_workspace_schema),
            last_scenario_id=kwargs.get('last_scenario_id', self.context.user_config.last_scenario_id),
            splitter_sizes=kwargs.get('splitter_sizes', self.context.user_config.splitter_sizes),
            environment_panel_expanded=kwargs.get('environment_panel_expanded', self.context.user_config.environment_panel_expanded),
            window=self.context.user_config.window,
        )
        save_user_config(self.context.paths.app_config_path, config)
        self.context.user_config = config

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_user_preferences(
            splitter_sizes=self.main_splitter.sizes(),
            last_scenario_id=(self._selected_scenario().id if self._selected_scenario() else self.context.user_config.last_scenario_id),
        )
        self.context.user_config.window.width = self.width()
        self.context.user_config.window.height = self.height()
        save_user_config(self.context.paths.app_config_path, self.context.user_config)
        if self.context.session_client is not None:
            self.context.session_client.update_app_state(
                active_view='closed',
                clean_shutdown=True,
                workspace_schema_id=self.context.workspace_schema.id,
                effective_workspace_root=(str(self.context.workspace_root_path) if self.context.workspace_root_path else None),
                selected_data_root_path=(str(self.context.data_root_selector_path) if self.context.data_root_selector_path else None),
                recent_artifacts=tuple(self._recent_artifacts),
            )
        super().closeEvent(event)
