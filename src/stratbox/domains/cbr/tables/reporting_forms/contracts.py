"""Public contracts for exact CBR form inputs, data and presentations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, TYPE_CHECKING

from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.core.formats.dbf_lossless import DBFTable
from stratbox.shared.data.representation import Representation
from stratbox.shared.material_collections import CollectionManifest

if TYPE_CHECKING:
    from pandas import DataFrame


@dataclass(frozen=True, slots=True)
class FormKey:
    code: str
    as_of: date


@dataclass(frozen=True, slots=True)
class SelectFormSourcesRequest:
    keys: tuple[FormKey, ...]


@dataclass(frozen=True, slots=True)
class FormSource:
    key: FormKey
    url: str


@dataclass(frozen=True, slots=True)
class ParseFormRequest:
    key: FormKey
    payload: SourcePayload


@dataclass(frozen=True, slots=True)
class ExtractFormRequest:
    key: FormKey
    payload: SourcePayload
    text_encoding: str = "cp866"
    encoding_overrides: tuple[tuple[str, str], ...] = ()
    strict: bool = True
    member_name: str = "source.dbf"


@dataclass(frozen=True, slots=True)
class FormMember:
    name: str
    data: bytes
    identity: ByteIdentity
    status: str
    table: DBFTable | None = None
    diagnostic: str | None = None


@dataclass(frozen=True, slots=True)
class FormFlakes:
    key: FormKey
    original_identity: ByteIdentity
    source_id: str | None
    media_type: str
    members: tuple[FormMember, ...]
    lineage: tuple[UsedInputReceipt, ...]
    archived: bool
    method_version: str = "cbr.forms.flakes.v1"

    @property
    def complete(self) -> bool:
        return all(member.status in {"decoded", "auxiliary"} for member in self.members)


@dataclass(frozen=True, slots=True)
class NormalizeFormRequest:
    flakes: FormFlakes
    include_deleted: bool = False


@dataclass(frozen=True, slots=True)
class FormFlakeSnapshotRequest:
    flakes: FormFlakes
    dataset_id: str
    version_id: str


@dataclass(frozen=True, slots=True)
class DiscoverFormsRequest:
    payload: SourcePayload | None = None
    date_from: date | None = None
    date_to: date | None = None
    form_codes: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class FormInventory:
    sources: tuple[FormSource, ...]
    index_identity: ByteIdentity
    lineage: tuple[UsedInputReceipt, ...]
    selection: tuple[str | None, str | None, tuple[str, ...] | None]
    unsupported_sources: tuple[tuple[FormSource, str], ...] = ()


@dataclass(frozen=True, slots=True)
class FormHistoryRequest:
    snapshots: tuple[FormSnapshot, ...]
    dataset_id: str
    version_id: str


@dataclass(frozen=True, slots=True)
class FormSnapshot:
    key: FormKey
    physical_fields: Mapping[str, str]
    rows: DataFrame
    lineage: tuple[UsedInputReceipt, ...]
    evidence: ComputationReceipt | None = None


@dataclass(frozen=True, slots=True)
class RenderFormFlakesRequest:
    flakes: FormFlakes
    prefix: str = ""
    include_member_originals: bool = True


@dataclass(frozen=True, slots=True)
class FormFlakeExport:
    files: tuple[tuple[str, Representation], ...]
    manifest: CollectionManifest


@dataclass(frozen=True, slots=True)
class ReadFormFlakeExportRequest:
    files: tuple[tuple[str, SourcePayload], ...]
    manifest: CollectionManifest
