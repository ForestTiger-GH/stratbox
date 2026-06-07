"""AppDock-facing entrypoint for Strategy Box."""

from __future__ import annotations

import sys

from app.platform.appdock.entry import main


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
