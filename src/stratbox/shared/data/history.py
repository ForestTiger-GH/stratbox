"""Portable history membership, explicit revisions and validation bindings.

Certificates describe a validation result. Authority comes from an accepted
validator output in the execution journal, never from these data constructors.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace

from .values import Assessment, SourceDataset, fingerprint, immutable
from .selection import observation_key, SelectionError


def dataset_content_identity(dataset):
    """Return a stable content binding excluding native state and certificates."""
    if not isinstance(dataset, SourceDataset):
        raise TypeError("history.dataset_required")
    return fingerprint((dataset.source_id, dataset.issue_id, dataset.rows,
                        dataset.semantics, dataset.source_uses))


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
        coordinates = tuple(self.coordinates)
        coordinate_set = set(coordinates)
        if len(coordinates) > 1000000 or len(coordinates) != len(coordinate_set) or any(not isinstance(v, str) or not v for v in coordinates):
            raise ValueError("validation.certificate_coordinates_invalid")
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
class HistoryMember:
    dataset_identity: str
    content_identity: str
    source_id: str
    issue_id: str
    coordinates: tuple[str, ...]
    certificate_ids: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("coordinates", "certificate_ids"):
            values = tuple(getattr(self, name))
            if len(values) != len(set(values)) or len(values) > 1000000:
                raise ValueError("history.member_invalid")
            object.__setattr__(self, name, values)


@dataclass(frozen=True, slots=True)
class RevisionDecision:
    coordinate: str
    selected_inputs: tuple[str, ...]
    alternative_inputs: tuple[str, ...] = ()
    rule: str = "unique"
    alternative_rows: tuple[Mapping[str, object], ...] = ()

    def __post_init__(self):
        if self.rule not in {"unique", "equal", "latest", "earliest"} or not self.coordinate or not self.selected_inputs:
            raise ValueError("history.revision_decision_invalid")
        for name in ("selected_inputs", "alternative_inputs"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        object.__setattr__(self, "alternative_rows", immutable(tuple(self.alternative_rows)))


@dataclass(frozen=True, slots=True)
class HistoryMembership:
    members: tuple[HistoryMember, ...]
    expected_issues: tuple[str, ...] = ()
    missing_issues: tuple[str, ...] = ()
    revisions: tuple[RevisionDecision, ...] = ()
    policy_identity: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "members", tuple(self.members))
        object.__setattr__(self, "revisions", tuple(self.revisions))
        for name in ("expected_issues", "missing_issues"):
            values = tuple(getattr(self, name))
            if len(values) != len(set(values)) or any(not isinstance(v, str) for v in values):
                raise ValueError("history.issue_membership_invalid")
            object.__setattr__(self, name, values)
        if (len(self.members) > 10000 or any(not isinstance(v, HistoryMember) for v in self.members)
                or len({v.content_identity for v in self.members}) != len(self.members)
                or any(not isinstance(v, RevisionDecision) for v in self.revisions)
                or not set(self.missing_issues) <= set(self.expected_issues)):
            raise ValueError("history.membership_invalid")

    @property
    def complete(self):
        return not self.missing_issues


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

    def __post_init__(self):
        for name in ("grain", "ordered_issues", "expected_issues"):
            values = tuple(getattr(self, name))
            if len(values) != len(set(values)) or any(not isinstance(v, str) or not v for v in values):
                raise ValueError("history.policy_members_invalid")
            object.__setattr__(self, name, values)
        if self.equal_duplicates not in {"coalesce", "reject"} or self.conflicts not in {"reject", "latest", "earliest"}:
            raise ValueError("history.revision_policy_invalid")
        if self.conflicts != "reject" and (not self.ordered_issues or not self.ordering_basis):
            raise ValueError("history.revision_order_required")
        if self.as_of is not None and (not self.ordering_basis or self.as_of not in self.ordered_issues):
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


def member_for(dataset):
    certificates = tuple(getattr(dataset, "validation_certificates", ()))
    content = dataset_content_identity(dataset)
    return HistoryMember(dataset.identity, content, dataset.source_id, dataset.issue_id,
        tuple(dict.fromkeys(observation_key(row) for row in dataset.rows)),
        tuple(cert.identity for cert in certificates if isinstance(cert, ValidationCertificate)
              and cert.dataset_identity == content and cert.source_id == dataset.source_id and cert.issue_id == dataset.issue_id))


def history_members(datasets):
    members = {}
    for dataset in datasets:
        membership = getattr(dataset, "history_membership", None)
        values = membership.members if isinstance(membership, HistoryMembership) else (member_for(dataset),)
        for value in values:
            previous = members.get(value.content_identity)
            if previous is not None and previous != value:
                raise ValueError("history.member_conflict")
            members[value.content_identity] = value
    return tuple(members.values())


def history_certificates(datasets):
    certificates = {}
    for dataset in datasets:
        for certificate in getattr(dataset, "validation_certificates", ()):
            if not isinstance(certificate, ValidationCertificate):
                raise TypeError("validation.typed_certificate_required")
            certificates[certificate.identity] = certificate
    return tuple(certificates.values())


def verify_history_certificates(dataset, verify_authority):
    """Verify original per-issue bindings and actual selected row coverage."""
    membership = getattr(dataset, "history_membership", None)
    by_identity = {}
    for certificate in getattr(dataset, "validation_certificates", ()):
        if not isinstance(certificate, ValidationCertificate):
            raise TypeError("validation.typed_certificate_required")
        by_identity[certificate.identity] = certificate
    certificates = tuple(by_identity.values())
    if not isinstance(membership, HistoryMembership):
        content = dataset_content_identity(dataset)
        return bool(certificates) and any(certificate.dataset_identity == content
            and certificate.source_id == dataset.source_id and certificate.issue_id == dataset.issue_id and certificate.assessment.complete
            and verify_authority(certificate) for certificate in certificates)
    semantics_identity = fingerprint(stable_semantics(dataset))
    sources = {member.source_id for member in membership.members}
    issues = {member.issue_id for member in membership.members}
    expected_issue = next(iter(issues)) if len(issues) == 1 else 'multi_issue_history'
    if sources != {dataset.source_id} or dataset.issue_id != expected_issue:
        return False
    admitted_rows = set()
    authority = {}
    def competent_authority(key):
        if key not in authority:
            authority[key] = bool(verify_authority(by_identity[key]))
        return authority[key]
    for member in membership.members:
        competent = [by_identity[key] for key in member.certificate_ids if key in by_identity
                     and by_identity[key].dataset_identity == member.content_identity
                     and by_identity[key].source_id == member.source_id
                     and by_identity[key].issue_id == member.issue_id
                     and by_identity[key].semantics_identity == semantics_identity
                     and by_identity[key].assessment.complete and competent_authority(key)]
        if not competent:
            return False
        coordinates = set(member.coordinates)
        for certificate in competent:
            admitted_rows.update((coordinate, identity) for coordinate, identity in certificate.row_identities
                                 if coordinate in coordinates)
    return all((observation_key(row), fingerprint(row)) in admitted_rows for row in dataset.rows)


def resolve_revisions(datasets, policy):
    """Resolve only explicitly ordered conflicts; retain every rejected value."""
    policy = revision_policy(policy)
    datasets = tuple(datasets)
    if not datasets or len(datasets) > 10000 or any(not isinstance(value, SourceDataset) for value in datasets):
        raise ValueError("history.datasets_required")
    if len({dataset.source_id for dataset in datasets}) > 1 and not policy.allow_cross_source:
        raise ValueError("observations.source_mismatch")
    semantics = stable_semantics(datasets[0])
    if any(stable_semantics(dataset) != semantics for dataset in datasets[1:]):
        raise ValueError("observations.semantic_mismatch")
    order = {value: index for index, value in enumerate(policy.ordered_issues)}
    groups = {}
    count = 0
    participating = set()
    for dataset in datasets:
        membership = getattr(dataset, "history_membership", None)
        members = {member.content_identity: member for member in history_members((dataset,))}
        members_by_coordinate = {}
        for key, member in members.items():
            for coordinate in member.coordinates:
                members_by_coordinate.setdefault(coordinate, []).append(key)
        prior = {decision.coordinate: decision for decision in membership.revisions} if isinstance(membership, HistoryMembership) else {}
        for row in dataset.rows:
            coordinate = observation_key(row, policy.grain or None)
            original_coordinate = observation_key(row)
            selected_ids = (prior[coordinate].selected_inputs if coordinate in prior
                            else tuple(members_by_coordinate.get(original_coordinate, ())))
            if not selected_ids or any(key not in members for key in selected_ids):
                raise ValueError("history.row_membership_unresolved")
            entries = [(members[key], row) for key in selected_ids]
            if coordinate in prior:
                decision = prior[coordinate]
                if len(decision.alternative_inputs) != len(decision.alternative_rows):
                    raise ValueError("history.revision_evidence_incomplete")
                for key, alternative in zip(decision.alternative_inputs, decision.alternative_rows):
                    if key not in members:
                        raise ValueError("history.row_membership_unresolved")
                    entries.append((members[key], alternative))
            for member, candidate_row in entries:
                if policy.as_of is not None:
                    if member.issue_id not in order:
                        raise ValueError("history.revision_order_incomplete")
                    if order[member.issue_id] > order[policy.as_of]:
                        continue
                count += 1
                if count > policy.max_rows:
                    raise ValueError("history.row_limit")
                participating.add(member.content_identity)
                groups.setdefault(coordinate, []).append((member, candidate_row))
    if not groups and policy.as_of is not None:
        raise ValueError("history.no_admitted_vintage")
    resolved, decisions = [], []
    for coordinate, candidates in groups.items():
        unique = {_observation_payload(row) for _, row in candidates}
        if len(candidates) == 1:
            selected, rejected, rule = candidates, [], "unique"
        elif len(unique) == 1:
            if policy.equal_duplicates == "reject":
                raise ValueError("history.equal_duplicate_rejected")
            selected, rejected, rule = candidates, [], "equal"
        else:
            if policy.conflicts == "reject":
                raise ValueError("history.ambiguous_revision")
            if any(member.issue_id not in order for member, _ in candidates):
                raise ValueError("history.revision_order_incomplete")
            best = (max if policy.conflicts == "latest" else min)(order[member.issue_id] for member, _ in candidates)
            selected = [(member, row) for member, row in candidates if order[member.issue_id] == best]
            rejected = [(member, row) for member, row in candidates if order[member.issue_id] != best]
            if len({_observation_payload(row) for _, row in selected}) != 1:
                raise ValueError("history.ambiguous_same_revision")
            rule = policy.conflicts
        resolved.append(selected[0][1])
        decisions.append(RevisionDecision(coordinate, tuple(dict.fromkeys(member.content_identity for member, _ in selected)),
            tuple(member.content_identity for member, _ in rejected), rule, tuple(row for _, row in rejected)))
    members = tuple(member for member in history_members(datasets) if member.content_identity in participating)
    observed = tuple(dict.fromkeys(member.issue_id for member in members))
    observed_set = set(observed)
    missing = tuple(issue for issue in policy.expected_issues if issue not in observed_set)
    membership = HistoryMembership(members, policy.expected_issues, missing, tuple(decisions), policy.identity)
    assessment = Assessment("complete" if not missing and all(d.assessment.complete for d in datasets) else "partial",
        tuple(dict.fromkeys(f for dataset in datasets for f in dataset.assessment.findings)),
        expected=policy.expected_issues, observed=observed,
        qualifications=frozenset.intersection(*(d.assessment.qualifications for d in datasets)) | frozenset({"explicit_revision_policy"}))
    result = SourceDataset(datasets[0].source_id, tuple(resolved), semantics,
        issue_id=observed[0] if len(observed) == 1 else "multi_issue_history",
        lineage=tuple(dataset.identity for dataset in datasets), assessment=assessment,
        source_uses=tuple(dict.fromkeys(use for dataset in datasets for use in dataset.source_uses)),
        validation_certificates=history_certificates(datasets), history_membership=membership)
    return result, tuple(decisions)


def _observation_payload(row):
    """Publication provenance may differ while the measured observation agrees."""
    provenance = {"source_issue", "source_issue_id", "source_row", "source_cell", "source_locator", "evidence", "lineage"}
    return fingerprint({key: value for key, value in row.items() if key not in provenance})
