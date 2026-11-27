"""Exact publication candidates, reversible views and portable validation.

A history retains a bounded normalized evidence ledger independently of its
selected rows. Certificates describe checks; authority comes from accepted
validator evidence, never from constructing one of these portable records.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
import json

from .values import Assessment, SourceDataset, canonical_tree, fingerprint, immutable
from .selection import observation_key


HISTORY_SCHEMA = "stratbox.history.candidates.v1"


def _tokens(values, message, *, limit=1000000, empty=False):
    values = tuple(values)
    if (len(values) > limit or len(values) != len(set(values))
            or any(not isinstance(value, str) or (not empty and not value) for value in values)):
        raise ValueError(message)
    return values


def _bounded_size(value, limit, message):
    size = 0
    for chunk in json.JSONEncoder(ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).iterencode(canonical_tree(value)):
        size += len(chunk.encode("utf-8"))
        if size > limit:
            raise ValueError(message)
    return size


def dataset_content_identity(dataset):
    """Bind exact content, excluding native state and validation attachments."""
    if not isinstance(dataset, SourceDataset):
        raise TypeError("history.dataset_required")
    return fingerprint((dataset.source_id, dataset.issue_id, dataset.rows,
                        dataset.semantics, dataset.source_uses))


def history_value_identity(dataset):
    """Identify portable history meaning without optional parser acceleration.

    Execution may separately include native inputs in its exact work key. A
    history transformation consumes the explicit rows, evidence and scope.
    """
    return dataset.identity if dataset.native is None else fingerprint(replace(dataset, native=None))


@dataclass(frozen=True, slots=True)
class ValidationCertificate:
    dataset_identity: str
    rule_id: str
    method_identity: str
    build_identity: str
    source_id: str
    issue_id: str = ""
    material_identities: tuple[object, ...] = ()
    coordinates: tuple[str, ...] = ()
    assessment: Assessment = Assessment()
    evidence_reference: str | None = None
    row_identities: tuple[tuple[str, str], ...] = ()
    semantics_identity: str | None = None

    def __post_init__(self):
        for name in ("dataset_identity", "rule_id", "method_identity", "build_identity", "source_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or len(value) > 4096:
                raise ValueError("validation.certificate_binding_required")
        if not isinstance(self.assessment, Assessment):
            raise TypeError("validation.assessment_required")
        if self.semantics_identity is not None and (not isinstance(self.semantics_identity, str) or not self.semantics_identity):
            raise ValueError("validation.semantic_binding_invalid")
        coordinates = _tokens(self.coordinates, "validation.certificate_coordinates_invalid")
        coordinate_set = set(coordinates)
        object.__setattr__(self, "coordinates", coordinates)
        object.__setattr__(self, "material_identities", immutable(tuple(self.material_identities)))
        identities = tuple(tuple(pair) for pair in self.row_identities)
        if (len(identities) > 1000000 or any(len(pair) != 2 or any(not isinstance(v, str) or not v for v in pair) for pair in identities)
                or any(coordinate not in coordinate_set for coordinate, _ in identities)):
            raise ValueError("validation.certificate_rows_invalid")
        object.__setattr__(self, "row_identities", identities)

    @property
    def identity(self):
        return fingerprint(self)

    def binds(self, dataset):
        return (isinstance(dataset, SourceDataset) and self.source_id == dataset.source_id
                and self.issue_id == dataset.issue_id and self.dataset_identity == dataset_content_identity(dataset))


def make_validation_certificate(dataset, *, rule_id, method_identity, build_identity,
                                material_identities=(), assessment=None, evidence_reference=None):
    rows = tuple((observation_key(row), fingerprint(row)) for row in dataset.rows)
    return ValidationCertificate(dataset_content_identity(dataset), rule_id, method_identity,
        build_identity, dataset.source_id, dataset.issue_id, tuple(material_identities),
        tuple(dict.fromkeys(key for key, _ in rows)), dataset.assessment if assessment is None else assessment,
        evidence_reference, rows, fingerprint(stable_semantics(dataset)))


@dataclass(frozen=True, slots=True)
class PublicationRevision:
    """A qualified publication coordinate; chronology is supplied separately.

    ``occurrence_id`` distinguishes admitted A -> B -> A occurrences without
    duplicating A's row payload. A repeated poll alone supplies no new revision.
    """
    source_id: str
    issue_id: str
    revision_id: str
    asset_id: str = ""
    occurrence_id: str = ""

    def __post_init__(self):
        for name in ("source_id", "issue_id", "revision_id", "asset_id", "occurrence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) > 4096 or (name in {"source_id", "revision_id"} and not value):
                raise ValueError("history.revision_identity_invalid")

    @property
    def identity(self):
        return fingerprint((self.source_id, self.issue_id, self.asset_id,
                            self.revision_id, self.occurrence_id))


@dataclass(frozen=True, slots=True)
class HistoryLimits:
    max_members: int = 10000
    max_candidates: int = 1000000
    max_payload_bytes: int = 256 * 1024 * 1024
    max_witnesses: int = 1000000
    max_coordinates: int = 1000000
    max_encoded_bytes: int = 512 * 1024 * 1024

    def __post_init__(self):
        ceilings = {"max_members": 100000, "max_candidates": 10000000,
            "max_payload_bytes": 2 * 1024 * 1024 * 1024, "max_witnesses": 10000000,
            "max_coordinates": 10000000, "max_encoded_bytes": 4 * 1024 * 1024 * 1024}
        if any(type(getattr(self, name)) is not int or not 1 <= getattr(self, name) <= maximum
               for name, maximum in ceilings.items()):
            raise ValueError("history.limit_invalid")


@dataclass(frozen=True, slots=True)
class HistoryMember:
    content_identity: str
    source_id: str
    issue_id: str
    coordinates: tuple[str, ...]
    certificate_ids: tuple[str, ...] = ()
    asset_ids: tuple[str, ...] = ()
    revision: PublicationRevision | None = None
    assessment: Assessment = Assessment()

    def __post_init__(self):
        if (not isinstance(self.content_identity, str) or not self.content_identity
                or not isinstance(self.source_id, str) or not self.source_id or not isinstance(self.issue_id, str)
                or not isinstance(self.assessment, Assessment)):
            raise ValueError("history.member_invalid")
        for name in ("coordinates", "certificate_ids", "asset_ids"):
            object.__setattr__(self, name, _tokens(getattr(self, name), "history.member_invalid"))
        if self.revision is not None and (not isinstance(self.revision, PublicationRevision)
                or self.revision.source_id != self.source_id or self.revision.issue_id != self.issue_id
                or (self.revision.asset_id and self.revision.asset_id not in self.asset_ids)):
            raise ValueError("history.revision_member_mismatch")

    @property
    def identity(self):
        # Validation additions and view qualifications never change a candidate.
        return fingerprint((self.content_identity, self.source_id, self.issue_id,
            self.asset_ids, None if self.revision is None else self.revision.identity))


@dataclass(frozen=True, slots=True)
class HistoryRow:
    value: Mapping[str, object]
    identity: str = ""

    def __post_init__(self):
        if not isinstance(self.value, Mapping):
            raise ValueError("history.row_required")
        value = immutable(self.value)
        identity = fingerprint(value)
        if self.identity and self.identity != identity:
            raise ValueError("history.row_identity_mismatch")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "identity", identity)


@dataclass(frozen=True, slots=True)
class HistoryCandidate:
    member_id: str
    coordinate: str
    row_identity: str
    ordinal: int
    identity: str = ""

    def __post_init__(self):
        if (any(not isinstance(value, str) or not value for value in
                (self.member_id, self.coordinate, self.row_identity))
                or type(self.ordinal) is not int or self.ordinal < 0):
            raise ValueError("history.candidate_invalid")
        identity = fingerprint((self.member_id, self.coordinate, self.row_identity, self.ordinal))
        if self.identity and self.identity != identity:
            raise ValueError("history.candidate_identity_mismatch")
        object.__setattr__(self, "identity", identity)


@dataclass(frozen=True, slots=True)
class HistoryExpectation:
    """Expected issue/revision in its real source, asset and coordinate scope."""
    source_id: str
    issue_id: str
    asset_id: str = ""
    revision_id: str | None = None
    coordinates: tuple[str, ...] = ()

    def __post_init__(self):
        if (not isinstance(self.source_id, str) or not self.source_id
                or not isinstance(self.issue_id, str) or not isinstance(self.asset_id, str)
                or (self.revision_id is not None and (not isinstance(self.revision_id, str) or not self.revision_id))):
            raise ValueError("history.expectation_invalid")
        object.__setattr__(self, "coordinates", _tokens(self.coordinates, "history.expectation_invalid"))

    @property
    def identity(self):
        return fingerprint(self)

    def matches(self, member, coordinates):
        return (member.source_id == self.source_id and member.issue_id == self.issue_id
            and (not self.asset_id or self.asset_id in member.asset_ids)
            and (self.revision_id is None or member.revision is not None
                 and member.revision.revision_id == self.revision_id)
            and set(self.coordinates) <= coordinates)


@dataclass(frozen=True, slots=True)
class RevisionDecision:
    coordinate: str
    selected_candidates: tuple[str, ...]
    alternative_candidates: tuple[str, ...] = ()
    rule: str = "unique"
    representative: str | None = None
    policy_identity: str | None = None

    def __post_init__(self):
        if self.rule not in {"unique", "equal", "latest", "earliest", "unavailable"} or not self.coordinate:
            raise ValueError("history.revision_decision_invalid")
        for name in ("selected_candidates", "alternative_candidates"):
            object.__setattr__(self, name, _tokens(getattr(self, name), "history.revision_decision_invalid"))
        if (set(self.selected_candidates) & set(self.alternative_candidates)
                or (self.rule == "unavailable") != (not self.selected_candidates)
                or (self.selected_candidates and self.representative not in self.selected_candidates)
                or (not self.selected_candidates and self.representative is not None)):
            raise ValueError("history.revision_decision_invalid")


@dataclass(frozen=True, slots=True)
class HistoryMembership:
    # Required schema and normalized tables make old lossy envelopes fail closed.
    schema: str
    members: tuple[HistoryMember, ...]
    rows: tuple[HistoryRow, ...]
    candidates: tuple[HistoryCandidate, ...]
    active_scope: tuple[str, ...]
    revisions: tuple[RevisionDecision, ...]
    semantics_identity: str
    grain: tuple[str, ...] = ()
    expectations: tuple[HistoryExpectation, ...] = ()
    view_expectations: tuple[HistoryExpectation, ...] = ()
    eligible_candidates: tuple[str, ...] = ()
    policy_identity: str | None = None
    selection_identity: str | None = None
    selection_coverage: object | None = None
    selection_scopes: tuple[object, ...] = ()
    limits: HistoryLimits = HistoryLimits()

    def __post_init__(self):
        if self.schema != HISTORY_SCHEMA or not isinstance(self.semantics_identity, str) or not self.semantics_identity:
            raise ValueError("history.unsupported_schema")
        if not isinstance(self.limits, HistoryLimits):
            raise ValueError("history.typed_limits_required")
        for name, kind in (("members", HistoryMember), ("rows", HistoryRow), ("candidates", HistoryCandidate),
                           ("revisions", RevisionDecision), ("expectations", HistoryExpectation),
                           ("view_expectations", HistoryExpectation)):
            values = tuple(getattr(self, name))
            if any(not isinstance(value, kind) for value in values):
                raise ValueError("history.typed_ledger_required")
            object.__setattr__(self, name, values)
        for name in ("active_scope", "grain", "eligible_candidates"):
            object.__setattr__(self, name, _tokens(getattr(self, name), "history.scope_invalid", limit=10000000))
        limits = self.limits
        if len(self.members) > limits.max_members:
            raise ValueError("history.member_limit")
        if len(self.candidates) > limits.max_candidates:
            raise ValueError("history.candidate_limit")
        if len(self.active_scope) > limits.max_coordinates:
            raise ValueError("history.coordinate_limit")
        if sum(len(member.certificate_ids) for member in self.members) > limits.max_witnesses:
            raise ValueError("history.witness_limit")
        members, rows, candidates = ({value.identity: value for value in values}
                                    for values in (self.members, self.rows, self.candidates))
        if any(fingerprint(row.value) != row.identity for row in self.rows):
            raise ValueError("history.row_identity_mismatch")
        if any(len(index) != len(values) for index, values in
               ((members, self.members), (rows, self.rows), (candidates, self.candidates))):
            raise ValueError("history.duplicate_identity")
        active = set(self.active_scope)
        member_coordinates = {key: set(member.coordinates) for key, member in members.items()}
        ordinals = set()
        grouped = {}
        for candidate in self.candidates:
            member, row = members.get(candidate.member_id), rows.get(candidate.row_identity)
            if (member is None or row is None or candidate.coordinate not in active
                    or candidate.coordinate != observation_key(row.value, self.grain or None)
                    or observation_key(row.value) not in member_coordinates[candidate.member_id]):
                raise ValueError("history.candidate_binding_invalid")
            ordinal = candidate.member_id, candidate.ordinal
            if ordinal in ordinals:
                raise ValueError("history.candidate_ordinal_conflict")
            ordinals.add(ordinal)
            grouped.setdefault(candidate.coordinate, set()).add(candidate.identity)
        if set(rows) != {candidate.row_identity for candidate in self.candidates}:
            raise ValueError("history.unbound_row_payload")
        if not set(self.eligible_candidates) <= set(candidates):
            raise ValueError("history.eligible_candidate_invalid")
        decisions = {decision.coordinate: decision for decision in self.revisions}
        if len(decisions) != len(self.revisions) or set(decisions) != active:
            raise ValueError("history.decision_scope_invalid")
        for coordinate, decision in decisions.items():
            if (set(decision.selected_candidates) | set(decision.alternative_candidates)) != grouped.get(coordinate, set()):
                raise ValueError("history.decision_evidence_incomplete")
            if not set(decision.selected_candidates) <= set(self.eligible_candidates):
                raise ValueError("history.selected_candidate_ineligible")
        for expectations in (self.expectations, self.view_expectations):
            if len({expectation.identity for expectation in expectations}) != len(expectations):
                raise ValueError("history.duplicate_expectation")
        from .coverage import SelectedScopeCoverage
        scopes = tuple(self.selection_scopes)
        if (self.selection_coverage is not None and not isinstance(self.selection_coverage, SelectedScopeCoverage)
                or any(not isinstance(value, SelectedScopeCoverage) for value in scopes)):
            raise ValueError("history.selection_coverage_invalid")
        object.__setattr__(self, "selection_scopes", scopes)
        _bounded_size(self.rows, limits.max_payload_bytes, "history.payload_limit")
        _bounded_size((self.members, self.rows, self.candidates, self.active_scope, self.revisions,
            self.semantics_identity, self.grain, self.expectations, self.view_expectations,
            self.eligible_candidates, self.policy_identity, self.selection_identity,
            self.selection_coverage, self.selection_scopes, self.limits), limits.max_encoded_bytes, "history.encoded_limit")

    @property
    def all_expectations(self):
        return tuple({value.identity: value for value in (*self.expectations, *self.view_expectations)}.values())

    @property
    def expected_issues(self):
        return tuple(dict.fromkeys(item.issue_id for item in self.all_expectations))

    @property
    def missing_expectations(self):
        members = {member.identity: member for member in self.members}
        eligible = set(self.eligible_candidates)
        observed = {}
        for member in self.members:
            if not member.coordinates:
                observed[member.identity] = set()
        for candidate in self.candidates:
            if candidate.identity in eligible:
                observed.setdefault(candidate.member_id, set()).add(candidate.coordinate)
        return tuple(item for item in self.all_expectations
            if not any(item.matches(members[key], coordinates) for key, coordinates in observed.items()))

    @property
    def missing_issues(self):
        return tuple(dict.fromkeys(item.issue_id for item in self.missing_expectations))

    @property
    def missing_coordinates(self):
        return tuple(decision.coordinate for decision in self.revisions if not decision.selected_candidates)

    @property
    def complete(self):
        return not self.missing_expectations and not self.missing_coordinates


@dataclass(frozen=True, slots=True)
class RevisionPolicy:
    grain: tuple[str, ...] = ()
    equal_duplicates: str = "coalesce"
    conflicts: str = "reject"
    ordered_issues: tuple[str, ...] = ()
    ordering_basis: str | None = None
    as_of: str | None = None
    expected_issues: tuple[str, ...] = ()
    allow_cross_source: bool = False
    max_rows: int = 1000000
    ordered_revisions: tuple[str, ...] = ()
    expected_members: tuple[HistoryExpectation, ...] = ()
    limits: HistoryLimits = HistoryLimits()
    provenance_fields: tuple[str, ...] = ("source_issue", "source_issue_id", "source_row", "source_cell",
        "source_locator", "evidence", "evidence_ref", "lineage")

    def __post_init__(self):
        for name in ("grain", "ordered_issues", "ordered_revisions", "expected_issues", "provenance_fields"):
            object.__setattr__(self, name, _tokens(getattr(self, name), "history.policy_members_invalid"))
        if set(self.provenance_fields) & {"period", "metric", "subject", "subject_namespace", "unit", "scale",
                "value", "value_status", "perimeter", "measure_kind", "frequency", "period_kind", "basis",
                "value_basis", "dimensions", "legal_kind", "currency", "portfolio", "activity", "bank", "sex", "age",
                *self.grain}:
            raise ValueError("history.economic_field_is_not_provenance")
        if isinstance(self.limits, Mapping):
            object.__setattr__(self, "limits", HistoryLimits(**self.limits))
        if not isinstance(self.limits, HistoryLimits):
            raise ValueError("history.typed_limits_required")
        expected = tuple(HistoryExpectation(**value) if isinstance(value, Mapping) else value for value in self.expected_members)
        if any(not isinstance(value, HistoryExpectation) for value in expected):
            raise ValueError("history.expectation_invalid")
        object.__setattr__(self, "expected_members", expected)
        if self.ordered_issues and self.ordered_revisions:
            raise ValueError("history.single_order_basis_required")
        order = self.ordered_revisions or self.ordered_issues
        if self.equal_duplicates not in {"coalesce", "reject"} or self.conflicts not in {"reject", "latest", "earliest"}:
            raise ValueError("history.revision_policy_invalid")
        if self.conflicts != "reject" and (not order or not self.ordering_basis):
            raise ValueError("history.revision_order_required")
        if self.as_of is not None and (not self.ordering_basis or self.as_of not in order):
            raise ValueError("history.as_of_order_required")
        if type(self.allow_cross_source) is not bool or type(self.max_rows) is not int or not 1 <= self.max_rows <= 10000000:
            raise ValueError("history.policy_limit_invalid")

    @property
    def identity(self):
        return fingerprint(self)


def revision_policy(value):
    if isinstance(value, RevisionPolicy):
        return value
    if not isinstance(value, Mapping) or set(value) - {f.name for f in fields(RevisionPolicy)}:
        raise ValueError("history.typed_policy_required")
    return RevisionPolicy(**value)


def stable_semantics(dataset):
    return {key: value for key, value in dataset.semantics.items() if key != "source_issues"}


def history_grain(dataset, override=()):
    """Use the admitted history grain or the original's declared semantic grain."""
    if override:
        return _tokens(override, "history.grain_invalid")
    if isinstance(dataset.history_membership, HistoryMembership):
        return dataset.history_membership.grain
    return _tokens(dataset.semantics.get("grain", ()), "history.grain_invalid")


