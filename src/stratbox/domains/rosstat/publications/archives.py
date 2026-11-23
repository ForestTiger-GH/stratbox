"""Regional issue archive inventory and exact member acquisition, with lineage."""
from dataclasses import dataclass
from pathlib import PurePosixPath

from stratbox.core.formats.archives.members import (
    ArchiveLimits,ArchiveMember,RarArchiveReader,open_zip,zip_members,validate_members,extract_members,
)
from stratbox.shared.evidence import SourcePayload,UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

@dataclass(frozen=True,slots=True)
class RegionalArchiveInventory:
    source_identity: ByteIdentity
    members: tuple[ArchiveMember,...]
    lineage: tuple[UsedInputReceipt,...]

@dataclass(frozen=True,slots=True)
class RegionalMember:
    name: str
    payload: SourcePayload
    container_identity: ByteIdentity
    lineage: tuple[UsedInputReceipt,...]


def inspect_archive(payload: SourcePayload, *, limits=ArchiveLimits(), rar_reader=None, budget=None) -> RegionalArchiveInventory:
    if payload.data.startswith(b"Rar!"):
        with (rar_reader or RarArchiveReader()).open(payload.data) as archive:
            members=archive.members()
            validate_members(members,limits)
            if len(payload.data)>limits.packed_bytes:
                raise ValueError("archive.size_limit")
    else:
        with open_zip(payload.data,limits,budget=budget) as archive:
            members=zip_members(archive)
    return RegionalArchiveInventory(payload.identity,members,(UsedInputReceipt.for_payload(payload,"regional_archive"),))


def acquire_members(payload: SourcePayload, inventory: RegionalArchiveInventory, names: tuple[str,...], *,
                    limits=ArchiveLimits(),rar_reader=None,budget=None,checkpoint=None) -> tuple[RegionalMember,...]:
    if inventory.source_identity != payload.identity or not names:
        raise ValueError("rosstat.archive_inventory_mismatch")
    if not set(names) <= {member.name for member in inventory.members if not member.directory}:
        raise ValueError("rosstat.archive_member_unknown")
    values=extract_members(payload.data,select=lambda available:names,limits=limits,
        rar_reader=rar_reader or (RarArchiveReader() if payload.data.startswith(b"Rar!") else None),
        budget=budget,checkpoint=checkpoint)
    result=[]
    media={".xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
           ".xls":"application/vnd.ms-excel",".pdf":"application/pdf",
           ".docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    for name,data in values.items():
        source=SourcePayload(data,media.get(PurePosixPath(name).suffix.lower(),"application/octet-stream"),payload.source_id)
        receipt=UsedInputReceipt.for_payload(source,"archive_member",container=payload.identity,member=name)
        result.append(RegionalMember(name,source,payload.identity,(*inventory.lineage,receipt)))
    return tuple(result)
