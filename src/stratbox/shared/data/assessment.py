"""Actual value assessments and pinned analytical calculation evidence.

These records describe observed values. Port guarantees remain requirements
and cannot create an assessment or establish analytical coverage.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from decimal import Decimal
from datetime import date

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.identifiers import safe_token


@dataclass(frozen=True, slots=True)
class ProcessingFinding:
    code: str
    severity: str
    count: int
    description: str
    examples: tuple[str, ...] = ()
    scope_id: str | None = None

    def __post_init__(self):
        safe_token(self.code)
        if (self.severity not in {"information", "warning", "error"}
                or type(self.count) is not int or self.count < 1
                or not isinstance(self.description, str) or not self.description
                or not isinstance(self.examples, tuple) or len(self.examples) > 16
                or any(not isinstance(value, str) for value in self.examples)):
            raise ValueError("assessment.finding_invalid")
        if self.scope_id is not None and (not isinstance(self.scope_id, str) or not self.scope_id):
            raise ValueError("assessment.finding_scope_invalid")


@dataclass(frozen=True, slots=True)
class CoverageCoordinate:
    """An exact observation grain; axis marginals are a separate projection."""
    subject_namespace: str
    subject_id: str
    metric_id: str
    period_kind: str
    period: str
    perimeter: str
    dimensions: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if (any(not isinstance(value, str) or not value for value in (self.subject_namespace,
                self.subject_id, self.metric_id, self.period, self.perimeter))
                or self.period_kind not in {"as_of", "capture", "interval"}
                or not isinstance(self.dimensions, tuple)
                or any(not isinstance(pair, tuple) or len(pair) != 2 or any(not isinstance(value, str) for value in pair)
                       for pair in self.dimensions)
                or len({key for key, _ in self.dimensions}) != len(self.dimensions)):
            raise ValueError("assessment.coordinate_invalid")
        periods = self.period.split("/") if self.period_kind == "interval" else [self.period]
        try:
            dates = [date.fromisoformat(value) for value in periods]
            if (len(dates) != (2 if self.period_kind == "interval" else 1)
                    or any(value.isoformat() != token for value, token in zip(dates, periods))
                    or dates[0] > dates[-1]):
                raise ValueError
        except ValueError:
            raise ValueError("assessment.coordinate_period_invalid") from None

    @property
    def identity(self):
        return ByteIdentity.of(canonical_manifest_bytes({"subject": (self.subject_namespace, self.subject_id),
            "metric": self.metric_id, "period_kind": self.period_kind, "period": self.period,
            "dimensions": tuple(sorted(self.dimensions)), "perimeter": self.perimeter})).sha256


def observation_coordinate(item):
    period = item.period.as_of.isoformat() if item.period.as_of is not None else f"{item.period.start}/{item.period.end}"
    return CoverageCoordinate(item.subject.namespace, item.subject.id, item.metric.id, item.period.kind,
        period, item.perimeter, tuple(sorted(item.dimensions)))


@dataclass(frozen=True, slots=True)
class CoverageAssessment:
    scope_id: str
    members: tuple[str, ...]
    membership_closed: bool
    observed: tuple[str, ...]
    expected: tuple[str, ...] | None = None
    source_identity: ByteIdentity | None = None
    selection: tuple[str, int, int, int, int] | None = None
    expected_coordinates: tuple[CoverageCoordinate, ...] | None = None

    def __post_init__(self):
        if not isinstance(self.scope_id, str) or not self.scope_id or type(self.membership_closed) is not bool:
            raise ValueError("assessment.coverage_invalid")
        for values in (self.members, self.observed, self.expected):
            if values is not None and (not isinstance(values, tuple) or len(values) != len(set(values))
                    or any(not isinstance(value, str) or not value for value in values)):
                raise ValueError("assessment.coverage_invalid")
        if self.source_identity is not None and not isinstance(self.source_identity, ByteIdentity):
            raise ValueError("assessment.source_identity_invalid")
        if self.selection is not None and (not isinstance(self.selection, tuple) or len(self.selection) != 5
                or not isinstance(self.selection[0], str)
                or any(type(value) is not int or value < 1 for value in self.selection[1:])):
            raise ValueError("assessment.selection_invalid")
        if self.expected_coordinates is not None and (not isinstance(self.expected_coordinates, tuple)
                or any(not isinstance(value, CoverageCoordinate) for value in self.expected_coordinates)
                or len({value.identity for value in self.expected_coordinates}) != len(self.expected_coordinates)):
            raise ValueError("assessment.expected_coordinates_invalid")

    @property
    def axis_status(self):
        if self.expected is None:
            return "unknown"
        return "complete" if self.membership_closed and set(self.expected) <= set(self.observed) else "partial"

    @property
    def status(self):
        if self.expected_coordinates is None:
            return "partial" if self.axis_status == "partial" else "unknown"
        expected = {value.identity for value in self.expected_coordinates}
        return "complete" if (self.membership_closed and expected <= set(self.members)
            and self.axis_status != "partial") else "partial"

    @property
    def facts(self):
        return frozenset({"coverage." + self.status, "axis_coverage." + self.axis_status,
            *(('membership.closed',) if self.membership_closed else ()),
            *(("source.selected",) if self.selection is not None else ())})


@dataclass(frozen=True, slots=True)
class CalculationEvidence:
    rule_id: str
    rule_revision: str
    rule_fingerprint: str
    inputs: tuple[tuple[str, ByteIdentity, str], ...]
    period_policy: str
    origin_policy: str
    release_policy: str
    rationale: str

    def __post_init__(self):
        safe_token(self.rule_id)
        if (not self.rule_revision or not self.rule_fingerprint or not self.rationale
                or not isinstance(self.inputs, tuple) or not self.inputs
                or any(not isinstance(item, tuple) or len(item) != 3 or not isinstance(item[0], str)
                       or not isinstance(item[1], ByteIdentity) or not isinstance(item[2], str) for item in self.inputs)):
            raise ValueError("assessment.calculation_evidence_invalid")


@dataclass(frozen=True, slots=True)
class ValueEvidence:
    qualifications: frozenset[str] = frozenset()
    coverage: CoverageAssessment | None = None
    findings: tuple[ProcessingFinding, ...] = ()
    calculations: tuple[CalculationEvidence, ...] = ()
    method_fingerprints: tuple[str, ...] = ()
    profile_fingerprints: tuple[str, ...] = ()
    reference_fingerprints: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.qualifications, frozenset):
            raise ValueError("assessment.qualifications_invalid")
        for item in self.qualifications:
            safe_token(item)
        if self.coverage is not None and not isinstance(self.coverage, CoverageAssessment):
            raise ValueError("assessment.coverage_invalid")
        for values, kind in ((self.findings, ProcessingFinding), (self.calculations, CalculationEvidence)):
            if not isinstance(values, tuple) or any(not isinstance(value, kind) for value in values):
                raise ValueError("assessment.evidence_invalid")
        for values in (self.method_fingerprints, self.profile_fingerprints, self.reference_fingerprints):
            if not isinstance(values, tuple) or any(not isinstance(value, str) or not value for value in values):
                raise ValueError("assessment.fingerprint_invalid")


def value_evidence(value) -> ValueEvidence:
    """Read actual evidence; absent assessments never inherit port claims."""
    evidence = getattr(value, "evidence", None)
    if isinstance(evidence, ValueEvidence):
        return evidence
    if isinstance(value, CoverageAssessment):
        return ValueEvidence(coverage=value)
    batch = getattr(value, "batch", None)
    evidence = getattr(batch, "evidence", None)
    if isinstance(evidence, ValueEvidence):
        return evidence
    observations = getattr(value, "observations", ())
    if isinstance(observations, tuple):
        # A published value status is evidence about that value. It establishes
        # neither validation nor completeness of a caller-supplied collection.
        statuses = frozenset(getattr(item, "value_status", "") for item in observations)
        statuses = frozenset(value for value in statuses if value)
        return ValueEvidence(statuses)
    return ValueEvidence()


def observation_scope(observations):
    """Describe the exact observed membership without inferring expectations."""
    observed, members = set(), []
    for item in observations:
        period = item.period.as_of.isoformat() if item.period.as_of else f"{item.period.start}/{item.period.end}"
        observed.update((f"subject:{item.subject.namespace}:{item.subject.id}", f"metric:{item.metric.id}", f"period:{period}"))
        members.append(observation_coordinate(item).identity)
    return tuple(members), tuple(sorted(observed))


def selected_evidence(evidence, observations):
    """Keep the original required scope while recording the selected members."""
    coverage = evidence.coverage
    if coverage is not None:
        members, observed = observation_scope(observations)
        selection_id = ByteIdentity.of(canonical_manifest_bytes({"members": members})).sha256[:16]
        coverage = replace(coverage, scope_id=coverage.scope_id + ".view." + selection_id,
            members=members, observed=observed)
    return replace(evidence, qualifications=evidence.qualifications | {"view.selected"}, coverage=coverage)


def assessment_value(value):
    if isinstance(value, ByteIdentity):
        return {"sha256": value.sha256, "size": value.size}
    if isinstance(value, (ProcessingFinding, CoverageCoordinate, CoverageAssessment, CalculationEvidence, ValueEvidence)):
        return {field.name: assessment_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, (tuple, frozenset)):
        values = sorted(value) if isinstance(value, frozenset) else value
        return [assessment_value(item) for item in values]
    if value is None or type(value) in {str, int, bool}:
        return value
    raise ValueError("assessment.encoding_invalid")


def assessment_from(kind, value):
    """Restore one fixed assessment vocabulary, never an import path."""
    classes = {item.__name__: item for item in (ProcessingFinding, CoverageCoordinate, CoverageAssessment, CalculationEvidence, ValueEvidence)}
    if kind not in classes or not isinstance(value, dict) or set(value) != {field.name for field in fields(classes[kind])}:
        raise ValueError("assessment.encoding_invalid")
    if kind == "ValueEvidence":
        return evidence_from(value)
    if kind == "ProcessingFinding":
        if not isinstance(value["examples"], list):
            raise ValueError("assessment.encoding_invalid")
        return ProcessingFinding(**{**value, "examples": tuple(value["examples"])})
    if kind == "CoverageCoordinate":
        if not isinstance(value["dimensions"], list):
            raise ValueError("assessment.encoding_invalid")
        return CoverageCoordinate(**{**value, "dimensions": tuple(tuple(pair) for pair in value["dimensions"])})
    if kind == "CoverageAssessment":
        data = dict(value)
        if (any(not isinstance(data[key], list) for key in ("members", "observed"))
                or data["expected"] is not None and not isinstance(data["expected"], list)
                or data["selection"] is not None and not isinstance(data["selection"], list)):
            raise ValueError("assessment.encoding_invalid")
        data["members"], data["observed"] = tuple(data["members"]), tuple(data["observed"])
        data["expected"] = None if data["expected"] is None else tuple(data["expected"])
        data["selection"] = None if data["selection"] is None else tuple(data["selection"])
        data["source_identity"] = None if data["source_identity"] is None else ByteIdentity(**data["source_identity"])
        if data["expected_coordinates"] is not None:
            if not isinstance(data["expected_coordinates"], list):
                raise ValueError("assessment.encoding_invalid")
            data["expected_coordinates"] = tuple(assessment_from("CoverageCoordinate", item) for item in data["expected_coordinates"])
        return CoverageAssessment(**data)
    if kind == "CalculationEvidence":
        if not isinstance(value["inputs"], list):
            raise ValueError("assessment.encoding_invalid")
        return CalculationEvidence(**{**value,
            "inputs": tuple((role, ByteIdentity(**identity), release) for role, identity, release in value["inputs"])})
    raise ValueError("assessment.kind_unsupported")


def evidence_from(value):
    if not isinstance(value, dict) or set(value) != {field.name for field in fields(ValueEvidence)}:
        raise ValueError("assessment.evidence_encoding_invalid")
    if any(not isinstance(value[key], list) for key in ("qualifications", "findings", "calculations",
            "method_fingerprints", "profile_fingerprints", "reference_fingerprints")):
        raise ValueError("assessment.evidence_encoding_invalid")
    findings = tuple(assessment_from("ProcessingFinding", item) for item in value["findings"])
    calculations = tuple(assessment_from("CalculationEvidence", item) for item in value["calculations"])
    coverage = None if value["coverage"] is None else assessment_from("CoverageAssessment", value["coverage"])
    return ValueEvidence(frozenset(value["qualifications"]), coverage, findings, calculations,
        tuple(value["method_fingerprints"]), tuple(value["profile_fingerprints"]), tuple(value["reference_fingerprints"]))