def member_for(dataset, revision=None):
    certificates = tuple(getattr(dataset, "validation_certificates", ()))
    content = dataset_content_identity(dataset)
    assets = tuple(sorted({use.coordinate.asset_id for use in dataset.source_uses
        if use.coordinate.asset_id and use.coordinate.source_id == dataset.source_id
        and use.coordinate.issue_id in {None, dataset.issue_id}}))
    if revision is not None and revision.asset_id:
        if revision.asset_id not in assets:
            raise ValueError("history.revision_asset_mismatch")
    return HistoryMember(content, dataset.source_id, dataset.issue_id,
        tuple(dict.fromkeys(observation_key(row) for row in dataset.rows)),
        tuple(cert.identity for cert in certificates if isinstance(cert, ValidationCertificate)
              and cert.dataset_identity == content and cert.source_id == dataset.source_id and cert.issue_id == dataset.issue_id),
        assets, revision, dataset.assessment)


def _member_union(members):
    result = {}
    for member in members:
        key = member.identity
        previous = result.get(key)
        if previous is not None:
            if (previous.content_identity, previous.source_id, previous.issue_id, previous.coordinates,
                    previous.asset_ids, previous.revision) != (member.content_identity, member.source_id,
                    member.issue_id, member.coordinates, member.asset_ids, member.revision):
                raise ValueError("history.member_conflict")
            assessment = previous.assessment
            if assessment != member.assessment:
                assessment = _combine_assessments((assessment, member.assessment))
            member = replace(previous, certificate_ids=tuple(sorted(set((*previous.certificate_ids, *member.certificate_ids)))),
                assessment=assessment)
        result[key] = member
    return tuple(result[key] for key in sorted(result))


