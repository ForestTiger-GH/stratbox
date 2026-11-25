"""A deterministic supplied semantic profile interprets one exact workbook."""
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import quote

from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.observations import Observation, ObservationBatch
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from ..publications.catalog import source
from .contracts import CellBinding, SemanticFlake, SemanticProfile

_MISSING = {"blank", "dash", "missing", "not_applicable", "withheld"}


def profile_identity(profile: SemanticProfile) -> ByteIdentity:
    return ByteIdentity.of(canonical_manifest_bytes(asdict(profile)))


def _validate_binding(binding):
    if (not isinstance(binding, CellBinding) or not binding.sheet or type(binding.row) is not int
            or type(binding.column) is not int or binding.row < 1 or binding.column < 1
            or not binding.subject.namespace or not binding.subject.id or not binding.perimeter
            or binding.metric.quantity_kind is None or binding.metric.definition_version is None
            or binding.metric.scale is None or binding.period.kind == "capture"
            or binding.decimal_separator not in {".", ","}
            or not isinstance(binding.missing_tokens, tuple)
            or any(not isinstance(p, tuple) or len(p) != 2 or type(p[0]) is not str or p[1] not in _MISSING
                   for p in binding.missing_tokens)
            or len({p[0] for p in binding.missing_tokens}) != len(binding.missing_tokens)):
        raise ValueError("frg.profile.semantics_required")
    if (binding.metric.quantity_kind == "stock" and binding.period.kind != "as_of"
            or binding.metric.quantity_kind == "flow" and binding.period.kind != "interval"):
        raise ValueError("frg.profile.period_quantity_mismatch")
    if (not isinstance(binding.dimensions, tuple)
            or any(not isinstance(p, tuple) or len(p) != 2 or any(type(x) is not str for x in p) for p in binding.dimensions)
            or len({p[0] for p in binding.dimensions}) != len(binding.dimensions)
            or "source_series" in dict(binding.dimensions)):
        raise ValueError("frg.profile.dimensions_invalid")


def _value(cell, binding):
    if cell is None or cell.value is None:
        if cell is not None and cell.formula is not None:
            raise ValueError("frg.flake.formula_cache_required")
        return None, "blank", None
    value = cell.value
    raw = cell.raw_token if cell.raw_token is not None else str(value)
    if type(value) is str:
        raw = value
        if value in dict(binding.missing_tokens):
            return None, dict(binding.missing_tokens)[value], raw
        numeric = value.replace("\u00a0", "").replace("\u202f", "").strip()
        if binding.decimal_separator == ",":
            if "." in numeric:
                raise ValueError("frg.flake.numeric_value_invalid")
            numeric = numeric.replace(",", ".")
        if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?", numeric):
            raise ValueError("frg.flake.numeric_value_invalid")
        try:
            value = Decimal(numeric)
        except InvalidOperation:
            raise ValueError("frg.flake.numeric_value_invalid") from None
    if type(value) not in {int, Decimal} or isinstance(value, Decimal) and not value.is_finite():
        raise ValueError("frg.flake.numeric_value_invalid")
    return value, "reported", raw


def build_flake(request):
    extract, profile = request.extract, request.profile
    source(extract.series_id)
    extract.__post_init__()
    if (not isinstance(profile, SemanticProfile) or profile.source_id != extract.series_id
            or profile.original_identity != extract.source_identity or not profile.profile_id
            or type(profile.version) is not int or profile.version < 1
            or not isinstance(profile.bindings, tuple) or not profile.bindings):
        raise ValueError("frg.profile.original_binding_mismatch")
    if profile.layout_identity is not None and (
            not isinstance(profile.layout_identity, ByteIdentity) or not profile.reviewed_originals
            or not isinstance(profile.reviewed_originals, tuple)
            or any(not isinstance(item, ByteIdentity) for item in profile.reviewed_originals)
            or not isinstance(profile.review_qualification, str) or not profile.review_qualification):
        raise ValueError("frg.profile.layout_evidence_required")
    if profile.layout_identity is None and (profile.reviewed_originals or profile.review_qualification is not None):
        raise ValueError("frg.profile.layout_evidence_required")
    physical = {sheet.name: sheet for sheet in extract.sheets}
    indexes = {name: {(cell.row, cell.column): cell for cell in sheet.cells} for name, sheet in physical.items()}
    positions, semantics, observations = set(), set(), []
    for binding in profile.bindings:
        _validate_binding(binding)
        sheet = physical.get(binding.sheet)
        if sheet is None or binding.row > sheet.rows or binding.column > sheet.columns:
            raise ValueError("frg.profile.coordinate_unavailable")
        position = binding.sheet, binding.row, binding.column
        if position in positions:
            raise ValueError("frg.profile.duplicate_cell")
        positions.add(position)
        dimensions = (*binding.dimensions, ("source_series", extract.series_id))
        key = binding.subject, binding.metric, binding.period, dimensions, binding.perimeter
        if key in semantics:
            raise ValueError("frg.profile.duplicate_semantic_key")
        semantics.add(key)
        cell = indexes[binding.sheet].get((binding.row, binding.column))
        value, status, raw = _value(cell, binding)
        evidence = (f"sha256:{extract.source_identity.sha256}#issue={quote(extract.issue_id, safe='')}&asset={quote(extract.asset_id, safe='')}"
                    f"&sheet={quote(binding.sheet, safe='')}&row={binding.row}&column={binding.column}")
        observations.append(Observation(binding.subject, binding.metric, binding.period, dimensions,
                                        binding.perimeter, value, status, evidence, raw))
    profile_digest = profile_identity(profile)
    lineage = (*extract.lineage, UsedInputReceipt("extract", extract.identity, "application/vnd.stratbox.dataset+json", "inline", extract.series_id),
               UsedInputReceipt("semantic_profile", profile_digest, "application/json", "inline", profile.profile_id))
    batch = ObservationBatch(extract.series_id + ".flake", 1, extract.source_identity.sha256, tuple(observations), lineage,
        (SourceUse(SourceCoordinate(extract.series_id, source_group_id="reported_metrics", issue_id=extract.issue_id,
            asset_id=extract.asset_id, material_identity=extract.source_identity,
            semantic_profile_edition=profile.profile_id + ":" + str(profile.version)), "extract", "byte_bound_profile_validated"),))
    observation_snapshot(batch)
    qualifications = ("caller_supplied_byte_bound_semantics", *extract.qualifications)
    if profile.layout_identity is not None:
        qualifications += ("externally_reviewed_layout", profile.review_qualification)
    return SemanticFlake(extract.series_id, extract.issue_id, extract.asset_id, extract.source_identity,
                         extract.identity, profile.profile_id, profile.version, profile_digest, batch,
                         qualifications)
