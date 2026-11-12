"""Portable child paths for FileStore directory commands."""

from pathlib import PureWindowsPath


def child_path(parent: str, name: str) -> str:
    if (
        not isinstance(name, str)
        or name in {"", ".", ".."}
        or "\x00" in name
        or "/" in name
        or "\\" in name
        or ":" in name
        or PureWindowsPath(name).drive
    ):
        raise ValueError("Directory entry must be a single child name")
    directory = str(parent).replace("\\", "/")
    if directory in {"", "."}:
        return name
    return f"{directory.rstrip('/')}/{name}"