def history_members(datasets):
    return _member_union(member for dataset in datasets for member in
        (history_for(dataset).members if dataset.history_membership is not None else (member_for(dataset),)))


def history_certificates(datasets):
    certificates = {}
    for dataset in datasets:
        for certificate in dataset.validation_certificates:
            if not isinstance(certificate, ValidationCertificate):
                raise TypeError("validation.typed_certificate_required")
            certificates[certificate.identity] = certificate
    return tuple(certificates[key] for key in sorted(certificates))


def history_certificate_dependencies(dataset):
    """Return witness references needed by retained candidates, without authority.

    Only compact ledger metadata and attached certificate records are inspected;
    the coordinator need not scan observation payloads to retain these facts.
    """
    if not isinstance(dataset, SourceDataset):
        return ()
    attached = {certificate.identity for certificate in dataset.validation_certificates
                if isinstance(certificate, ValidationCertificate)}
    membership = dataset.history_membership
    if membership is None:
        return tuple(sorted(attached))
    if not isinstance(membership, HistoryMembership):
        raise ValueError("history.unsupported_schema")
    needed = {candidate.member_id for candidate in membership.candidates}
    return tuple(sorted({identity for member in membership.members
        if not membership.candidates or member.identity in needed or not member.coordinates for identity in member.certificate_ids
        if identity in attached}))


