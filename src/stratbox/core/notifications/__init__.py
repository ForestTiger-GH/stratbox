"""Journal-first notification intent state and channel handoff contracts."""
from .state import MemoryNotificationState, FileNotificationState

__all__ = ("MemoryNotificationState", "FileNotificationState")
