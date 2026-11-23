"""Complete, editioned industry values in provider-independent snapshots.

Every supported domain structure is explicitly admitted. Tabular components
remain independently inspectable typed tables; the bounded metadata component
describes their meaning and preserves receipts, selection and geography.
"""
from __future__ import annotations

from dataclasses import fields
import json

from stratbox.core.formats.dataframes import (
    frame_from_table, frame_to_table, scalar_from_value, scalar_to_value,
)
from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.data.lineage import computation_from, computation_value
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.identity import canonical_manifest_bytes


_ROLES = {"flake": DataRole.EXTRACTS, "stream": DataRole.INTEGRATED,
          "calculation": DataRole.INTEGRATED, "view": DataRole.PRODUCTS}
_METADATA_LIMIT = 16 * 1024 * 1024


def snapshot_contract(family, kind):
    if family not in {"0105a", "0104a"} or kind not in _ROLES:
        raise ValueError("industry.snapshot_profile_unsupported")
    return DataContract(f"cbr.industries.{family}.{kind}.snapshot", 1, _ROLES[kind])


def value_snapshot(value, *, family, kind, dataset_id, version_id, inputs=(), types, checkpoint=None):
    import pandas as pd

    contract = snapshot_contract(family, kind)
    if type(value) is not types[kind]:
        raise ValueError("industry.snapshot_value_mismatch")
    names = {cls: name for name, cls in types.items()}
    tables = []

    def encode(item, depth=0):
        if depth > 48:
            raise ValueError("industry.snapshot_structure_limit")
        if checkpoint is not None:
            checkpoint()
        if isinstance(item, pd.DataFrame):
            name = f"frame_{len(tables)}"
            table, metadata = frame_to_table(item,
                contract=DataContract(f"{contract.schema_id}.frame", 1, contract.role), checkpoint=checkpoint)
            tables.append((name, table))
            return {"node": "frame", "name": name, "metadata": metadata}
        if isinstance(item, ComputationReceipt):
            return {"node": "computation", "value": computation_value(item)}
        if type(item) in names:
            return {"node": names[type(item)], "fields": {field.name: encode(getattr(item, field.name), depth + 1)
                                                          for field in fields(item)}}
        if isinstance(item, tuple):
            return {"node": "tuple", "items": [encode(x, depth + 1) for x in item]}
        if isinstance(item, list):
            return {"node": "list", "items": [encode(x, depth + 1) for x in item]}
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise ValueError("industry.snapshot_mapping_invalid")
            return {"node": "mapping", "items": {key: encode(val, depth + 1) for key, val in item.items()}}
        return {"node": "scalar", "value": scalar_to_value(item)}

    body = canonical_manifest_bytes({"profile": "cbr.industry.snapshot.v1", "family": family, "kind": kind,
        "quantity_kind": "stock" if family == "0105a" else "flow",
        "period_basis": "as_of" if family == "0105a" else "reference_month",
        "unit": "million_rubles", "value": encode(value)})
    if len(body) > _METADATA_LIMIT:
        raise ValueError("industry.snapshot_metadata_limit")
    schema = TableSchema(DataContract(f"{contract.schema_id}.metadata", 1, contract.role),
                         (ColumnSchema("descriptor", ScalarType.TEXT),))
    partial = bool(getattr(value, "is_partial", False) or getattr(getattr(value, "selection", None), "industry_codes", None))
    return DatasetSnapshot.build(dataset_id, version_id, contract,
        (("metadata", TypedTable(schema, ((body.decode("utf-8"),),))), *tables),
        coverage=SnapshotCoverage("partial" if partial else "unknown",
            "Selected source issues and industries; publisher-wide historical completeness is unspecified."),
        inputs=tuple(inputs))


def value_from_snapshot(snapshot, *, family, kind, types, checkpoint=None):
    contract = snapshot_contract(family, kind)
    if not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete or snapshot.manifest.contract != contract:
        raise ValueError("industry.snapshot_contract_mismatch")
    metadata = snapshot.table("metadata")
    schema = TableSchema(DataContract(f"{contract.schema_id}.metadata", 1, contract.role),
                         (ColumnSchema("descriptor", ScalarType.TEXT),))
    if metadata.schema != schema or len(metadata.rows) != 1:
        raise ValueError("industry.snapshot_metadata_invalid")
    encoded = metadata.rows[0][0].encode("utf-8")
    if len(encoded) > _METADATA_LIMIT:
        raise ValueError("industry.snapshot_metadata_limit")
    body = json.loads(encoded)
    if (canonical_manifest_bytes(body) != encoded or set(body) != {"profile", "family", "kind", "quantity_kind", "period_basis", "unit", "value"}
            or body["profile"] != "cbr.industry.snapshot.v1" or body["family"] != family or body["kind"] != kind
            or body["quantity_kind"] != ("stock" if family == "0105a" else "flow")
            or body["period_basis"] != ("as_of" if family == "0105a" else "reference_month")
            or body["unit"] != "million_rubles"):
        raise ValueError("industry.snapshot_metadata_invalid")
    used = []

    def decode(item, depth=0):
        if depth > 48 or not isinstance(item, dict):
            raise ValueError("industry.snapshot_structure_invalid")
        if checkpoint is not None:
            checkpoint()
        node = item.get("node")
        if node == "frame" and set(item) == {"node", "name", "metadata"}:
            name = item["name"]
            if not isinstance(name, str) or not name.startswith("frame_") or name in used:
                raise ValueError("industry.snapshot_component_invalid")
            used.append(name)
            table = snapshot.table(name)
            if table.schema.contract != DataContract(f"{contract.schema_id}.frame", 1, contract.role):
                raise ValueError("industry.snapshot_component_invalid")
            return frame_from_table(table, item["metadata"], checkpoint=checkpoint)
        if node == "computation" and set(item) == {"node", "value"}:
            return computation_from(item["value"])
        if node in types and set(item) == {"node", "fields"}:
            cls = types[node]
            if not isinstance(item["fields"], dict) or set(item["fields"]) != {field.name for field in fields(cls)}:
                raise ValueError("industry.snapshot_fields_invalid")
            return cls(**{name: decode(field, depth + 1) for name, field in item["fields"].items()})
        if node in {"tuple", "list"} and set(item) == {"node", "items"} and isinstance(item["items"], list):
            values = [decode(x, depth + 1) for x in item["items"]]
            return tuple(values) if node == "tuple" else values
        if node == "mapping" and set(item) == {"node", "items"} and isinstance(item["items"], dict):
            return {key: decode(val, depth + 1) for key, val in item["items"].items()}
        if node == "scalar" and set(item) == {"node", "value"}:
            return scalar_from_value(item["value"])
        raise ValueError("industry.snapshot_node_invalid")

    value = decode(body["value"])
    expected_names = ("metadata", *(f"frame_{index}" for index in range(len(used))))
    if (type(value) is not types[kind] or tuple(name for name, _ in snapshot.tables) != expected_names
            or set(used) != set(expected_names[1:])):
        raise ValueError("industry.snapshot_value_mismatch")
    return value


__all__ = ("snapshot_contract", "value_snapshot", "value_from_snapshot")