def _combine_assessments(assessments, *, complete=True, qualifications=(), expected=(), observed=(), coverage=None):
    assessments = tuple(assessments)
    qualified = (frozenset.intersection(*(value.qualifications for value in assessments)) if assessments else frozenset())
    return Assessment("complete" if complete and all(value.complete for value in assessments) else "partial",
        tuple(dict.fromkeys(finding for value in assessments for finding in value.findings)),
        tuple(expected), tuple(observed), qualified | frozenset(qualifications), coverage)


def _view_members(membership):
    selected = {key for decision in membership.revisions for key in decision.selected_candidates}
    member_ids = {candidate.member_id for candidate in membership.candidates if candidate.identity in selected}
    return tuple(member for member in membership.members if member.identity in member_ids)


def history_view_labels(membership):
    members = _view_members(membership) or membership.members
    sources = {member.source_id for member in members}
    issues = {member.issue_id for member in members}
    return (next(iter(sources)) if len(sources) == 1 else "multi_source_history",
            next(iter(issues)) if len(issues) == 1 else "multi_issue_history")


def validate_history_view(dataset):
    """Reject a forged materialized view or an unsupported old history schema."""
    membership = dataset.history_membership
    if membership is None:
        return
    if not isinstance(membership, HistoryMembership) or membership.schema != HISTORY_SCHEMA:
        raise ValueError("history.unsupported_schema")
    rows = {value.identity: value.value for value in membership.rows}
    if any(fingerprint(value) != key for key, value in rows.items()):
        raise ValueError("history.row_identity_mismatch")
    candidates = {value.identity: value for value in membership.candidates}
    expected = {decision.coordinate: candidates[decision.representative].row_identity
                for decision in membership.revisions if decision.representative is not None}
    actual = {}
    for row in dataset.rows:
        coordinate = observation_key(row, membership.grain or None)
        if coordinate in actual:
            raise ValueError("observations.duplicate_grain")
        actual[coordinate] = fingerprint(row)
    if actual != expected or any(identity not in rows for identity in actual.values()):
        raise ValueError("history.view_binding_mismatch")
    if (dataset.source_id, dataset.issue_id) != history_view_labels(membership):
        raise ValueError("history.view_scope_mismatch")
    if fingerprint(stable_semantics(dataset)) != membership.semantics_identity:
        raise ValueError("history.semantic_binding_mismatch")


