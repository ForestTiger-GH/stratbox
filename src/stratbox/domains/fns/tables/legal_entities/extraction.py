"""Preserve every admitted 1-YUR workbook before selecting a reviewed table."""
from dataclasses import dataclass, replace

from stratbox.core.formats.archives.members import extract_members, open_zip
from stratbox.core.formats.spreadsheets.extracts import extract_workbook
from stratbox.core.formats.spreadsheets.workbook_input import WorkbookError
from stratbox.shared.data.snapshots import CoverageDimension, SnapshotCoverage
from stratbox.shared.data.workbooks import WorkbookExtract
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

from ...publications.contracts import ReleaseContext
from .archive import _CONTAINER_LIMITS, _WORKBOOK_LIMITS
from .history import HistoryError
from .parser import OLE

PROFILE = "fns.1yur.all-workbook-cells.v1"


def _is_workbook_package(data):
    if not data.startswith(b"PK\x03\x04"):
        return False
    with open_zip(data, replace(_WORKBOOK_LIMITS, packed_bytes=_CONTAINER_LIMITS.packed_bytes)) as archive:
        names = set(archive.namelist())
        return "[Content_Types].xml" in names and bool({"xl/workbook.xml", "xl/workbook.bin"} & names)


@dataclass(frozen=True, slots=True)
class MemberInventory:
    name: str
    identity: ByteIdentity
    disposition: str
    reason: str


@dataclass(frozen=True, slots=True)
class WorkbookBundle:
    context: ReleaseContext
    source_identity: ByteIdentity
    container_format: str
    members: tuple[tuple[str, WorkbookExtract], ...]
    inventory: tuple[MemberInventory, ...]
    lineage: tuple[UsedInputReceipt, ...]
    coverage: SnapshotCoverage
    qualifications: tuple[str, ...]
    profile_id: str = PROFILE

    @property
    def identity(self):
        from .snapshots import flake_snapshot
        return flake_snapshot(self).identity


def extract_bundle(payload, context, *, rar_reader=None, budget=None, checkpoint=None):
    if context.series_id != "fns.1yur":
        raise HistoryError("SOURCE_SERIES_MISMATCH")
    if not 0 < len(payload.data) <= _CONTAINER_LIMITS.packed_bytes:
        raise HistoryError("SOURCE_SIZE_INVALID")
    if payload.data.startswith((OLE, b"\x09\x00", b"\x09\x02", b"\x09\x04", b"\x09\x08")) or _is_workbook_package(payload.data):
        raw_members = {"main": payload.data}
        container_format = "standalone"
    else:
        raw_members = extract_members(payload.data, select=lambda names: names,
            limits=_CONTAINER_LIMITS, rar_reader=rar_reader, budget=budget, checkpoint=checkpoint)
        container_format = "rar" if payload.data.startswith(b"Rar!") else "zip"
    lineage = [UsedInputReceipt.for_payload(payload, "source_asset")]
    members, inventory, qualifications = [], [], []
    for ordinal, (name, raw) in enumerate(raw_members.items()):
        if checkpoint is not None:
            checkpoint()
        identity = ByteIdentity.of(raw)
        candidate = (container_format == "standalone" or raw.startswith((OLE, b"PK\x03\x04")) or
                     name.casefold().endswith((".xls", ".xlsx", ".xlsm", ".xlsb")))
        if not candidate:
            inventory.append(MemberInventory(name, identity, "original_only", "non_workbook_member"))
            qualifications.append("source.non_workbook_members_retained_in_original")
            continue
        source = SourcePayload(raw, source_id=payload.source_id)
        receipt = UsedInputReceipt.for_payload(source, "workbook_member",
            container=payload.identity if container_format != "standalone" else None,
            member=name if container_format != "standalone" else None)
        try:
            workbook = extract_workbook(source, series_id=context.series_id, issue_id=context.issue_id,
                asset_id=context.asset_id if container_format == "standalone" else "member-" + ByteIdentity.of(name.encode("utf-8")).sha256,
                profile_id=PROFILE, budget=budget, checkpoint=checkpoint)
        except WorkbookError as error:
            inventory.append(MemberInventory(name, identity, "rejected_workbook", str(error)))
            qualifications.append("source.workbook_member_unreadable")
            continue
        workbook = replace(workbook, lineage=(receipt,))
        lineage.append(receipt)
        members.append((name, workbook))
        inventory.append(MemberInventory(name, identity, "extracted", "all_decoder_visible_cells"))
        qualifications.extend(workbook.qualifications)
    if not members:
        raise HistoryError("SOURCE_NO_ADMITTED_WORKBOOK")
    incomplete = any(item.disposition == "rejected_workbook" for item in inventory)
    requested = tuple(item.name for item in inventory if item.disposition != "original_only")
    materialized = tuple(name for name, _ in members)
    missing = tuple(item.name for item in inventory if item.disposition == "rejected_workbook")
    return WorkbookBundle(context, payload.identity, container_format, tuple(members), tuple(inventory),
        tuple(lineage), SnapshotCoverage("partial" if incomplete else "complete",
            "All decoder-visible cells of every admitted workbook; every other container member has an explicit disposition.",
            (CoverageDimension("workbook_members", requested=requested, materialized=materialized,
                validated=materialized, output=materialized, missing=missing),)),
        tuple(dict.fromkeys(qualifications)))
