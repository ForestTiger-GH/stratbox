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
from app.core.user_config import save_user_config
from app.profiles.diagnostics import run_profile_diagnostics
from app.tasks.models import TaskParamSpec, TaskResult, TaskSpec
from app.tasks.registry import TaskRegistry, load_task_registry
from app.gui.workers import TaskWorker


class MainWindow(QMainWindow):
    """Минимальное главное окно приложения.

    Окно уже разделяет профиль, задачу, параметры, логи и сервисные действия.
    Предметная логика не находится в GUI: задачи запускаются через adapter-слой.
    """

    def __init__(self, context: AppContext):
        super().__init__()
        self.context = context
        self.registry: TaskRegistry = load_task_registry()
        self._param_widgets: dict[str, QWidget] = {}
        self._thread: QThread | None = None
        self._worker: TaskWorker | None = None

        self.setWindowTitle("Strategy Box")
        self._build_ui()
        self._load_profiles()
        self._load_tasks()
        self._refresh_status()
        self._render_selected_task()

    def _build_ui(self) -> None:
        """Собирает виджеты главного окна."""
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

        profile_box = QGroupBox("Profile")
        profile_layout = QVBoxLayout(profile_box)
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        profile_layout.addWidget(self.profile_combo)
        self.check_profile_button = QPushButton("Check profile")
        self.check_profile_button.clicked.connect(self._check_profile)
        profile_layout.addWidget(self.check_profile_button)
        self.profile_status = QPlainTextEdit()
        self.profile_status.setReadOnly(True)
        self.profile_status.setMaximumHeight(180)
        profile_layout.addWidget(self.profile_status)
        left_layout.addWidget(profile_box)

        task_box = QGroupBox("Tasks")
        task_layout = QVBoxLayout(task_box)
        self.task_list = QListWidget()
        self.task_list.currentItemChanged.connect(lambda *_: self._render_selected_task())
        task_layout.addWidget(self.task_list)
        left_layout.addWidget(task_box, 1)

        service_box = QGroupBox("Service")
        service_layout = QVBoxLayout(service_box)
        self.open_data_button = QPushButton("Open data folder")
        self.open_data_button.clicked.connect(lambda: self._open_path(self.context.active_profile.resolved_root))
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

        splitter.setSizes([360, 840])
        self._last_outputs: tuple[str, ...] = ()

    def _load_profiles(self) -> None:
        """Заполняет список профилей."""
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for profile in self.context.profiles.items:
            self.profile_combo.addItem(profile.title, profile.id)
        index = self.profile_combo.findData(self.context.active_profile.id)
        self.profile_combo.setCurrentIndex(max(index, 0))
        self.profile_combo.blockSignals(False)

    def _load_tasks(self) -> None:
        """Заполняет список задач."""
        self.task_list.clear()
        for spec in self.registry.enabled():
            item = QListWidgetItem(f"{spec.category} / {spec.title}")
            item.setData(1000, spec.id)
            self.task_list.addItem(item)
        if self.task_list.count():
            self.task_list.setCurrentRow(0)

    def _selected_task(self) -> TaskSpec | None:
        """Возвращает текущую задачу."""
        item = self.task_list.currentItem()
        if not item:
            return None
        return self.registry.get(str(item.data(1000)))

    def _clear_params(self) -> None:
        """Удаляет старые поля параметров."""
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._param_widgets = {}

    def _render_selected_task(self) -> None:
        """Рисует описание и параметры выбранной задачи."""
        spec = self._selected_task()
        self._clear_params()
        if spec is None:
            self.task_title.setText("No task selected")
            self.task_description.setText("")
            return

        self.task_title.setText(spec.title)
        self.task_description.setText(spec.description)
        for param in spec.params:
            widget = self._make_param_widget(param)
            self._param_widgets[param.name] = widget
            self.params_layout.addRow(param.title, widget)

    def _make_param_widget(self, param: TaskParamSpec) -> QWidget:
        """Создает виджет ввода для параметра задачи."""
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
        """Собирает параметры из формы."""
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

    def _refresh_status(self) -> None:
        """Обновляет верхнюю строку статуса версии."""
        version = self.context.version
        dirty = " dirty" if version.dirty else ""
        self.version_label.setText(
            f"Branch: {version.branch} | Commit: {version.commit_short}{dirty} | "
            f"Repo: {self.context.paths.repo_dir} | Data: {self.context.active_profile.resolved_root}"
        )

    def _on_profile_changed(self) -> None:
        """Переключает активный профиль."""
        profile_id = str(self.profile_combo.currentData())
        self.context.user_config.active_profile = profile_id
        save_user_config(self.context.paths.app_config_path, self.context.user_config)
        self.context = build_app_context(profile_id=profile_id)
        self._refresh_status()
        self._check_profile()

    def _check_profile(self) -> None:
        """Проверяет активный профиль и показывает результат."""
        report = run_profile_diagnostics(self.context.active_profile)
        lines = [report.title, f"Root: {self.context.active_profile.resolved_root}", ""]
        for item in report.items:
            mark = "OK" if item.ok else "FAIL"
            lines.append(f"{mark}: {item.title} — {item.details}")
        self.profile_status.setPlainText("\n".join(lines))

    def _run_selected_task(self) -> None:
        """Запускает выбранную задачу в фоне."""
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
        """Обрабатывает завершение фоновой задачи."""
        self.run_button.setEnabled(True)
        self._last_outputs = result.outputs
        self.open_last_output_button.setEnabled(bool(result.outputs))
        self.log_view.appendPlainText(result.message)
        self.log_view.appendPlainText(f"OK: {result.ok}")
        for output in result.outputs:
            self.log_view.appendPlainText(f"Output: {output}")
        self._thread = None
        self._worker = None

    def _open_path(self, path: str) -> None:
        """Открывает файл или папку средствами ОС."""
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
        """Открывает первый путь из последнего результата."""
        if self._last_outputs:
            self._open_path(self._last_outputs[0])
