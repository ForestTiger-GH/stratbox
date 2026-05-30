"""Запуск GUI приложения."""

from __future__ import annotations

import os

from app.core.context import AppContext


def run_gui(context: AppContext) -> int:
    """Запускает Qt-интерфейс приложения."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        context.logger.error('PySide6 is not installed. Install app extra: pip install -e .[app]')
        print('ERROR: PySide6 is not installed. Install app extra: pip install -e .[app]')
        return 1

    from importlib.resources import files

    from app.gui.main_window import MainWindow

    if context.run_mode == 'launcher_managed' and context.session_env is not None:
        context.session_env.mark_running(app_pid=os.getpid())
        context = build_runtime_context_after_session_mark(context)

    try:
        app = QApplication([])
        app.setApplicationName('Strategy Box')
        try:
            stylesheet = files('app').joinpath('resources', 'styles', 'app.qss').read_text(encoding='utf-8')
            app.setStyleSheet(stylesheet)
        except Exception:
            context.logger.warning('GUI stylesheet was not loaded')
        if context.run_mode == 'launcher_managed' and context.session_env is not None:
            app.aboutToQuit.connect(lambda: context.session_env.mark_ended(status='app_closed'))
        window = MainWindow(context)
        window.resize(context.user_config.window.width, context.user_config.window.height)
        window.show()
        return int(app.exec())
    except Exception:
        if context.run_mode == 'launcher_managed' and context.session_env is not None:
            context.session_env.mark_ended(status='app_failed', failure_message='GUI startup failed')
        raise


def build_runtime_context_after_session_mark(context: AppContext) -> AppContext:
    """Пересобирает контекст после перевода launcher-managed session в running."""
    from app.core.context import build_app_context

    return build_app_context()
