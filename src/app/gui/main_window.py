"""Главное окно Strategy Box."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread
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
from app.gui.workers import TaskWorker
from app.tasks.models import TaskParamSpec, TaskResult, TaskSpec
from app.tasks.registry import TaskRegistry, load_task_registry
from app.workspace import resolve_data_root_status, resolve_workspace_root, run_workspace_diagnostics


class MainWindow(QMainWindow):
    """Главное окно приложения Strategy Box."""

    def __init__(self, context: AppContext):
        super().__init__()
        self.context = context
        self.registry: TaskRegistry = load_task_registry()
        self._param_widgets: dict[str, QWidget] = {}
        self._thread: QThread | None = None
        self._worker: TaskWorker | None = None

        self.setWindowTitle("Strategy Box")
        self._build_ui()
        self._load_tasks()
        self._refresh_context_views()
        self._render_selected_task()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)

        header = QLabel("Strategy Box")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        main_layout.addWidget(header)

        splitter = QSplitter()
        main_layout.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        splitter.addWidget(left)

        env_box = QGroupBox("Environment")
        env_layout = QVBoxLayout(env_box)
        self.environment_label = QLabel()
        self.environment_label.setWordWrap(True)
        env_layout.addWidget(self.environment_label)

        env_buttons = QHBoxLayout()
        self.check_environment_button = QPushButton("Check environment")
        self.check_environment_button.clicked.connect(self._check_environment)
        env_buttons.addWidget(self.check_environment_button)
        self.change_data_root_button = QPushButton("Change data root")
        self.change_data_root_button.clicked.connect(self._change_data_root)
        env_buttons.addWidget(self.change_data_root_button)
        env_layout.addLayout(env_buttons)

        self.environment_status = QPlainTextEdit()
        self.environment_status.setReadOnly(True)
        self.environment_status.setMaximumHeight(260)
        env_layout.addWidget(self.environment_status)
        left_layout.addWidget(env_box)

        task_box = QGroupBox("Tasks")
        task_layout = QVBoxLayout(task_box)
        self.task_list = QListWidget()
        self.task_list.currentItemChanged.connect(lambda *_: self._render_selected_task())
        task_layout.addWidget(self.task_list)
        left_layout.addWidget(task_box, 1)

        service_box = QGroupBox("Service")
        service_layout = QVBoxLayout(service_box)
        self.open_data_button = QPushButton("Open workspace root")
        self.open_data_button.clicked.connect(self._open_data_root)
        service_layout.addWidget(self.open_data_button)
        self.open_logs_button = QPushButton("Open logs")
        self.open_logs_button.clicked.connect(lambda: self._open_path(str(self.context.paths.logs_dir)))
        service_layout.addWidget(self.open_logs_button)
        self.open_repo_button = QPushButton("Open repo")
        self.open_repo_button.clicked.connect(lambda: self._open_path(str(self.context.paths.repo_dir)))
        service_layout.addWidget(self.open_repo_button)
        left_layout.addWidget(service_box)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        splitter.addWidget(right)

        self.version_label = QLabel()
        self.version_label.setWordWrap(True)
        right_layout.addWidget(self.version_label)

        self.task_title = QLabel()
        self.task_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        right_layout.addWidget(self.task_title)

        self.task_description = QLabel()
        self.task_description.setWordWrap(True)
        right_layout.addWidget(self.task_description)

        params_box = QGroupBox("Parameters")
        self.params_layout = QFormLayout(params_box)
        right_layout.addWidget(params_box)

        buttons = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self._run_selected_task)
        buttons.addWidget(self.run_button)
        self.open_last_output_button = QPushButton("Open last output")
        self.open_last_output_button.clicked.connect(self._open_last_output)
        self.open_last_output_button.setEnabled(False)
        buttons.addWidget(self.open_last_output_button)
        right_layout.addLayout(buttons)

        log_box = QGroupBox("Execution log")
        log_layout = QVBoxLayout(log_box)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        right_layout.addWidget(log_box, 1)

        splitter.setSizes([420, 900])
        self._last_outputs: tuple[str, ...] = ()

    def _load_tasks(self) -> None:
        self.task_list.clear()
        for spec in self.registry.enabled():
            item = QListWidgetItem(f"{spec.category} / {spec.title}")
            item.setData(1000, spec.id)
            self.task_list.addItem(item)
        if self.task_list.count():
            self.task_list.setCurrentRow(0)

    def _selected_task(self) -> TaskSpec | None:
        item = self.task_list.currentItem()
        if not item:
            return None
        return self.registry.get(str(item.data(1000)))

    def _clear_params(self) -> None:
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._param_widgets = {}

    def _render_selected_task(self) -> None:
        spec = self._selected_task()
        self._clear_params()
        if spec is None:
            self.task_title.setText("No task selected")
            self.task_description.setText("")
            self.run_button.setEnabled(False)
            return

        self.task_title.setText(spec.title)
        description = spec.description
        if spec.requires_data_root and not self.context.workspace_status.available:
            description += "\n\nTask requires available workspace root."
        self.task_description.setText(description)
        for param in spec.params:
            widget = self._make_param_widget(param)
            self._param_widgets[param.name] = widget
            self.params_layout.addRow(param.title, widget)
        self.run_button.setEnabled(not (spec.requires_data_root and not self.context.workspace_status.available))

    def _make_param_widget(self, param: TaskParamSpec) -> QWidget:
        if param.type == "bool":
            widget = QCheckBox()
            widget.setChecked(bool(param.default))
            return widget
        if param.type == "select":
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
                line.setText(", ".join(str(x) for x in param.default))
            else:
                line.setText(str(param.default))
        return line

    def _collect_params(self) -> dict[str, Any]:
        spec = self._selected_task()
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
                if param.type == "int":
                    out[name] = int(text) if text.strip() else None
                elif param.type == "float":
                    out[name] = float(text) if text.strip() else None
                elif param.type == "multiselect":
                    out[name] = [x.strip() for x in text.split(",") if x.strip()]
                else:
                    out[name] = text
        return out

    def _refresh_context_views(self) -> None:
        version = self.context.version
        dirty = " dirty" if version.dirty else ""
        selector_text = str(self.context.data_root_selector_path) if self.context.data_root_selector_path else "(not set)"
        data_root_text = str(self.context.workspace_root_path or self.context.data_root_path) if (self.context.workspace_root_path or self.context.data_root_path) else "(not set)"
        version_lines = [
            f"Run mode: {self.context.run_mode}",
            f"Branch / Commit: {version.branch} / {version.commit_short}{dirty}",
            f"Repo: {self.context.paths.repo_dir}",
        ]
        if self.context.appdock_handoff is not None:
            version_lines.extend([
                f"Connector / App target: {self.context.appdock_handoff.connector_id} / {self.context.appdock_handoff.active_app_target}",
                f"Bundle / Profile: {self.context.appdock_handoff.bundle_id} / {(self.context.appdock_handoff.bundle_profile or '(none)')}",
                f"Attach mode: {self.context.appdock_handoff.attach_mode}",
                f"Deployment profile: {self.context.appdock_handoff.deployment_profile}",
                f"Target revision: {self.context.appdock_handoff.target_revision.commit}",
                f"Target sync mode: {self.context.appdock_handoff.target_revision.sync_mode}",
            ])
        version_lines.extend([
            f"Node ID: {self.context.node_id or '(unknown)'}",
            f"Node created: {self.context.node_created_at_utc or '(unknown)'}",
            f"Session ID: {self.context.session_id or '(unknown)'}",
            f"Session started: {self.context.session_started_at_utc or '(unknown)'}",
            f"Account / Host: {(self.context.account_name or '(unknown)')} / {(self.context.host_name or '(unknown)')}",
            f"Data root selector: {selector_text}",
            f"Selector status: {'available' if self.context.data_root_status.available else 'unavailable'}",
            f"Workspace root: {data_root_text}",
            f"Workspace status: {'available' if self.context.workspace_status.available else 'unavailable'}",
            f"Degraded launch: {self.context.degraded_launch}",
        ])
        self.version_label.setText("\n".join(version_lines))
        env_lines = [
            f"Workspace schema: {self.context.workspace_schema.title}",
            f"Data root selector: {selector_text}",
            f"Workspace root: {data_root_text}",
        ]
        if self.context.health_snapshot is not None:
            env_lines.extend([
                f"Environment overall: {self.context.health_snapshot.overall_status}",
                f"Install: {self.context.health_snapshot.install_status} | Target: {self.context.health_snapshot.target_status}",
                f"Runtime: {self.context.health_snapshot.runtime_status} | Venv: {self.context.health_snapshot.venv_status}",
                f"Data: {self.context.health_snapshot.data_status}",
            ])
        self.environment_label.setText("\n".join(env_lines))
        self.open_data_button.setEnabled(self.context.workspace_status.available and self.context.workspace_root_path is not None)
        self._check_environment(quiet=True)

    def _check_environment(self, quiet: bool = False) -> None:
        resolution = resolve_workspace_root(self.context.workspace_schema, self.context.data_root_selector_path, run_mode=self.context.run_mode, create_missing=False)
        report = run_workspace_diagnostics(self.context.workspace_schema, resolution, create_missing=False)
        lines = [
            report.title,
            f"Run mode: {self.context.run_mode}",
            f"Node ID: {self.context.node_id or '(unknown)'}",
            f"Session ID: {self.context.session_id or '(unknown)'}",
            f"User / Host: {(self.context.account_name or '(unknown)')} / {(self.context.host_name or '(unknown)')}",
            f"Data root selector status: {self.context.data_root_status.message}",
            f"Workspace status: {self.context.workspace_status.message}",
            "",
        ]
        if self.context.appdock_handoff is not None:
            lines.extend([
                f"Attach mode: {self.context.appdock_handoff.attach_mode}",
                f"Deployment profile: {self.context.appdock_handoff.deployment_profile}",
                f"Target revision: {self.context.appdock_handoff.target_revision.commit}",
                f"Target sync mode: {self.context.appdock_handoff.target_revision.sync_mode}",
                "",
            ])
        if self.context.user_state is not None:
            lines.extend([
                "User state:",
                f"  Preferred data locator: {self.context.user_state.preferred_data_locator}",
                f"  Last selected selector: {self.context.user_state.last_effective_data_root_path}",
                f"  Last session: {self.context.user_state.last_session_id}",
                "",
            ])
        if self.context.session_state is not None:
            lines.extend([
                "Session state:",
                f"  Status: {self.context.session_state.status}",
                f"  Lifecycle: {self.context.session_state.lifecycle_state}",
                f"  Started: {self.context.session_state.started_at_utc}",
                f"  Ended: {self.context.session_state.ended_at_utc}",
                f"  Effective selector: {self.context.session_state.effective_data_root_path}",
                f"  Failure: {self.context.session_state.failure_message}",
                "",
            ])
        if self.context.active_session is not None:
            lines.extend([
                "Active session projection:",
                f"  Lifecycle: {self.context.active_session.lifecycle_state}",
                f"  App PID: {self.context.active_session.app_pid}",
                f"  Effective selector: {self.context.active_session.effective_data_root_path}",
                "",
            ])
        if self.context.health_snapshot is not None:
            lines.extend([
                "Node health snapshot:",
                f"  Overall: {self.context.health_snapshot.overall_status}",
                f"  Install: {self.context.health_snapshot.install_status} — {self.context.health_snapshot.install_message}",
                f"  Target: {self.context.health_snapshot.target_status} — {self.context.health_snapshot.target_message}",
                f"  Runtime: {self.context.health_snapshot.runtime_status} — {self.context.health_snapshot.runtime_message}",
                f"  Venv: {self.context.health_snapshot.venv_status} — {self.context.health_snapshot.venv_message}",
                f"  Data: {self.context.health_snapshot.data_status} — {self.context.health_snapshot.data_message}",
                "",
            ])
        for item in report.items:
            mark = "OK" if item.ok else "FAIL"
            lines.append(f"{mark}: {item.title} — {item.details} [{item.severity}]")
        self.environment_status.setPlainText("\n".join(lines))
        if not quiet:
            self.log_view.appendPlainText("Environment check finished")

    def _change_data_root(self) -> None:
        if self._thread is not None:
            QMessageBox.information(self, "Strategy Box", "Finish current task before changing data root.")
            return
        initial = str(self.context.data_root_selector_path or self.context.workspace_root_path or Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Select data root", initial)
        if not selected:
            return

        selected_path = Path(selected).expanduser()
        status = resolve_data_root_status(selected_path)
        data_locator = {
            "kind": "local_path",
            "value": str(selected_path),
            "display_name": str(selected_path),
        }

        if self.context.run_mode == "appdock_managed":
            if self.context.session_client is None:
                QMessageBox.warning(self, "Strategy Box", "AppDock-managed session misses session state client.")
                return
            try:
                self.context.session_client.update_data_root(
                    data_locator=data_locator,
                    data_root_path=selected_path,
                    data_root_status=status,
                )
                self.context = build_app_context()
            except Exception as exc:
                QMessageBox.warning(self, "Strategy Box", str(exc))
                return
        else:
            self.context = build_app_context(standalone_dev_root=str(selected_path), override_data_root_path=selected_path)

        self._refresh_context_views()
        self._render_selected_task()
        self.log_view.appendPlainText(f"Data root changed to: {selected_path}")

    def _run_selected_task(self) -> None:
        spec = self._selected_task()
        if spec is None:
            return
        params = self._collect_params()
        self.run_button.setEnabled(False)
        self.log_view.appendPlainText(f"Starting task: {spec.title}")

        self._thread = QThread(self)
        self._worker = TaskWorker(spec=spec, context=self.context, params=params)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_task_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_task_finished(self, result: TaskResult) -> None:
        self.run_button.setEnabled(True)
        self._last_outputs = result.outputs
        self.open_last_output_button.setEnabled(bool(result.outputs))
        self.log_view.appendPlainText(result.message)
        self.log_view.appendPlainText(f"OK: {result.ok}")
        for output in result.outputs:
            self.log_view.appendPlainText(f"Output: {output}")
        self._thread = None
        self._worker = None
        self._render_selected_task()

    def _open_data_root(self) -> None:
        if self.context.workspace_root_path is not None:
            self._open_path(str(self.context.workspace_root_path))

    def _open_path(self, path: str) -> None:
        try:
            p = Path(path)
            target = p if p.is_dir() else p.parent
            if os.name == "nt":
                os.startfile(str(target))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(target)])
        except Exception as exc:
            QMessageBox.warning(self, "Open path failed", str(exc))

    def _open_last_output(self) -> None:
        if self._last_outputs:
            self._open_path(self._last_outputs[0])
