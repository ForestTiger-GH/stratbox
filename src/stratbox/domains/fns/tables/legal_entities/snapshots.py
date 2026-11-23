"""A portable bundle includes each workbook's partitioned tables and member evidence."""
import json
from dataclasses import replace

from stratbox.core.storage.datasets.codec import manifest_from
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, TableSchema, TypedTable, manifest_value
from stratbox.shared.data.workbooks import workbook_snapshot, workbook_from_snapshot
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

from ..snapshots import context_table, read_context
from .extraction import MemberInventory, WorkbookBundle, PROFILE

FLAKE = DataContract("fns.1yur.workbook_bundle.snapshot", 1, DataRole.EXTRACTS)
_T, _I = ScalarType.TEXT, ScalarType.INTEGER
_INVENTORY = TableSchema(DataContract("fns.1yur.member_inventory", 1), (
    ColumnSchema("name", _T), ColumnSchema("sha256", _T), ColumnSchema("size", _I),
    ColumnSchema("disposition", _T), ColumnSchema("reason", _T),
), ("name",))
_WORKBOOKS = TableSchema(DataContract("fns.1yur.member_manifests", 1), (
    ColumnSchema("ordinal", _I), ColumnSchema("name", _T), ColumnSchema("manifest", _T),
), ("ordinal",))


def flake_snapshot(value, *, dataset_id=None, version_id=None):
    if (not isinstance(value, WorkbookBundle) or value.context.series_id != "fns.1yur"
            or value.profile_id != PROFILE or not value.members
            or value.container_format not in {"standalone", "zip", "rar"}
            or not any(item.identity == value.source_identity for item in value.lineage)):
        raise ValueError("fns.1yur.flake_invalid")
    indexed = {item.name: item for item in value.inventory}
    if (len(indexed) != len(value.inventory) or len({name for name, _ in value.members}) != len(value.members)
            or any(item.disposition not in {"extracted", "original_only", "rejected_workbook"} or not item.reason for item in value.inventory)):
        raise ValueError("fns.1yur.member_inventory_invalid")
    tables, manifests = [], []
    for ordinal, (name, workbook) in enumerate(value.members):
        item = indexed.get(name)
        if (item is None or item.disposition != "extracted" or item.identity != workbook.source_identity
                or workbook.series_id != value.context.series_id or workbook.issue_id != value.context.issue_id):
            raise ValueError("fns.1yur.member_identity_mismatch")
        child = workbook_snapshot(workbook)
        manifests.append((ordinal, name, canonical_manifest_bytes(manifest_value(child.manifest)).decode("utf-8")))
        tables.extend((f"w{ordinal:04d}_{key}", table) for key, table in child.tables)
    if {name for name, _ in value.members} != {item.name for item in value.inventory if item.disposition == "extracted"}:
        raise ValueError("fns.1yur.member_inventory_incomplete")
    result = DatasetSnapshot.build(dataset_id or "fns.1yur.flake",
        version_id or "content", FLAKE,
        (("context", context_table(value.context, value.source_identity, PROFILE, value.qualifications,
            details_json=canonical_manifest_bytes({"container_format": value.container_format}).decode("utf-8"))),
         ("inventory", TypedTable(_INVENTORY, tuple((item.name, item.identity.sha256, item.identity.size,
            item.disposition, item.reason) for item in value.inventory))),
         ("workbooks", TypedTable(_WORKBOOKS, tuple(manifests))), *tables),
        coverage=value.coverage, inputs=value.lineage)
    if version_id is None:
        result = DatasetSnapshot(replace(result.manifest, version_id=result.identity.sha256), result.tables)
    return result


def flake_from_snapshot(snapshot):
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete
            or snapshot.manifest.contract != FLAKE
            or tuple(name for name, _ in snapshot.tables)[:3] != ("context", "inventory", "workbooks")
            or snapshot.table("inventory").schema != _INVENTORY
            or snapshot.table("workbooks").schema != _WORKBOOKS):
        raise ValueError("fns.1yur.flake_snapshot_invalid")
    context, identity, profile, qualifications, dispositions, details = read_context(snapshot.table("context"))
    if dispositions:
        raise ValueError("fns.1yur.flake_snapshot_context_invalid")
    inventory = tuple(MemberInventory(name, ByteIdentity(sha, size), disposition, reason)
        for name, sha, size, disposition, reason in snapshot.table("inventory").rows)
    members, expected = [], ["context", "inventory", "workbooks"]
    for index, (ordinal, name, manifest) in enumerate(snapshot.table("workbooks").rows):
        if index != ordinal:
            raise ValueError("fns.1yur.member_order_invalid")
        child_manifest = manifest_from(json.loads(manifest))
        child_tables = tuple((component.name, snapshot.table(f"w{ordinal:04d}_{component.name}"))
                             for component in child_manifest.components)
        expected.extend(f"w{ordinal:04d}_{component.name}" for component in child_manifest.components)
        members.append((name, workbook_from_snapshot(DatasetSnapshot(child_manifest, child_tables))))
    if tuple(expected) != tuple(name for name, _ in snapshot.tables):
        raise ValueError("fns.1yur.flake_snapshot_components_invalid")
    result = WorkbookBundle(context, identity, json.loads(details)["container_format"], tuple(members),
        inventory, snapshot.manifest.inputs, snapshot.manifest.coverage, qualifications, profile)
    if flake_snapshot(result, dataset_id=snapshot.manifest.dataset_id,
                      version_id=snapshot.manifest.version_id).identity != snapshot.identity:
        raise ValueError("fns.1yur.flake_snapshot_identity_mismatch")
    return result
