from __future__ import annotations

from importlib.resources import files

from app.runtime.bootstrap import build_runtime
from app.runtime.context import AppContext


def run_gui(context: AppContext) -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        context.logger.error('PySide6 is not installed. Install app extra: pip install -e .[app]')
        print('ERROR: PySide6 is not installed. Install app extra: pip install -e .[app]')
        return 1

    from app.presentation.desktop.shell.main_window import MainWindow

    runtime = build_runtime(context)

    app = QApplication([])
    app.setApplicationName('Strategy Box')
    try:
        stylesheet = files('app').joinpath('resources', 'styles', 'app.qss').read_text(encoding='utf-8')
        app.setStyleSheet(stylesheet)
    except Exception:
        context.logger.warning('GUI stylesheet was not loaded')

    try:
        window = MainWindow(runtime)
        prefs = runtime.preferences.current()
        window.resize(prefs.width, prefs.height)
        app.aboutToQuit.connect(lambda: runtime.surface_state.mark_closed(clean_shutdown=True))
        window.show()
        runtime.surface_state.mark_running()
    except Exception:
        context.logger.exception('Strategy Box GUI startup failed')
        runtime.surface_state.mark_closed(clean_shutdown=False)
        raise
    return int(app.exec())
