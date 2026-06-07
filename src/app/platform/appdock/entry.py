"""Canonical AppDock-facing module entry for Strategy Box.

This module is the only AppDock-specific Python-module entrypoint and is intended
to be launched as ``python -m app.platform.appdock.entry``.
"""

from __future__ import annotations

import sys

from app.__main__ import main as app_main


def main(argv: list[str] | None = None) -> int:
    return app_main(argv, launch_origin='appdock')


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
