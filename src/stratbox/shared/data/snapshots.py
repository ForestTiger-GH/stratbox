"""Portable typed tables and immutable logical dataset snapshots.

These values describe data, schema and lineage. Provider identifiers and physical
locations belong to references, and never participate in a logical content hash.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
import base64
import re
import struct

from stratbox.shared.data.processing import DataContract
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", re.ASCII)


def identifier(value: str) -> None:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError("dataset.invalid_identifier")


class ScalarType(str, Enum):
    BOOLEAN = "boolean"
    INT64 = "int64"
    INTEGER = "integer"
    FLOAT64 = "float64"
    DECIMAL = "decimal"
    TEXT = "text"
    BINARY = "binary"
    DATE = "date"
    TIMESTAMP = "timestamp"
    LOCAL_DATETIME = "local_datetime"
    DURATION = "duration"


@dataclass(frozen=True, slots=True)
class ColumnSchema:
    name: str
    scalar_type: ScalarType
    nullable: bool = False
    unit: str | None = None

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name or len(self.name) > 256:
            raise ValueError("dataset.invalid_column")
        if not isinstance(self.scalar_type, ScalarType) or type(self.nullable) is not bool:
            raise ValueError("dataset.invalid_column_type")
        if self.unit is not None and (not isinstance(self.unit, str) or not self.unit or len(self.unit) > 256):
            raise ValueError("dataset.invalid_unit")


def contract_value(contract: DataContract) -> dict:
    return {"schema_id": contract.schema_id, "version": contract.version,
            "role": contract.role.value if contract.role is not None else None}


@dataclass(frozen=True, slots=True)
class TableSchema:
    contract: DataContract
    columns: tuple[ColumnSchema, ...]
    primary_key: tuple[str, ...] = ()
    identity: ByteIdentity = field(init=False)

    def __post_init__(self):
        if not isinstance(self.contract, DataContract) or not isinstance(self.columns, tuple):
            raise ValueError("dataset.invalid_schema")
        if any(not isinstance(column, ColumnSchema) for column in self.columns):
            raise ValueError("dataset.invalid_schema")
        names = tuple(column.name for column in self.columns)
        if len(set(names)) != len(names):
            raise ValueError("dataset.duplicate_column")
        if (not isinstance(self.primary_key, tuple) or len(set(self.primary_key)) != len(self.primary_key)
                or any(name not in names for name in self.primary_key)):
            raise ValueError("dataset.invalid_primary_key")
        if any(column.nullable for column in self.columns if column.name in self.primary_key):
            raise ValueError("dataset.nullable_primary_key")
        object.__setattr__(self, "identity", ByteIdentity.of(canonical_manifest_bytes(schema_value(self))))


def schema_value(schema: TableSchema) -> dict:
    return {"encoding": "stratbox.table-schema.v1", "contract": contract_value(schema.contract),
            "columns": [{"name": c.name, "type": c.scalar_type.value, "nullable": c.nullable, "unit": c.unit}
                        for c in schema.columns], "primary_key": list(schema.primary_key)}


def scalar_value(value: object, column: ColumnSchema) -> object:
    """Encode without implicit numeric coercion, timezone loss or float rounding."""
    if value is None:
        if column.nullable:
            return None
        raise ValueError("dataset.null_not_allowed")
    kind = column.scalar_type
    if kind is ScalarType.BOOLEAN and type(value) is bool:
        return value
    if kind in {ScalarType.INTEGER, ScalarType.INT64} and type(value) is int:
        if kind is ScalarType.INT64 and not -(2**63) <= value < 2**63:
            raise ValueError("dataset.integer_out_of_range")
        return str(value)
    if kind is ScalarType.FLOAT64 and type(value) is float:
        # Includes signed zero and the exact bit pattern of NaN/infinity.
        return struct.pack(">d", value).hex()
    if kind is ScalarType.DECIMAL and isinstance(value, Decimal) and value.is_finite():
        return str(value)
    if kind is ScalarType.TEXT and type(value) is str:
        return value
    if kind is ScalarType.BINARY and type(value) is bytes:
        return base64.b64encode(value).decode("ascii")
    if kind is ScalarType.DATE and type(value) is date:
        return value.isoformat()
    if kind is ScalarType.TIMESTAMP and type(value) is datetime and value.utcoffset() is not None:
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    if kind is ScalarType.LOCAL_DATETIME and type(value) is datetime and value.utcoffset() is None:
        return value.isoformat(timespec="microseconds")
    if kind is ScalarType.DURATION and type(value) is timedelta:
        return str((value.days * 86400 + value.seconds) * 1_000_000 + value.microseconds)
    raise TypeError("dataset.scalar_type_mismatch")


@dataclass(frozen=True, slots=True)
class TypedTable:
    schema: TableSchema
    rows: tuple[tuple[object, ...], ...]
    identity: ByteIdentity = field(init=False)

    def __post_init__(self):
        if not isinstance(self.schema, TableSchema) or not isinstance(self.rows, tuple):
            raise ValueError("dataset.invalid_table")
        keys: set[tuple[object, ...]] = set()
        positions = tuple(i for i, column in enumerate(self.schema.columns) if column.name in self.schema.primary_key)
        for row in self.rows:
            if not isinstance(row, tuple) or len(row) != len(self.schema.columns):
                raise ValueError("dataset.row_width_mismatch")
            values = tuple(scalar_value(value, column) for value, column in zip(row, self.schema.columns))
            if positions:
                key = tuple(values[i] for i in positions)
                if key in keys:
                    raise ValueError("dataset.duplicate_primary_key")
                keys.add(key)
        object.__setattr__(self, "identity", ByteIdentity.of(canonical_manifest_bytes(table_value(self))))


def table_value(table: TypedTable) -> dict:
    return {"encoding": "stratbox.typed-table.logical.v1", "schema": schema_value(table.schema),
            "rows": [[scalar_value(value, column) for value, column in zip(row, table.schema.columns)]
                     for row in table.rows]}


@dataclass(frozen=True, slots=True)
class TableComponent:
    name: str
    schema: TableSchema
    identity: ByteIdentity
    row_count: int

    def __post_init__(self):
        identifier(self.name)
        if not isinstance(self.schema, TableSchema) or not isinstance(self.identity, ByteIdentity):
            raise ValueError("dataset.invalid_component")
        if type(self.row_count) is not int or self.row_count < 0:
            raise ValueError("dataset.invalid_row_count")

    @classmethod
    def for_table(cls, name: str, table: TypedTable) -> TableComponent:
        return cls(name, table.schema, table.identity, len(table.rows))


@dataclass(frozen=True, slots=True)
class SnapshotCoverage:
    """Caller-declared source coverage, independent of selected table membership."""

    status: str
    description: str | None = None

    def __post_init__(self):
        if self.status not in {"complete", "partial", "unknown"}:
            raise ValueError("dataset.invalid_coverage")
        if self.description is not None and (not isinstance(self.description, str) or not self.description
                                             or len(self.description) > 4096):
            raise ValueError("dataset.invalid_coverage")


def identity_value(identity: ByteIdentity) -> dict:
    return {"sha256": identity.sha256, "size": identity.size}


def input_value(receipt: UsedInputReceipt) -> dict:
    identifier(receipt.role)
    if not isinstance(receipt.identity, ByteIdentity) or receipt.availability not in {"inline", "reference_only"}:
        raise ValueError("dataset.invalid_input_receipt")
    if not isinstance(receipt.media_type, str) or not re.fullmatch(r"[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+", receipt.media_type):
        raise ValueError("dataset.invalid_input_receipt")
    if receipt.source_id is not None and (not isinstance(receipt.source_id, str) or not receipt.source_id):
        raise ValueError("dataset.invalid_input_receipt")
    if (receipt.container is None) != (receipt.member is None):
        raise ValueError("dataset.invalid_input_receipt")
    if receipt.container is not None and (not isinstance(receipt.container, ByteIdentity) or not isinstance(receipt.member, str) or not receipt.member):
        raise ValueError("dataset.invalid_input_receipt")
    if receipt.version is not None and not isinstance(receipt.version, ByteIdentity):
        raise ValueError("dataset.invalid_input_receipt")
    return {"role": receipt.role, "identity": identity_value(receipt.identity),
            "media_type": receipt.media_type, "availability": receipt.availability,
            "source_id": receipt.source_id,
            "container": identity_value(receipt.container) if receipt.container else None,
            "member": receipt.member, "version": identity_value(receipt.version) if receipt.version else None}


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_id: str
    version_id: str
    contract: DataContract
    components: tuple[TableComponent, ...]
    coverage: SnapshotCoverage
    inputs: tuple[UsedInputReceipt, ...] = ()
    parents: tuple[ByteIdentity, ...] = ()
    identity: ByteIdentity = field(init=False)

    def __post_init__(self):
        identifier(self.dataset_id)
        identifier(self.version_id)
        if not isinstance(self.contract, DataContract) or not isinstance(self.coverage, SnapshotCoverage):
            raise ValueError("dataset.invalid_manifest")
        if not isinstance(self.components, tuple) or any(not isinstance(c, TableComponent) for c in self.components):
            raise ValueError("dataset.invalid_manifest")
        if len({c.name for c in self.components}) != len(self.components):
            raise ValueError("dataset.duplicate_component")
        if not isinstance(self.inputs, tuple) or any(not isinstance(i, UsedInputReceipt) for i in self.inputs):
            raise ValueError("dataset.invalid_inputs")
        if not isinstance(self.parents, tuple) or any(not isinstance(i, ByteIdentity) for i in self.parents):
            raise ValueError("dataset.invalid_parents")
        if len(set(self.parents)) != len(self.parents):
            raise ValueError("dataset.duplicate_parent")
        logical = manifest_value(self)
        # Availability describes how an operation received evidence. It is
        # preserved by the codec, but memory versus retained input is not a
        # different logical dataset.
        for receipt in logical["inputs"]:
            receipt.pop("availability")
        object.__setattr__(self, "identity", ByteIdentity.of(canonical_manifest_bytes(logical)))


def manifest_value(manifest: DatasetManifest) -> dict:
    return {"encoding": "stratbox.dataset.logical.v1", "dataset_id": manifest.dataset_id,
            "version_id": manifest.version_id, "contract": contract_value(manifest.contract),
            "components": [{"name": c.name, "schema": schema_value(c.schema),
                            "identity": identity_value(c.identity), "row_count": c.row_count}
                           for c in manifest.components],
            "coverage": {"status": manifest.coverage.status, "description": manifest.coverage.description},
            "inputs": [input_value(i) for i in manifest.inputs],
            "parents": [identity_value(i) for i in manifest.parents]}


@dataclass(frozen=True, slots=True)
class DatasetSnapshot:
    """A pinned manifest plus all or an explicitly selected subset of its tables."""

    manifest: DatasetManifest
    tables: tuple[tuple[str, TypedTable], ...]

    def __post_init__(self):
        if not isinstance(self.manifest, DatasetManifest) or not isinstance(self.tables, tuple):
            raise ValueError("dataset.invalid_snapshot")
        declared = {c.name: c for c in self.manifest.components}
        seen: set[str] = set()
        for pair in self.tables:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError("dataset.invalid_table_binding")
            name, table = pair
            if name in seen or name not in declared or not isinstance(table, TypedTable):
                raise ValueError("dataset.invalid_table_binding")
            component = declared[name]
            if table.identity != component.identity or table.schema != component.schema or len(table.rows) != component.row_count:
                raise ValueError("dataset.component_mismatch")
            seen.add(name)
        if tuple(name for name, _ in self.tables) != tuple(c.name for c in self.manifest.components if c.name in seen):
            raise ValueError("dataset.component_order_mismatch")

    @property
    def complete(self) -> bool:
        return len(self.tables) == len(self.manifest.components)

    @property
    def identity(self) -> ByteIdentity:
        return self.manifest.identity

    def table(self, name: str) -> TypedTable:
        for candidate, table in self.tables:
            if candidate == name:
                return table
        raise KeyError(name)

    @classmethod
    def build(cls, dataset_id: str, version_id: str, contract: DataContract,
              tables: tuple[tuple[str, TypedTable], ...], *, coverage: SnapshotCoverage,
              inputs: tuple[UsedInputReceipt, ...] = (), parents: tuple[ByteIdentity, ...] = ()) -> DatasetSnapshot:
        manifest = DatasetManifest(dataset_id, version_id, contract,
                                   tuple(TableComponent.for_table(name, table) for name, table in tables), coverage, inputs, parents)
        return cls(manifest, tables)


@dataclass(frozen=True, slots=True)
class SnapshotReference:
    provider_id: str
    scope_id: str
    dataset_id: str
    version_id: str
    identity: ByteIdentity

    def __post_init__(self):
        for value in (self.provider_id, self.scope_id, self.dataset_id, self.version_id):
            identifier(value)
        if not isinstance(self.identity, ByteIdentity):
            raise ValueError("dataset.invalid_reference")


@dataclass(frozen=True, slots=True)
class ComponentLink:
    name: str
    snapshot: SnapshotReference
    component: str

    def __post_init__(self):
        identifier(self.name)
        identifier(self.component)
        if not isinstance(self.snapshot, SnapshotReference):
            raise ValueError("dataset.invalid_component_link")


@dataclass(frozen=True, slots=True)
class DatasetAssembly:
    """Composition of pinned components; it never implies row concatenation."""

    manifest: DatasetManifest
    links: tuple[ComponentLink, ...]

    def __post_init__(self):
        if not isinstance(self.manifest, DatasetManifest) or not isinstance(self.links, tuple):
            raise ValueError("dataset.invalid_assembly")
        if any(not isinstance(link, ComponentLink) for link in self.links):
            raise ValueError("dataset.invalid_assembly")
        if tuple(link.name for link in self.links) != tuple(c.name for c in self.manifest.components):
            raise ValueError("dataset.component_order_mismatch")
        if set(self.manifest.parents) != {link.snapshot.identity for link in self.links}:
            raise ValueError("dataset.assembly_parent_mismatch")

    @property
    def identity(self) -> ByteIdentity:
        return self.manifest.identity
