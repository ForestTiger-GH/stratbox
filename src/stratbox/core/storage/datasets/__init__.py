"""Content addressed canonical dataset retention and typed selection."""
from .stores import FileDatasetStore, MemoryDatasetStore

__all__ = ("FileDatasetStore", "MemoryDatasetStore")