def history_for(dataset, *, grain=None, limits=None):
    """Admit an original exact dataset or reuse its complete normalized ledger."""
    if not isinstance(dataset, SourceDataset):
        raise TypeError("history.dataset_required")
    grain = history_grain(dataset, grain)
    if dataset.history_membership is not None:
        validate_history_view(dataset)
        membership = dataset.history_membership
        if grain and grain != membership.grain:
            raise ValueError("history.grain_mismatch")
        return membership if limits is None or membership.limits == limits else replace(membership, limits=limits)
    limits = limits or HistoryLimits()
    member = member_for(dataset)
    rows, candidates, decisions = {}, [], []
    active, seen = [], set()
    for ordinal, value in enumerate(dataset.rows):
        row = HistoryRow(value)
        coordinate = observation_key(value, grain or None)
        if coordinate in seen:
            raise ValueError("observations.duplicate_grain")
        seen.add(coordinate)
        rows.setdefault(row.identity, row)
        candidate = HistoryCandidate(member.identity, coordinate, row.identity, ordinal)
        candidates.append(candidate)
        active.append(coordinate)
        decisions.append(RevisionDecision(coordinate, (candidate.identity,), representative=candidate.identity))
        if len(candidates) > limits.max_candidates:
            raise ValueError("history.candidate_limit")
    return HistoryMembership(HISTORY_SCHEMA, (member,), tuple(rows.values()), tuple(candidates), tuple(active),
        tuple(decisions), fingerprint(stable_semantics(dataset)), grain=grain,
        eligible_candidates=tuple(candidate.identity for candidate in candidates), limits=limits)


