"""Restricted, explicitly admitted machine-call contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

from stratbox.core.storage.filestore import FileStore
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.data.releases import ParsedRelease
from stratbox.core.execution import ExecutionContext, OperationResult


class WireRequestError(ValueError):
    @property
    def code(self) -> str:
        return self.args[0]


@dataclass(frozen=True, slots=True)
class DirectoryMaterial:
    directory: str
    store: FileStore


class MaterialResolver(Protocol):
    """Resolve opaque references using the application-supplied authority."""

    def source(self, reference: str) -> SourcePayload: ...
    def release(self, reference: str) -> ParsedRelease: ...
    def directory(self, reference: str) -> DirectoryMaterial: ...


@dataclass(frozen=True, slots=True)
class ReadOnlyWireCodec:
    operation_id: str
    contract_version: int
    input_fields: Mapping[str, dict]
    required_fields: tuple[str, ...]
    output_fields: Mapping[str, dict]
    resolve_and_invoke: Callable[[dict, MaterialResolver, ExecutionContext | None], OperationResult]
    project: Callable[[OperationResult], dict | None]

    def __post_init__(self) -> None:
        if not set(self.required_fields) <= set(self.input_fields):
            raise ValueError("Machine codec required fields must be declared")
