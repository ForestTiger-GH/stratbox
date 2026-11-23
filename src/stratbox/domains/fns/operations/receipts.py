"""Evidence accounting for small publication/control results outside table snapshots."""
from dataclasses import asdict, is_dataclass

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes


def record_control(value, invocation):
    identity = ByteIdentity.of(canonical_manifest_bytes(asdict(value) if is_dataclass(value) else value))
    invocation.record(identity)
    invocation.account_output(identity)
    return value


def record_acquired(value, invocation, observation_date):
    invocation.record(value.payload.identity, parameters={"observation_date": observation_date},
        resources={"request_sha256": value.receipt.request_sha256,
                   "source_id": value.receipt.source_id})
    invocation.account_output(value.payload.identity)
    return value