def bind_publication_revision(dataset, revision):
    """Bind one original dataset to an explicitly qualified revision occurrence.

    This does not assert publisher chronology or validation authority. Supply the
    qualified order through ``RevisionPolicy.ordered_revisions`` when resolving.
    """
    if not isinstance(revision, PublicationRevision):
        raise ValueError("history.typed_revision_required")
    if dataset.history_membership is not None:
        raise ValueError("history.original_revision_binding_required")
    original = history_for(dataset)
    member = member_for(dataset, revision)
    candidates = tuple(HistoryCandidate(member.identity, item.coordinate, item.row_identity, item.ordinal)
                       for item in original.candidates)
    decisions = tuple(RevisionDecision(item.coordinate, (item.identity,), representative=item.identity) for item in candidates)
    membership = replace(original, members=(member,), candidates=candidates, revisions=decisions,
        eligible_candidates=tuple(item.identity for item in candidates))
    return replace(dataset, history_membership=membership, native=None)


def _expectations(members, issues):
    scopes = {(member.source_id, asset) for member in members for asset in member.asset_ids or ("",)}
    return tuple(HistoryExpectation(source, issue, asset) for source, asset in sorted(scopes) for issue in issues)


def _union_ledgers(datasets, *, grain=(), limits=HistoryLimits()):
    memberships = tuple(history_for(dataset, grain=grain, limits=limits) for dataset in datasets)
    grains = {item.grain for item in memberships}
    if len(grains) != 1:
        raise ValueError("history.grain_mismatch")
    members = _member_union(member for item in memberships for member in item.members)
    rows, candidates, expectations = {}, {}, {}
    active, seen = [], set()
    for membership in memberships:
        for row in membership.rows:
            previous = rows.setdefault(row.identity, row)
            if previous != row:
                raise ValueError("history.row_identity_mismatch")
        for candidate in membership.candidates:
            previous = candidates.setdefault(candidate.identity, candidate)
            if previous != candidate:
                raise ValueError("history.candidate_identity_mismatch")
        for expected in membership.expectations:
            expectations[expected.identity] = expected
        for coordinate in membership.active_scope:
            if coordinate not in seen:
                active.append(coordinate)
                seen.add(coordinate)
        if len(candidates) > limits.max_candidates or len(members) > limits.max_members:
            raise ValueError("history.candidate_limit" if len(candidates) > limits.max_candidates else "history.member_limit")
    return (members, tuple(rows[key] for key in sorted(rows)), tuple(candidates[key] for key in sorted(candidates)),
            tuple(active), tuple(expectations[key] for key in sorted(expectations)), memberships[0].grain, memberships)


def _assess_history(membership, *, qualification):
    eligible = set(membership.eligible_candidates)
    member_ids = {item.member_id for item in membership.candidates if item.identity in eligible}
    members = tuple(member for member in membership.members if member.identity in member_ids or not member.coordinates)
    missing = {item.identity for item in membership.missing_expectations}
    expected = tuple(item.identity for item in membership.all_expectations)
    coverage = membership.selection_coverage
    if coverage is not None:
        observed_coordinates = tuple(decision.coordinate for decision in membership.revisions if decision.selected_candidates)
        coverage = replace(coverage, selected=observed_coordinates,
            missing=tuple(coordinate for coordinate in coverage.requested if coordinate not in set(observed_coordinates)))
    return _combine_assessments((member.assessment for member in members), complete=membership.complete,
        qualifications=(qualification,), expected=expected,
        observed=tuple(value for value in expected if value not in missing), coverage=coverage)


def _result(datasets, membership, *, qualification, rows=None):
    if rows is None:
        payloads = {row.identity: row.value for row in membership.rows}
        candidates = {item.identity: item for item in membership.candidates}
        rows = tuple(payloads[candidates[decision.representative].row_identity]
            for decision in membership.revisions if decision.representative is not None)
    source, issue = history_view_labels(membership)
    return SourceDataset(source, tuple(rows), stable_semantics(datasets[0]), issue,
        tuple(history_value_identity(dataset) for dataset in datasets), _assess_history(membership, qualification=qualification),
        source_uses=tuple(dict.fromkeys(use for dataset in datasets for use in dataset.source_uses)),
        validation_certificates=history_certificates(datasets), history_membership=membership)


