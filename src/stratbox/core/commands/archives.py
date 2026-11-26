"""Bounded archive inventories and pure buffered or staged representations."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
from pathlib import PurePosixPath
from collections.abc import Mapping

from stratbox.core.formats.archives.members import (
    ArchiveError, ArchiveLimits, open_zip_stream, validate_members, zip_members,
)
from stratbox.core.formats.archives.store import ArchiveEntry, ArchiveWriteLimits, encode_zip
from stratbox.shared.data.archives import ArchiveInventory, ArchiveInventoryMember, ArchiveMemberSelection
from stratbox.shared.data.values import Assessment
from stratbox.shared.identity import ByteIdentity
from ._physical import material_properties, open_material, physical_material, representation_writer
from ._settings import _option


def _limits(context, settings, *, placement="buffered"):
    large = 64 * 1024**3 if placement == "staged" else 256 * 1024**2
    total = _option(context, settings, "max_unpacked_bytes", large)
    return ArchiveLimits(_option(context, settings, "max_members", 1000), total,
        _option(context, settings, "max_member_bytes", total),
        _option(context, settings, "max_packed_bytes", 64 * 1024**3),
        _option(context, settings, "max_metadata_bytes", 16 * 1024**2))


@contextmanager
def _contents(value, context, limits):
    material = physical_material(value)
    depth = int(getattr(material, "metadata", {}).get("archive_depth", 0)) + 1
    if not 1 <= depth <= 4:
        raise ArchiveError("archive.depth_limit")
    budget = getattr(context, "budget", None)
    if budget is not None:
        budget.check("archive_depth", depth)
    if not 0 < material.identity.size <= limits.packed_bytes:
        raise ArchiveError("archive.size_limit")
    with open_material(value, context) as stream:
        signature = stream.read(8)
        stream.seek(0)
        if signature.startswith(b"PK"):
            with open_zip_stream(stream, material.identity.size, limits, budget=budget,
                                 depth=depth, selected_only=True) as archive:
                yield "zip", zip_members(archive), archive.open
        elif signature.startswith(b"Rar!\x1a\x07"):
            provider = context.provider("archive_reader")
            if not callable(getattr(provider, "open", None)):
                raise ArchiveError("archive.reader_protocol_required")
            with provider.open(stream, limits=limits) as contents:
                members = tuple(contents.members())
                validate_members(members, limits, selected_only=True)
                if budget is not None:
                    budget.charge("objects", len(members))
                yield "rar", members, contents.open
        else:
            raise ArchiveError("archive.format_unsupported")


def _inventory(parent_identity, format, members, *, coverage="complete_inventory"):
    return ArchiveInventory(parent_identity, format, tuple(ArchiveInventoryMember(
        member.name, member.size, member.compressed_size,
        "directory" if member.directory else "file" if member.regular else "nonregular",
        member.encrypted, member.compression,
        "directory" if member.directory else "available") for member in members), coverage)


def archive_inspect(inputs, settings, context):
    value, limits = inputs["material"], _limits(context, settings)
    with _contents(value, context, limits) as (format, members, _):
        inventory = _inventory(physical_material(value).identity, format, members)
    return {"inventory": inventory, "assessment": Assessment(
        qualifications=frozenset({"inventory_only", "member_bytes_unverified"}))}


def _selection(inputs, settings, context, members):
    supplied = inputs.get("selection", _option(context, settings, "selection", None))
    if supplied is None:
        supplied = ArchiveMemberSelection(names=_option(context, settings, "names", None),
            suffixes=tuple(_option(context, settings, "suffixes", ())),
            allow_empty=_option(context, settings, "allow_empty", True))
    if not isinstance(supplied, ArchiveMemberSelection):
        raise ArchiveError("archive.selection_invalid")
    available = {member.name: member for member in members if not member.directory}
    if supplied.names is not None and any(name not in available for name in supplied.names):
        raise ArchiveError("archive.selected_member_missing")
    names = set(available if supplied.names is None else supplied.names)
    names -= set(supplied.exclude_names)
    suffixes = {suffix.casefold() for suffix in supplied.suffixes}
    selected = tuple(member for member in members if member.name in names and not member.directory
                     and (not suffixes or PurePosixPath(member.name).suffix.casefold() in suffixes))
    if not selected and not supplied.allow_empty:
        raise ArchiveError("archive.required_selection_empty")
    return selected


def archive_unpack(inputs, settings, context):
    value = inputs["material"]
    material = physical_material(value)
    properties = material_properties(value)
    placement = _option(context, settings, "placement", "buffered")
    if placement not in {"buffered", "staged"}:
        raise ArchiveError("material.placement_invalid")
    limits = _limits(context, settings, placement=placement)
    budget, result, identities = getattr(context, "budget", None), [], {}
    with _contents(value, context, limits) as (format, members, open_member):
        selected = _selection(inputs, settings, context, members)
        validate_members(selected, limits)
        for member in selected:
            context.checkpoint()
            metadata = {**properties["metadata"], "member": member.name,
                "parent": material.identity.sha256,
                "container_asset_id": properties["metadata"].get("asset_id"),
                "asset_id": member.name,
                "archive_depth": int(properties["metadata"].get("archive_depth", 0)) + 1}
            with open_member(member.name) as source, representation_writer(context,
                    placement=placement, max_bytes=member.size,
                    source_id=properties["source_id"], metadata=metadata,
                    lineage=(*properties["lineage"], material.identity),
                    source_uses=properties["source_uses"]) as writer:
                digest, size = sha256(), 0
                while True:
                    context.checkpoint()
                    chunk = source.read(min(65536, member.size - size + 1))
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > member.size:
                        raise ArchiveError("archive.member_size_mismatch")
                    if budget is not None:
                        budget.charge("decoded_bytes", len(chunk))
                    digest.update(chunk)
                    writer.stream.write(chunk)
                if size != member.size:
                    raise ArchiveError("archive.member_size_mismatch")
                extracted = writer.seal()
                identity = ByteIdentity(digest.hexdigest(), size)
                if extracted.identity != identity:
                    raise ArchiveError("archive.member_identity_mismatch")
                identities[member.name] = identity
                result.append(extracted)
        inventory = _inventory(material.identity, format, members)
        dispositions = tuple(replace(member,
            disposition="verified" if member.name in identities else
                "directory" if member.kind == "directory" else "excluded",
            identity=identities.get(member.name)) for member in inventory.members)
        coverage = "all_members_verified" if len(identities) == sum(not m.directory for m in members) else "selected_members_verified"
        inventory = replace(inventory, members=dispositions, coverage=coverage)
    return {"members": tuple(result), "inventory": inventory, "assessment": Assessment(
        expected=tuple(member.name for member in selected), observed=tuple(identities),
        qualifications=frozenset({coverage}))}


def archive_pack(inputs, settings, context):
    members = tuple(inputs["members"])
    placement = _option(context, settings, "placement", "buffered")
    limits = _limits(context, settings, placement=placement)
    if len(members) > limits.members:
        raise ArchiveError("archive.member_limit")
    names = _option(context, settings, "names", None)
    if names is not None and (isinstance(names, str) or len(names) != len(members)):
        raise ArchiveError("archive.names_count_mismatch")
    entries, manifest, uses = [], [], []
    for index, value in enumerate(members):
        explicit = None
        if isinstance(value, Mapping):
            if set(value) != {"name", "material"}:
                raise ArchiveError("archive.named_member_invalid")
            explicit, value = value["name"], value["material"]
            if names is not None and names[index] != explicit:
                raise ArchiveError("archive.member_name_conflict")
        material, properties = physical_material(value), material_properties(value)
        name = names[index] if names is not None else explicit if explicit is not None else \
            properties["metadata"].get("member", properties["metadata"].get("filename", str(index)))
        entries.append(ArchiveEntry(value, name, material.identity))
        manifest.append({"name": name, "identity": material.identity,
                         "source_id": properties["source_id"], "source_uses": properties["source_uses"]})
        for use in properties["source_uses"]:
            if use not in uses:
                uses.append(use)
    if any(entry.identity.size > limits.member_bytes for entry in entries):
        raise ArchiveError("archive.member_size_limit")
    max_bytes = _option(context, settings, "max_bytes", 64 * 1024**3 if placement == "staged" else 128 * 1024**2)
    compression = _option(context, settings, "compression", "deflated")
    with representation_writer(context, placement=placement, max_bytes=max_bytes,
            media_type="application/zip", metadata={"members": tuple(manifest), "compression": compression},
            lineage=tuple(entry.identity for entry in entries), source_uses=tuple(uses)) as writer:
        encoded = encode_zip(tuple(entries), writer.stream,
            open_member=lambda value: open_material(value, context), compression=compression,
            limits=ArchiveWriteLimits(limits.members, limits.unpacked_bytes), max_output_bytes=max_bytes,
            checkpoint=context.checkpoint, budget=getattr(context, "budget", None))
        material = writer.seal()
        if material.identity != encoded.identity:
            raise ArchiveError("archive.verification_failed")
    return {"material": material, "manifest": tuple(manifest), "assessment": Assessment(
        qualifications=frozenset({"all_members_verified", "deterministic_zip_metadata"}))}
