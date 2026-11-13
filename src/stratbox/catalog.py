"""Curated descriptions and wire calls for a small read-only operation set."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from importlib import import_module
import json
import re
from typing import Protocol

from stratbox.base.filestore import FileStore
from stratbox.data import SourcePayload
from stratbox.data.releases import CompareReleaseRequest, ParsedRelease
from stratbox.execution import ExecutionContext, OperationDefinition, OperationResult

_DECLARATIONS = {
    "macrobanks.cbr_offices.operations": "ACQUIRE PARSE CAPTURE READ COMPARE",
    "macrobanks.cbr_offices_reg.operations": "DISCOVER ACQUIRE PARSE CAPTURE READ COMPARE",
    "macrobanks.cbr_file_collector.operations": "DISCOVER COLLECT ARCHIVE",
    "macrobanks.cbr_forms.operations": "SELECT ACQUIRE PARSE BUILD VIEWS RENDER",
    "macrobanks.cbr_industries.operations": "DISCOVER ACQUIRE PARSE BUILD_STREAM CALCULATE_APK PIVOT RENDER_PIVOTS RENDER_INDUSTRY",
    "macrobanks.cbr_industries.issuance_0104.operations": "DISCOVER ACQUIRE PARSE BUILD_STREAM CALCULATE_APK PIVOT RENDER_INDUSTRY",
    "macrobanks.cbr_sors_restoration.api": "READ LOAD RESTORE CROSSWALK PIVOT RENDER",
    "macrobanks.escrow.operations": "DISCOVER ACQUIRE PARSE HISTORY VIEWS RENDER",
    "macrobanks.frg.api": "SCAN PLAN APPLY ARCHIVE STREAM_ARCHIVE",
    "organizations.fns_sme.operations": "DISCOVER ACQUIRE PARSE CAPTURE READ COMPARE",
    "organizations.fns_1yur.operations": "DISCOVER ACQUIRE PARSE CAPTURE READ COMPARE",
    "notifications.operations": "PREPARE DELIVER QUALIFY RECONCILE",
}
_REF = r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}"
_DATE = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
_HASH = r"[0-9a-f]{64}"
_MAX_JSON = 16_384
_JSON_STRUCTURE = re.compile(r'"(?:[^"\\]|\\.)*"|[{}\[\]]', re.DOTALL)
_SCHEMA = "https://json-schema.org/draft/2020-12/schema"
_STRING = {"type": "string"}
_REF_FIELD = {**_STRING, "pattern": f"^{_REF}$"}
_DATE_FIELD = {**_STRING, "pattern": f"^{_DATE}$", "format": "date"}
_DIGEST_FIELD = {**_STRING, "pattern": f"^{_HASH}$"}
_INTEGER = {"type": "integer", "minimum": 0}
_INPUTS = {
    "cbr.offices.parse": (
        {"source_ref": _REF_FIELD, "expected_sha256": _DIGEST_FIELD, "capture_date": _DATE_FIELD},
        ("source_ref", "capture_date"),
    ),
    "cbr.offices.compare": (
        {"candidate_ref": _REF_FIELD, "baseline_ref": _REF_FIELD}, ("candidate_ref",)
    ),
    "frg.plan_cleanup": (
        {"directory_ref": _REF_FIELD, "delete_others": {"type": "boolean"}}, ("directory_ref",)
    ),
}
_OUTPUTS = {
    "cbr.offices.parse": {
        "as_of": _DATE_FIELD, "row_count": _INTEGER,
        "dataset_sha256": _DIGEST_FIELD, "representation_sha256": _DIGEST_FIELD,
    },
    "cbr.offices.compare": {"state": _STRING, "reason": _STRING, "changed_count": _INTEGER},
    "frg.plan_cleanup": {"plan_sha256": _DIGEST_FIELD, "action_count": _INTEGER},
}


def _object(properties, required):
    return {"type": "object", "additionalProperties": False, "properties": properties,
            "required": list(required)}


def _name(kind: type) -> str:
    return f"{kind.__module__}.{kind.__qualname__}"


@dataclass(frozen=True, slots=True)
class OperationCatalog:
    definitions: tuple[OperationDefinition, ...]

    def __post_init__(self) -> None:
        identities = {(item.operation_id, item.contract_version) for item in self.definitions}
        if len(identities) != len(self.definitions):
            raise ValueError("Duplicate operation contract")

    def get(self, operation_id: str, contract_version: int) -> OperationDefinition:
        for item in self.definitions:
            if (item.operation_id, item.contract_version) == (operation_id, contract_version):
                return item
        raise WireRequestError("operation.contract_unavailable")

    def describe(self) -> tuple[dict, ...]:
        descriptions = []
        for item in sorted(self.definitions, key=lambda op: (op.operation_id, op.contract_version)):
            required = sorted(item.required_capabilities)
            optional = sorted(item.optional_capabilities)
            descriptions.append({
                "operation_id": item.operation_id,
                "contract_version": item.contract_version,
                "method_version": item.method_version,
                "purpose": item.operation_id.rsplit(".", 1)[-1].replace("_", " "),
                "python_request": _name(item.request_type),
                "machine_input_roles": sorted(_INPUTS[item.operation_id][0]) if item.operation_id in _INPUTS else [],
                "machine_result_fields": sorted(_OUTPUTS.get(item.operation_id, {})),
                "python_result": " | ".join(
                    _name(kind) for kind in item.value_type
                ) if isinstance(item.value_type, tuple) else _name(item.value_type),
                "capabilities": [
                    {"role": role, "required": role in required,
                     "version": item.capability(role).version,
                     "managed_guarantees": sorted(item.capability(role, managed=True).guarantees)}
                    for role in required + optional
                ],
                "effects": [asdict(effect) for effect in item.effects],
                "limits": asdict(item.limits) if item.limits else None,
                "partial_allowed": item.partial_allowed,
                "cancellation": "cooperative",
                "diagnostic_envelope": 2,
                "machine_read_only": item.operation_id in _INPUTS,
            })
        return tuple(descriptions)


def operation_catalog() -> OperationCatalog:
    declarations = []
    for path, names in _DECLARATIONS.items():
        module = import_module(f"stratbox.{path}")
        declarations.extend(getattr(module, name) for name in names.split())
    return OperationCatalog(tuple(declarations))


def wire_schemas(operation_id: str, contract_version: int) -> tuple[dict, dict]:
    """Return the request and response schemas for an explicitly enabled codec."""
    import copy

    op = operation_catalog().get(operation_id, contract_version)
    if operation_id not in _INPUTS:
        raise WireRequestError("operation.wire_unavailable")
    fields, required = _INPUTS[operation_id]
    identity = {"operation_id": {"const": operation_id}, "contract_version": {"const": contract_version}}
    request = {"$schema": _SCHEMA, **_object(
        {**identity, "input": _object(fields, required)}, (*identity, "input")
    )}
    values = _OUTPUTS[operation_id]
    response_fields = {
        **identity,
        "method_version": {"const": op.method_version},
        "outcome": {"enum": ["succeeded", "partial", "failed", "cancelled", "unknown"]},
        "value": {"anyOf": [_object(values, values), {"type": "null"}]},
        "diagnostics": {"type": "array", "items": _object(
            {"code": _STRING, "stage": _STRING, "component": _STRING, "retry_disposition": _STRING},
            ("code", "stage", "component", "retry_disposition"),
        )},
    }
    return copy.deepcopy((request, {"$schema": _SCHEMA, **_object(response_fields, response_fields)}))


@dataclass(frozen=True, slots=True)
class DirectoryMaterial:
    directory: str
    store: FileStore


class MaterialResolver(Protocol):
    """Resolve opaque references under application-owned read permissions."""

    def source(self, reference: str) -> SourcePayload: ...
    def release(self, reference: str) -> ParsedRelease: ...
    def directory(self, reference: str) -> DirectoryMaterial: ...


class WireRequestError(ValueError):
    @property
    def code(self) -> str:
        return self.args[0]


def _unique(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise WireRequestError("request.duplicate_field")
        fields[key] = value
    return fields


def _shape(value, allowed, required):
    if not isinstance(value, dict) or not set(required) <= value.keys() <= set(allowed):
        raise WireRequestError("request.invalid_fields")


def _input(raw: bytes) -> tuple[OperationDefinition, dict]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= _MAX_JSON:
        raise WireRequestError("request.size_limit")
    try:
        encoded = raw.decode("utf-8")
        depth = 0
        for match in _JSON_STRUCTURE.finditer(encoded):
            token = match[0]
            if token in ("{", "["):
                depth += 1
                if depth > 2:
                    raise WireRequestError("request.depth_limit")
            elif token in ("}", "]"):
                depth -= 1
        body = json.loads(encoded, object_pairs_hook=_unique)
    except WireRequestError:
        raise
    except (ValueError, RecursionError):
        raise WireRequestError("request.invalid_json") from None
    fields = {"operation_id", "contract_version", "input"}
    _shape(body, fields, fields)
    operation_id, version = body["operation_id"], body["contract_version"]
    if not isinstance(operation_id, str) or type(version) is not int:
        raise WireRequestError("request.invalid_type")
    op = operation_catalog().get(operation_id, version)
    if operation_id not in _INPUTS:
        raise WireRequestError("operation.wire_unavailable")
    fields, required = _INPUTS[operation_id]
    data = body["input"]
    _shape(data, fields, required)
    for name, value in data.items():
        schema = fields[name]
        if schema["type"] == "boolean":
            if type(value) is not bool:
                raise WireRequestError("request.invalid_type")
        elif not isinstance(value, str) or not re.fullmatch(schema["pattern"], value, re.ASCII):
            raise WireRequestError("request.invalid_value")
    return op, data


def _execute(op, data, materials, context):
    from stratbox.macrobanks import cbr_offices, frg

    if op.operation_id == "cbr.offices.parse":
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
        return cbr_offices.parse(cbr_offices.ParseOfficesRequest(payload, day), context=context)
    if op.operation_id == "cbr.offices.compare":
        candidate = materials.release(data["candidate_ref"])
        baseline = materials.release(data["baseline_ref"]) if "baseline_ref" in data else None
        return cbr_offices.compare(CompareReleaseRequest(candidate, baseline), context=context)
    directory = materials.directory(data["directory_ref"])
    if not isinstance(directory, DirectoryMaterial):
        raise WireRequestError("material.invalid_directory")
    return frg.plan_cleanup(
        frg.PlanCleanupRequest(directory.directory, data.get("delete_others", False)),
        store=directory.store, context=context,
    )


def _project(result: OperationResult) -> dict | None:
    value = result.value
    if value is None:
        return None
    if result.operation_id == "cbr.offices.parse":
        return {
            "as_of": value.as_of.isoformat(), "row_count": value.row_count,
            "dataset_sha256": value.dataset_version.identity.sha256,
            "representation_sha256": value.representation.identity.sha256,
        }
    if result.operation_id == "cbr.offices.compare":
        return {"state": value.state, "reason": value.reason, "changed_count": value.changed_count}
    return {"plan_sha256": value.identity.sha256, "action_count": len(value.actions)}


def invoke_read_only(
    raw: bytes, *, materials: MaterialResolver, context: ExecutionContext | None = None
) -> bytes:
    """Decode a curated request, call its domain function and return a safe projection."""
    op, data = _input(raw)
    try:
        result = _execute(op, data, materials, context)
    except WireRequestError:
        raise
    except Exception:
        raise WireRequestError("material.unavailable") from None
    return json.dumps({
        "operation_id": op.operation_id,
        "contract_version": op.contract_version,
        "method_version": op.method_version,
        "outcome": result.outcome,
        "value": _project(result),
        "diagnostics": [
            {"code": item.code, "stage": item.stage, "component": item.component,
             "retry_disposition": item.retry_disposition}
            for item in result.diagnostics
        ],
    }, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