def _compatible(datasets, allow_cross_source):
    if not datasets or len(datasets) > 10000 or any(not isinstance(value, SourceDataset) for value in datasets):
        raise ValueError("history.datasets_required")
    sources = {member.source_id for dataset in datasets for member in
        (dataset.history_membership.members if isinstance(dataset.history_membership, HistoryMembership) else (member_for(dataset),))}
    if len(sources) > 1 and not allow_cross_source:
        raise ValueError("observations.source_mismatch")
    semantics = stable_semantics(datasets[0])
    if any(stable_semantics(dataset) != semantics for dataset in datasets[1:]):
        raise ValueError("observations.semantic_mismatch")


def merge_histories(datasets, *, allow_cross_source=False, grain=(), limits=HistoryLimits()):
    """Strictly append disjoint displayed coordinates with complete evidence."""
    datasets = tuple(datasets)
    _compatible(datasets, allow_cross_source)
    visible = set()
    for dataset in datasets:
        for row in dataset.rows:
            coordinate = observation_key(row, history_grain(dataset, grain) or None)
            if coordinate in visible:
                raise ValueError("observations.duplicate_grain")
            visible.add(coordinate)
    members, rows, candidates, active, expectations, actual_grain, ledgers = _union_ledgers(datasets, grain=grain, limits=limits)
    decisions, eligible = {}, set()
    for ledger in ledgers:
        eligible.update(ledger.eligible_candidates)
        for decision in ledger.revisions:
            previous = decisions.get(decision.coordinate)
            if previous is not None and previous.selected_candidates and decision.selected_candidates:
                raise ValueError("observations.duplicate_grain")
            if previous is None or decision.selected_candidates:
                decisions[decision.coordinate] = decision
    grouped = {}
    for candidate in candidates:
        grouped.setdefault(candidate.coordinate, set()).add(candidate.identity)
    combined = tuple(replace(decisions[coordinate],
        alternative_candidates=tuple(sorted(grouped.get(coordinate, set()) - set(decisions[coordinate].selected_candidates))))
        for coordinate in active)
    view_expectations = {value.identity: value for ledger in ledgers for value in ledger.view_expectations}
    selection_scopes = {fingerprint(value): value for ledger in ledgers for value in ledger.selection_scopes}
    membership = HistoryMembership(HISTORY_SCHEMA, members, rows, candidates, active, combined,
        fingerprint(stable_semantics(datasets[0])), grain=actual_grain, expectations=expectations,
        view_expectations=tuple(view_expectations[key] for key in sorted(view_expectations)),
        eligible_candidates=tuple(sorted(eligible)),
        selection_scopes=tuple(selection_scopes[key] for key in sorted(selection_scopes)), limits=limits)
    return _result(datasets, membership, qualification="partitioned_input_coverage",
        rows=tuple(row for dataset in datasets for row in dataset.rows))


def resolve_revisions(datasets, policy):
    """Resolve a view from exact retained candidates without discarding vintages."""
    policy = revision_policy(policy)
    datasets = tuple(datasets)
    _compatible(datasets, policy.allow_cross_source)
    members, rows, candidates, active, inherited, grain, ledgers = _union_ledgers(datasets,
        grain=policy.grain, limits=policy.limits)
    by_member = {member.identity: member for member in members}
    by_row = {row.identity: row.value for row in rows}
    order = {key: index for index, key in enumerate(policy.ordered_revisions or policy.ordered_issues)}
    def rank(candidate):
        member = by_member[candidate.member_id]
        key = (None if member.revision is None else member.revision.identity) if policy.ordered_revisions else member.issue_id
        if key not in order:
            raise ValueError("history.revision_order_incomplete")
        return order[key]
    groups = {}
    for candidate in candidates:
        groups.setdefault(candidate.coordinate, []).append(candidate)
    decisions, eligible_ids = [], []
    for coordinate in active:
        all_candidates = groups.get(coordinate, ())
        eligible = tuple(candidate for candidate in all_candidates
            if policy.as_of is None or rank(candidate) <= order[policy.as_of])
        eligible_ids.extend(item.identity for item in eligible)
        if not eligible:
            selected, rule = (), "unavailable"
        elif len(eligible) == 1:
            selected, rule = eligible, "unique"
        elif len({_observation_payload(by_row[item.row_identity], policy) for item in eligible}) == 1:
            if policy.equal_duplicates == "reject":
                raise ValueError("history.equal_duplicate_rejected")
            selected, rule = eligible, "equal"
        else:
            if policy.conflicts == "reject":
                raise ValueError("history.ambiguous_revision")
            best = (max if policy.conflicts == "latest" else min)(rank(item) for item in eligible)
            selected = tuple(item for item in eligible if rank(item) == best)
            if len({_observation_payload(by_row[item.row_identity], policy) for item in selected}) != 1:
                raise ValueError("history.ambiguous_same_revision")
            rule = policy.conflicts
        selected_ids = tuple(sorted(item.identity for item in selected))
        # A stable representative makes input permutation irrelevant while the
        # decision still names every equal candidate's exact source evidence.
        decisions.append(RevisionDecision(coordinate, selected_ids,
            tuple(sorted(item.identity for item in all_candidates if item.identity not in set(selected_ids))),
            rule, selected_ids[0] if selected_ids else None, policy.identity))
    if sum(bool(decision.selected_candidates) for decision in decisions) > policy.max_rows:
        raise ValueError("history.row_limit")
    expected = {item.identity: item for item in (*policy.expected_members, *_expectations(members, policy.expected_issues))}
    previous_selections = tuple(dataset.history_membership.selection_coverage for dataset in datasets
        if isinstance(dataset.history_membership, HistoryMembership) and dataset.history_membership.selection_coverage is not None)
    selection = previous_selections[0] if len(datasets) == 1 and previous_selections else None
    selection_scopes = {fingerprint(value): value for ledger in ledgers for value in ledger.selection_scopes}
    membership = HistoryMembership(HISTORY_SCHEMA, members, rows, candidates, active, tuple(decisions),
        fingerprint(stable_semantics(datasets[0])), grain=grain, expectations=inherited,
        view_expectations=tuple(expected[key] for key in sorted(expected)),
        eligible_candidates=tuple(sorted(eligible_ids)), policy_identity=policy.identity,
        selection_identity=selection.selector_identity if selection is not None else None,
        selection_coverage=selection,
        selection_scopes=tuple(selection_scopes[key] for key in sorted(selection_scopes)), limits=policy.limits)
    result = _result(datasets, membership, qualification="explicit_revision_policy")
    return result, membership.revisions


