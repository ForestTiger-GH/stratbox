"""Bounded archive member expansion and archive representation creation."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import zipfile
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import ByteIdentity, Material
from ._settings import _option
from ._values import _material


def archive_unpack(inputs, settings, context):
    material = _material(inputs["material"])
    max_members, max_bytes = _option(context, settings, "max_members", 1000), _option(context, settings, "max_unpacked_bytes", 256 * 1024 * 1024)
    selected = _option(context, settings, "names", ())
    if not zipfile.is_zipfile(BytesIO(material.data)):
        provider = context.provider("archive_reader")
        return {"members": tuple(provider.unpack(material, max_members=max_members, max_bytes=max_bytes, checkpoint=context.checkpoint))}
    result, total = [], 0
    with zipfile.ZipFile(BytesIO(material.data)) as archive:
        entries = archive.infolist()
        from stratbox.core.formats.archives.members import validate_members, zip_members, ArchiveLimits
        validate_members(zip_members(archive), ArchiveLimits(max_members, max_bytes,
            _option(context, settings, "max_member_bytes", max_bytes), max(1, len(material.data))))
        if len(entries) > max_members or sum(x.file_size for x in entries) > max_bytes:
            raise ExecutionFailure("archive.expansion_limit")
        if len({x.filename for x in entries}) != len(entries):
            raise ExecutionFailure("archive.duplicate_member")
        for entry in entries:
            context.checkpoint()
            if entry.is_dir() or selected and entry.filename not in selected:
                continue
            if "\\" in entry.filename or Path(entry.filename).is_absolute() or ".." in Path(entry.filename).parts:
                raise ExecutionFailure("archive.member_path")
            data = archive.read(entry)
            total += len(data)
            if total > max_bytes:
                raise ExecutionFailure("archive.expansion_limit")
            result.append(Material(data, source_id=material.source_id,
                metadata={**dict(material.metadata), "member": entry.filename, "parent": material.identity.sha256,
                    "container_asset_id": material.metadata.get("asset_id"), "asset_id": entry.filename,
                    "archive_depth": int(material.metadata.get("archive_depth", 0)) + 1},
                lineage=(*material.lineage, material.identity)))
    return {"members": tuple(result)}


def archive_pack(inputs, settings, context):
    limit = _option(context, settings, "max_bytes", 128 * 1024 * 1024)
    class BoundedBuffer(BytesIO):
        def write(self, data):
            if self.tell() + len(data) > limit: raise ExecutionFailure("archive.output_limit")
            return super().write(data)
    stream, names, manifest = BoundedBuffer(), set(), []
    members = inputs["members"]
    if len(members) > _option(context, settings, "max_members", 1000): raise ExecutionFailure("archive.member_limit")
    if sum(len(_material(value).data) for value in members) > _option(context, settings, "max_unpacked_bytes", 256 * 1024 * 1024): raise ExecutionFailure("archive.input_limit")
    from stratbox.core.formats.archives.members import validate_members, ArchiveMember, ArchiveLimits
    validate_members(tuple(ArchiveMember(str(_material(value).metadata.get("member", index)), len(_material(value).data))
        for index, value in enumerate(members)), ArchiveLimits(_option(context, settings, "max_members", 1000),
        _option(context, settings, "max_unpacked_bytes", 256 * 1024 * 1024),
        _option(context, settings, "max_member_bytes", 256 * 1024 * 1024), limit))
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, value in enumerate(members):
            context.checkpoint()
            material = _material(value)
            name = material.metadata.get("member", str(index))
            if "\\" in name or Path(name).is_absolute() or ".." in Path(name).parts:
                raise ExecutionFailure("archive.member_path")
            if name in names: raise ExecutionFailure("archive.duplicate_member")
            names.add(name)
            archive.writestr(name, material.data)
            manifest.append({"name": name, "identity": material.identity})
    data = stream.getvalue()
    with zipfile.ZipFile(BytesIO(data)) as archive:
        for record in manifest:
            if ByteIdentity.of(archive.read(record["name"])) != record["identity"]:
                raise ExecutionFailure("archive.verification_failed")
    return {"material": Material(data, "application/zip", metadata={"members": tuple(manifest)}, lineage=tuple(record["identity"] for record in manifest))}
