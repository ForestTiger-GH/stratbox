"""Запуск GUI приложения."""

from __future__ import annotations

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

    if context.run_mode == 'appdock_managed' and context.session_client is not None:
        context.session_client.mark_running(active_view='main_window')

    try:
        app = QApplication([])
        app.setApplicationName('Strategy Box')
        try:
            stylesheet = files('app').joinpath('resources', 'styles', 'app.qss').read_text(encoding='utf-8')
            app.setStyleSheet(stylesheet)
        except Exception:
            context.logger.warning('GUI stylesheet was not loaded')
        if context.run_mode == 'appdock_managed' and context.session_client is not None:
            app.aboutToQuit.connect(lambda: context.session_client.mark_ended(clean_shutdown=True, active_view='main_window'))
        window = MainWindow(context)
        window.resize(context.user_config.window.width, context.user_config.window.height)
        window.show()
        return int(app.exec())
    except Exception:
        if context.run_mode == 'appdock_managed' and context.session_client is not None:
            context.session_client.mark_ended(clean_shutdown=False, active_view='main_window', warning='GUI startup failed')
        raise