def project_history(dataset, rows, *, query_identity=None, expected_coordinates=()):
    """Freeze a selected view's coordinates and retain only their candidates."""
    original = history_for(dataset)
    rows = tuple(rows)
    current = {fingerprint(row) for row in dataset.rows}
    if any(fingerprint(row) not in current for row in rows):
        raise ValueError("history.projection_not_subset")
    active = tuple(dict.fromkeys((*expected_coordinates,
        *(observation_key(row, original.grain or None) for row in rows))))
    selected = set(active)
    candidates = tuple(item for item in original.candidates if item.coordinate in selected)
    candidate_ids = {item.identity for item in candidates}
    row_ids = {item.row_identity for item in candidates}
    decisions = {item.coordinate: item for item in original.revisions}
    membership = replace(original, rows=tuple(item for item in original.rows if item.identity in row_ids),
        candidates=candidates, active_scope=active,
        revisions=tuple(decisions.get(coordinate, RevisionDecision(coordinate, (), rule="unavailable")) for coordinate in active),
        eligible_candidates=tuple(key for key in original.eligible_candidates if key in candidate_ids),
        selection_identity=query_identity)
    return membership


def set_history_expectations(dataset, expected_issues=(), expected_members=()):
    membership = history_for(dataset)
    additions = (*_expectations(membership.members, expected_issues), *tuple(expected_members))
    expected = {value.identity: value for value in (*membership.expectations, *additions)}
    membership = replace(membership, expectations=tuple(expected[key] for key in sorted(expected)))
    result = _result((dataset,), membership, qualification="explicit_issue_coverage", rows=dataset.rows)
    return result


def verify_history_certificates(dataset, verify_authority):
    """Verify exact source/member/candidate witnesses without creating authority."""
    try:
        validate_history_view(dataset)
    except (TypeError, ValueError, KeyError):
        return False
    certificates = {certificate.identity: certificate for certificate in history_certificates((dataset,))}
    membership = dataset.history_membership
    semantics = fingerprint(stable_semantics(dataset))
    if membership is None:
        content = dataset_content_identity(dataset)
        rows = {(observation_key(row), fingerprint(row)) for row in dataset.rows}
        return bool(certificates) and any(certificate.dataset_identity == content
            and certificate.source_id == dataset.source_id and certificate.issue_id == dataset.issue_id
            and certificate.semantics_identity == semantics and rows <= set(certificate.row_identities)
            and certificate.assessment.complete and verify_authority(certificate)
            for certificate in certificates.values())
    by_row = {row.identity: row.value for row in membership.rows}
    authority, admitted, competent_members = {}, {}, set()
    for member in membership.members:
        witnesses = set()
        for key in member.certificate_ids:
            certificate = certificates.get(key)
            if (certificate is None or certificate.dataset_identity != member.content_identity
                    or certificate.source_id != member.source_id or certificate.issue_id != member.issue_id
                    or certificate.semantics_identity != semantics or not certificate.assessment.complete):
                continue
            if key not in authority:
                authority[key] = bool(verify_authority(certificate))
            if authority[key]:
                competent_members.add(member.identity)
                witnesses.update(certificate.row_identities)
        admitted[member.identity] = witnesses
    if not membership.candidates:
        return bool(certificates) and all(member.identity in competent_members for member in membership.members)
    return bool(certificates) and all((observation_key(by_row[candidate.row_identity]), candidate.row_identity)
        in admitted[candidate.member_id] for candidate in membership.candidates)


def _observation_payload(row, policy):
    """Known provenance is projected away; unknown qualifiers remain economic."""
    return fingerprint({key: value for key, value in row.items() if key not in policy.provenance_fields})


PORTABLE_TYPES = (ValidationCertificate, PublicationRevision, HistoryLimits, HistoryMember,
    HistoryRow, HistoryCandidate, HistoryExpectation, RevisionDecision, HistoryMembership, RevisionPolicy)
