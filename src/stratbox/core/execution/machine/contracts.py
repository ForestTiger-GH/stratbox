"""Restricted, explicitly admitted machine-call contracts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable, Mapping, Protocol

from stratbox.core.storage.filestore import FileStore
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.data.releases import ParsedRelease
from stratbox.core.execution import ExecutionContext, OperationResult
from stratbox.shared.identifiers import safe_token


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


@dataclass(frozen=True, slots=True, init=False)
class ReadOnlyWireContract:
    """Immutable schemas that can be inspected without importing a codec."""

    operation_id: str
    required_fields: tuple[str, ...]
    _input_json: str
    _output_json: str

    def __init__(
        self,
        operation_id: str,
        input_fields: Mapping[str, dict],
        required_fields: tuple[str, ...],
        output_fields: Mapping[str, dict],
    ):
        safe_token(operation_id)
        if not isinstance(input_fields, Mapping) or not isinstance(
            output_fields, Mapping
        ):
            raise ValueError("Invalid machine fields")
        if (
            not isinstance(required_fields, tuple)
            or any(not isinstance(name, str) for name in required_fields)
            or len(set(required_fields)) != len(required_fields)
            or not set(required_fields) <= set(input_fields)
        ):
            raise ValueError("Machine codec required fields must be declared")
        for name, fields in (
            ("_input_json", input_fields),
            ("_output_json", output_fields),
        ):
            if not isinstance(fields, Mapping) or any(
                not isinstance(key, str) or not isinstance(value, dict)
                for key, value in fields.items()
            ):
                raise ValueError("Invalid machine fields")
            encoded = json.dumps(
                dict(fields), sort_keys=True, allow_nan=False, separators=(",", ":")
            )
            if len(encoded.encode("utf-8")) > 65_536:
                raise ValueError("Machine schema size limit")
            object.__setattr__(self, name, encoded)
        object.__setattr__(self, "operation_id", operation_id)
        object.__setattr__(self, "required_fields", required_fields)

    @property
    def input_fields(self) -> dict:
        return json.loads(self._input_json)

    @property
    def output_fields(self) -> dict:
        return json.loads(self._output_json)


@dataclass(frozen=True, slots=True)
class ReadOnlyWireCodec:
    contract: ReadOnlyWireContract
    resolve_and_invoke: Callable[
        [dict, MaterialResolver, ExecutionContext | None], OperationResult
    ]
    project: Callable[[OperationResult], dict | None]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.contract, ReadOnlyWireContract)
            or not callable(self.resolve_and_invoke)
            or not callable(self.project)
        ):
            raise ValueError("Invalid machine codec")

    @property
    def operation_id(self):
        return self.contract.operation_id

    @property
    def input_fields(self):
        return self.contract.input_fields

    @property
    def required_fields(self):
        return self.contract.required_fields

    @property
    def output_fields(self):
        return self.contract.output_fields
