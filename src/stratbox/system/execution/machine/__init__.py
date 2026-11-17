"""Explicitly admitted, bounded read-only machine interface."""

from .contracts import DirectoryMaterial, MaterialResolver, ReadOnlyWireCodec, WireRequestError
from .schema import wire_schemas
from .invoke import invoke_read_only
