"""Bounded classified decisions for machine consumers; no raw inputs or paths."""


def diagnostic_projection(diagnostic):
    return {
        "code": diagnostic.code,
        "stage": diagnostic.stage,
        "component": diagnostic.component,
        "reason_class": diagnostic.reason_class,
        "retry_disposition": diagnostic.retry_disposition,
        "evidence_ref": diagnostic.evidence_ref,
        "reconciliation_owner": diagnostic.reconciliation_owner,
    }


def effect_projection(effect):
    return {
        "kind": effect.kind,
        "state": effect.state,
        "effect_id": effect.effect_id,
        "stage": effect.stage,
        "reconciliation_owner": effect.reconciliation_owner,
    }


def computation_projection(result):
    from stratbox.shared.identity import ByteIdentity

    receipt = result.computation
    if receipt is None:
        return None
    if (not isinstance(receipt.computation_id, ByteIdentity)
            or not isinstance(receipt.output, ByteIdentity)
            or receipt.method_fingerprint is not None and not isinstance(receipt.method_fingerprint, ByteIdentity)
            or not isinstance(receipt.qualifications, frozenset)
            or len(receipt.qualifications) > 32
            or any(type(item) is not str or len(item) > 128 for item in receipt.qualifications)):
        # Optional projections never hide an already retained result/effect.
        return None
    def identity(value):
        return None if value is None else {"sha256": value.sha256, "size": value.size}
    return {
        "id": identity(receipt.computation_id),
        "output": identity(receipt.output),
        "method_fingerprint": identity(receipt.method_fingerprint),
        "argument_coverage": ("unqualified" if "signature_complete" not in receipt.qualifications else
            "declared" if result.definition.request_fields else "whole_request"),
        "qualifications": sorted(receipt.qualifications),
    }
