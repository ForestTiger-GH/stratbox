"""Official source inventory, independent raw acquisition, and index comparison."""

from .catalog import get_rosstat_source, list_rosstat_sources
from .discovery.selection import compare_publication_indices, select_assets
