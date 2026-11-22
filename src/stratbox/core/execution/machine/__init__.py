"""Explicitly admitted, bounded read-only machine interface."""

from stratbox.core.execution.machine.contracts import DirectoryMaterial, MaterialResolver, ReadOnlyWireCodec, ReadOnlyWireContract, WireRequestError
from stratbox.core.execution.machine.schema import wire_schemas
from stratbox.core.execution.machine.invoke import invoke_read_only
