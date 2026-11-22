"""Read-only machine adapters owned by the daily offices domain."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date

from stratbox.core.execution.machine.contracts import ReadOnlyWireCodec, WireRequestError
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.data.releases import CompareReleaseRequest
from . import operations
from .contracts import ParseOfficesRequest

from .machine_contracts import PARSE_CONTRACT, COMPARE_CONTRACT



def _parse(data, materials, context):
    try:
        day = date.fromisoformat(data["capture_date"])
    except ValueError:
        raise WireRequestError("request.invalid_date") from None
    payload = materials.source(data["source_ref"])
    if not isinstance(payload, SourcePayload):
        raise WireRequestError("material.invalid_source")
    expected = data.get("expected_sha256")
    if expected is not None and payload.identity.sha256 != expected:
        raise WireRequestError("material.digest_mismatch")
    return operations.parse(ParseOfficesRequest(payload, day), context=context)


def _compare(data, materials, context):
    candidate = materials.release(data["candidate_ref"])
    baseline = materials.release(data["baseline_ref"]) if "baseline_ref" in data else None
    return operations.compare(CompareReleaseRequest(candidate, baseline), context=context)


def _project_parse(result):
    v = result.value
    if v is None:
        return None
    return {"as_of": v.as_of.isoformat(), "row_count": v.row_count,
            "dataset_sha256": v.dataset_version.identity.sha256,
            "representation_sha256": v.representation.identity.sha256}


def _project_compare(result):
    v = result.value
    if v is None:
        return None
    return {"state": v.state, "reason": v.reason, "changed_count": v.changed_count,
            "layers": asdict(v.layers), "coverage": asdict(v.coverage) if v.coverage else None}


PARSE_CODEC = ReadOnlyWireCodec(PARSE_CONTRACT, _parse, _project_parse)
COMPARE_CODEC = ReadOnlyWireCodec(COMPARE_CONTRACT, _compare, _project_compare)
