"""Read-only machine adapters owned by the daily offices domain."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date

from stratbox.core.execution.machine.contracts import ReadOnlyWireCodec, WireRequestError
from stratbox.shared.data import SourcePayload
from stratbox.shared.data.releases import CompareReleaseRequest
from . import operations
from .contracts import ParseOfficesRequest

REF = {"type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"}
DAY = {"type": "string", "pattern": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", "format": "date"}
DIGEST = {"type": "string", "pattern": r"^[0-9a-f]{64}$"}
INTEGER = {"type": "integer", "minimum": 0}
STRING = {"type": "string"}
LAYER = {"enum": ["same", "changed", "unavailable", "incompatible"]}
LAYERS = ("original", "structure", "facts", "method", "representation")
COVERAGE = {
    "common_observations": INTEGER, "baseline_observations": INTEGER,
    "candidate_observations": INTEGER, "common_subjects": INTEGER, "scope": STRING,
}


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


PARSE_CODEC = ReadOnlyWireCodec(
    "cbr.offices.parse", 1,
    {"source_ref": REF, "expected_sha256": DIGEST, "capture_date": DAY},
    ("source_ref", "capture_date"),
    {"as_of": DAY, "row_count": INTEGER,
     "dataset_sha256": DIGEST, "representation_sha256": DIGEST},
    _parse, _project_parse,
)
COMPARE_CODEC = ReadOnlyWireCodec(
    "cbr.offices.compare", 2,
    {"candidate_ref": REF, "baseline_ref": REF}, ("candidate_ref",),
    {"state": STRING, "reason": STRING, "changed_count": INTEGER,
     "layers": {"type": "object", "additionalProperties": False,
                "properties": dict.fromkeys(LAYERS, LAYER), "required": list(LAYERS)},
     "coverage": {"anyOf": [{"type": "object", "additionalProperties": False,
                             "properties": COVERAGE, "required": list(COVERAGE)},
                            {"type": "null"}]}},
    _compare, _project_compare,
)
