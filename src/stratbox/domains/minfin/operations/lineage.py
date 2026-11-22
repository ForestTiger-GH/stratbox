"""Canonical domain value identities used by every retained/direct table path."""
from __future__ import annotations

from dataclasses import asdict

from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

from ..tables.contracts import FlakeTable, TableExtract, SerializeRequest, SerializeFlakeRequest
from ..tables.representation import serialize_tables
from ..tables.flake_codec import serialize_flake


def use_representation(invocation, value: Representation, *, role: str, source_id: str | None = None) -> None:
    invocation.check_cancelled()
    invocation.budget.charge("input_bytes", value.identity.size)
    invocation.use(UsedInputReceipt(role, value.identity, value.media_type, "inline", source_id))


def use_extract(invocation, value: TableExtract, *, role: str = "extract") -> Representation:
    representation = serialize_tables(SerializeRequest(value))
    use_representation(invocation, representation, role=role, source_id=value.source_id)
    invocation.budget.charge("cells", sum(len(sheet.cells) for sheet in value.sheets))
    return representation


def use_flake(invocation, value: FlakeTable) -> Representation:
    representation = serialize_flake(SerializeFlakeRequest(value))
    use_representation(invocation, representation, role="flake", source_id=value.source_id)
    invocation.budget.charge("cells", len(value.rows) * len(value.columns))
    return representation


def record_representation(invocation, value: Representation, *, parameters=None, resources=None) -> None:
    invocation.check_cancelled()
    invocation.account_output(value.identity)
    invocation.record(value.identity, parameters=parameters, resources=resources)


def record_value(invocation, value, *, schema: str, parameters=None, resources=None) -> None:
    data = canonical_manifest_bytes({"schema": schema, "value": asdict(value)})
    identity = ByteIdentity.of(data)
    invocation.check_cancelled()
    invocation.account_output(identity)
    invocation.record(identity, parameters=parameters, resources=resources)
