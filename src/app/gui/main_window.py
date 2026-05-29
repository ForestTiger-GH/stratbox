
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
from app.core.handoff import (
    get_launcher_config_path_from_env,
    get_launcher_handoff_path_from_env,
    patch_launcher_config_data_root,
    patch_launcher_handoff_data_root,
)
from app.core.user_config import save_user_config
from app.tasks.models import TaskParamSpec, TaskResult, TaskSpec
from app.tasks.registry import TaskRegistry, load_task_registry
from app.workspace import build_filestore_for_data_root, resolve_data_root_status, run_workspace_diagnostics
from app.gui.workers import TaskWorker


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
        self.environment_status.setMaximumHeight(220)
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
        self.open_data_button = QPushButton("Open data root")
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

        splitter.setSizes([380, 860])
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
        if spec.requires_data_root and not self.context.data_root_status.available:
            description += "\n\nTask requires available data_root."
        self.task_description.setText(description)
        for param in spec.params:
            widget = self._make_param_widget(param)
            self._param_widgets[param.name] = widget
            self.params_layout.addRow(param.title, widget)
        self.run_button.setEnabled(not (spec.requires_data_root and not self.context.data_root_status.available))

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
        data_root_text = str(self.context.data_root_path) if self.context.data_root_path else "(not set)"
        self.version_label.setText(
            f"Mode: {self.context.run_mode} | Branch: {version.branch} | Commit: {version.commit_short}{dirty} | "
            f"Repo: {self.context.paths.repo_dir}\n"
            f"Data root: {data_root_text} | Data status: {'available' if self.context.data_root_status.available else 'unavailable'} | "
            f"Degraded: {self.context.degraded_launch}"
        )
        self.environment_label.setText(
            f"Workspace schema: {self.context.workspace_schema.title}\n"
            f"Business root: {data_root_text}"
        )
        self.open_data_button.setEnabled(self.context.data_root_status.available and self.context.data_root_path is not None)
        self._check_environment(quiet=True)

    def _check_environment(self, quiet: bool = False) -> None:
        report = run_workspace_diagnostics(self.context.workspace_schema, self.context.data_root_path)
        lines = [
            report.title,
            f"Run mode: {self.context.run_mode}",
            f"Data root status: {self.context.data_root_status.message}",
            "",
        ]
        if self.context.launcher_handoff is not None:
            lines.extend([
                f"Launcher mode: {self.context.launcher_handoff.launcher_mode}",
                f"Install profile: {self.context.launcher_handoff.install_profile}",
                f"Trusted commit: {self.context.launcher_handoff.trusted_repo_commit}",
                "",
            ])
        for item in report.items:
            mark = "OK" if item.ok else "FAIL"
            lines.append(f"{mark}: {item.title} — {item.details}")
        self.environment_status.setPlainText("\n".join(lines))
        if not quiet:
            self.log_view.appendPlainText("Environment check finished")

    def _change_data_root(self) -> None:
        if self._thread is not None:
            QMessageBox.information(self, "Strategy Box", "Finish current task before changing data root.")
            return
        initial = str(self.context.data_root_path or Path.home())
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

        config_path = get_launcher_config_path_from_env()
        handoff_path = get_launcher_handoff_path_from_env()
        if self.context.run_mode == "launcher_managed":
            if config_path is None or handoff_path is None:
                QMessageBox.warning(self, "Strategy Box", "Launcher-managed session misses handoff/config paths.")
                return
            try:
                patch_launcher_config_data_root(config_path, data_locator)
                patch_launcher_handoff_data_root(handoff_path, data_locator, selected_path, available=status.available)
            except Exception as exc:
                QMessageBox.warning(self, "Strategy Box", str(exc))
                return
            self.context = build_app_context()
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
        if self.context.data_root_path is not None:
            self._open_path(str(self.context.data_root_path))

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
