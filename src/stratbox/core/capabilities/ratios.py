"""Ratios admitted by an explicit analytical pair and pinned input basis."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_EVEN
from collections.abc import Mapping

from stratbox.core.execution.contracts import OperationFailure
from stratbox.shared.data.assessment import CalculationEvidence, CoverageAssessment, ValueEvidence, value_evidence, observation_coordinate
from stratbox.shared.data.observations import MetricRef, ObservationBatch
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes


def _fail(code):
    raise OperationFailure("calculation." + code)


def _operand(batch, declared):
    if not isinstance(declared, Mapping) or not isinstance(batch, ObservationBatch):
        _fail("pair_contract_invalid")
    required = {"dataset_id", "metric_id", "definition_version", "unit", "quantity_kind", "scale"}
    if not required <= declared.keys() or any(declared[name] is None for name in required):
        _fail("pair_semantics_required")
    if batch.dataset_id != declared["dataset_id"]:
        _fail("pair_dataset_mismatch")
    if declared.get("release_id") is not None and batch.release_id != declared["release_id"]:
        _fail("pair_revision_mismatch")
    try:
        scale = Decimal(str(declared["scale"]))
        if not scale.is_finite() or scale <= 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        _fail("pair_contract_invalid")
    for item in batch.observations:
        metric = item.metric
        if (metric.id, metric.definition_version, metric.unit, metric.quantity_kind, metric.scale) != (
            declared["metric_id"], declared["definition_version"], declared["unit"], declared["quantity_kind"], scale
        ):
            _fail("pair_metric_mismatch")
        if declared.get("perimeter") is not None and item.perimeter != declared["perimeter"]:
            _fail("pair_perimeter_mismatch")
    if not batch.lineage:
        _fail("pair_origin_unavailable")
    return scale


def ratio_evaluate(request, invocation):
    pair = request.get("pair")
    if not isinstance(pair, Mapping):
        _fail("pair_required")
    required = {"id", "revision", "rationale", "numerator", "denominator", "result", "period_policy", "origin_policy", "release_policy"}
    if not required <= pair.keys() or any(not isinstance(pair[name], str) or not pair[name]
            for name in ("id", "revision", "rationale")):
        _fail("pair_contract_invalid")
    numerator, denominator = request["numerator"], request["denominator"]
    numerator_scale, denominator_scale = _operand(numerator, pair["numerator"]), _operand(denominator, pair["denominator"])
    period_policy, origin_policy, release_policy = pair["period_policy"], pair["origin_policy"], pair["release_policy"]
    if period_policy not in {"equal", "same_end"} or origin_policy not in {"common_material", "same_source", "declared_sources"} or release_policy not in {"same", "pinned"}:
        _fail("pair_policy_invalid")
    if release_policy == "same" and numerator.release_id != denominator.release_id:
        _fail("pair_revision_mismatch")
    if release_policy == "pinned" and any(not pair[role].get("release_id") for role in ("numerator", "denominator")):
        _fail("pair_revision_required")
    if origin_policy == "common_material" and not (
        {item.identity for item in numerator.lineage} & {item.identity for item in denominator.lineage}
    ):
        _fail("pair_origin_mismatch")
    if origin_policy == "same_source":
        sources = [{use.coordinate.source_id for use in batch.source_uses if use.coordinate.source_id}
                   for batch in (numerator, denominator)]
        if not sources[0] or sources[0] != sources[1]:
            _fail("pair_origin_mismatch")
    def key(item):
        period = item.period if period_policy == "equal" else (item.period.as_of or item.period.end)
        return item.subject, period, tuple(sorted(item.dimensions)), item.perimeter
    def indexed(batch):
        values = {key(item): item for item in batch.observations}
        if len(values) != len(batch.observations):
            _fail("duplicate_key")
        return values
    left, right = indexed(numerator), indexed(denominator)
    if not left or left.keys() != right.keys():
        _fail("coverage_mismatch")
    result = pair["result"]
    if not isinstance(result, Mapping) or not {"metric_id", "unit", "quantity_kind", "scale"} <= result.keys():
        _fail("pair_result_semantics_required")
    try:
        precision, multiplier = pair.get("precision", 28), Decimal(str(pair.get("multiplier", 1)))
        result_scale = Decimal(str(result["scale"]))
        if type(precision) is not int or not 1 <= precision <= 100_000 or not multiplier.is_finite() or not result_scale.is_finite() or result_scale <= 0:
            raise ValueError
        metric = MetricRef(result["metric_id"], result["unit"], result["quantity_kind"], pair["revision"], result_scale)
    except (ValueError, TypeError, InvalidOperation):
        _fail("pair_contract_invalid")
    rows = []
    with localcontext() as arithmetic:
        arithmetic.prec, arithmetic.rounding = precision, ROUND_HALF_EVEN
        for basis, item in left.items():
            invocation.check_cancelled()
            other = right[basis]
            if type(item.value) not in {int, Decimal} or type(other.value) not in {int, Decimal}:
                _fail("value_unavailable")
            if Decimal(other.value) == 0:
                _fail("zero_denominator")
            value = (Decimal(item.value) * numerator_scale) / (Decimal(other.value) * denominator_scale) * multiplier / result_scale
            if not value.is_finite():
                _fail("nonfinite_result")
            rows.append(replace(item, metric=metric, value=value, value_status="derived", raw_token=None,
                evidence_ref=f"ratio:{pair['id']}:{pair['revision']}:{item.evidence_ref}:{other.evidence_ref}"))
    input_evidence = value_evidence(numerator), value_evidence(denominator)
    rule_fingerprint = ByteIdentity.of(canonical_manifest_bytes(pair)).sha256
    receipts = tuple((role, observation_snapshot(batch).identity, batch.release_id)
        for role, batch in (("numerator", numerator), ("denominator", denominator)))
    evidence = CalculationEvidence(pair["id"], pair["revision"], rule_fingerprint, receipts,
        period_policy, origin_policy, release_policy, pair["rationale"])
    expected = None
    if all(item.coverage is not None and item.coverage.expected is not None for item in input_evidence):
        expected = tuple(sorted({f"metric:{metric.id}" if value.startswith("metric:") else value
            for item in input_evidence for value in item.coverage.expected}))
    observed = tuple(sorted({value for item in rows for value in (
        f"subject:{item.subject.namespace}:{item.subject.id}", f"metric:{item.metric.id}",
        f"period:{item.period.as_of.isoformat() if item.period.as_of else str(item.period.start) + '/' + str(item.period.end)}")}))
    membership = tuple(observation_coordinate(item).identity for item in rows)
    expected_coordinates = None
    if all(item.coverage is not None and item.coverage.expected_coordinates is not None for item in input_evidence):
        basis = (*input_evidence[0].coverage.expected_coordinates,
            *(observation_coordinate(item) for item in numerator.observations))
        def coordinate_key(coordinate):
            period = ((coordinate.period_kind, coordinate.period) if period_policy == "equal"
                else coordinate.period.rsplit("/", 1)[-1])
            return (coordinate.subject_namespace, coordinate.subject_id, period,
                tuple(sorted(coordinate.dimensions)), coordinate.perimeter)
        numerator_basis = {coordinate_key(coordinate): coordinate for coordinate in basis}
        mapped = {coordinate.identity: replace(coordinate, metric_id=metric.id)
            for coordinate in input_evidence[0].coverage.expected_coordinates}
        supported = True
        for coordinate in input_evidence[1].coverage.expected_coordinates:
            corresponding = numerator_basis.get(coordinate_key(coordinate))
            if corresponding is None:
                if period_policy == "equal":
                    corresponding = coordinate
                else:
                    supported = False
                    break
            mapped[corresponding.identity] = replace(corresponding, metric_id=metric.id)
        if supported:
            expected_coordinates = tuple({value.identity: value for value in mapped.values()}.values())
    dataset_id = request.get("dataset_id") or numerator.dataset_id + ".ratio"
    release = ByteIdentity.of(canonical_manifest_bytes({"rule": rule_fingerprint,
        "inputs": [(role, identity.sha256, revision) for role, identity, revision in receipts]})).sha256
    coverage = CoverageAssessment(dataset_id + ":" + release, membership, True, observed, expected,
        expected_coordinates=expected_coordinates)
    admitted = dict(getattr(invocation.context, "binding_identities", ()))
    methods = tuple(sorted({*getattr(input_evidence[0], "method_fingerprints"), *getattr(input_evidence[1], "method_fingerprints"),
        *(value for key, value in admitted.items() if key == "method" or key.startswith(("method:", "implementation:")))}))
    actual_evidence = ValueEvidence(frozenset({"derived", "calculation.admitted",
        *("input.coverage." + item.coverage.status for item in input_evidence if item.coverage is not None),
        *("input." + item.value_status for batch in (numerator, denominator) for item in batch.observations)}),
        coverage, tuple(dict.fromkeys(finding for item in input_evidence for finding in item.findings)), (evidence,), methods,
        tuple(sorted({value for item in input_evidence for value in item.profile_fingerprints})),
        tuple(sorted({value for item in input_evidence for value in item.reference_fingerprints})))
    return ObservationBatch(dataset_id, 1, release, tuple(rows),
        tuple(dict.fromkeys((*numerator.lineage, *denominator.lineage))),
        tuple(dict.fromkeys((*numerator.source_uses, *denominator.source_uses))), actual_evidence)
