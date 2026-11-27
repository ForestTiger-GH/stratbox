"""Adversarial algebra and scope laws for normalized historical evidence."""
from dataclasses import replace
from decimal import Decimal

import pytest

from stratbox.shared.data.history import (
    HistoryExpectation, HistoryLimits, PublicationRevision, RevisionPolicy,
    bind_publication_revision, dataset_content_identity, history_for,
    history_certificate_dependencies,
    make_validation_certificate, merge_histories, resolve_revisions,
    validate_history_view, verify_history_certificates,
)
from stratbox.shared.data.selection import ObservationQuery, observation_key, select_observations
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.values import Assessment, SourceDataset


def part(issue, value=1, *, period="2026-01", source="source", provenance=False, asset=""):
    row = {"period": period, "metric": "stock", "value": Decimal(value)}
    if provenance:
        row.update(source_issue=issue, source_cell=f"{issue}!A1", evidence_ref=f"original:{issue}")
    uses = () if not asset else (SourceUse(SourceCoordinate(source_id=source, issue_id=issue, asset_id=asset)),)
    return SourceDataset(source, (row,), {"unit": "RUB"}, issue, source_uses=uses)


def qualify(dataset, rule="source.rule"):
    certificate = make_validation_certificate(dataset, rule_id=rule,
        method_identity="reviewed.method", build_identity="fixture.build")
    return replace(dataset, validation_certificates=(*dataset.validation_certificates, certificate))


def ordered(*issues, **changes):
    return RevisionPolicy(conflicts="latest", ordered_issues=issues,
        ordering_basis="publisher.release_order", **changes)


def exact_candidates(dataset):
    ledger = dataset.history_membership
    members = {member.identity: member for member in ledger.members}
    rows = {row.identity: row.value for row in ledger.rows}
    return {candidate.identity: (members[candidate.member_id].issue_id, rows[candidate.row_identity])
        for candidate in ledger.candidates}


def test_disjoint_merge_keeps_original_value_for_later_as_of():
    policy = ordered("first", "revised", "next")
    latest, _ = resolve_revisions((part("first", 1), part("revised", 2)), policy)
    merged = merge_histories((latest, part("next", 3, period="2026-02")))
    old, _ = resolve_revisions((merged,), replace(policy, as_of="first"))
    assert [row["value"] for row in old.rows] == [1]
    assert old.history_membership.missing_coordinates
    assert not old.assessment.complete
    assert len(old.history_membership.candidates) == 3
    restored_latest, _ = resolve_revisions((old,), policy)
    assert [row["value"] for row in restored_latest.rows] == [2, 3]
    assert restored_latest.assessment.complete


@pytest.mark.parametrize("reverse", (False, True))
def test_equal_values_keep_exact_member_rows_and_certificates(reverse):
    parts = (qualify(part("first", provenance=True)), qualify(part("revised", provenance=True)))
    trusted = {certificate.identity for dataset in parts for certificate in dataset.validation_certificates}
    history, _ = resolve_revisions(tuple(reversed(parts)) if reverse else parts, ordered("first", "revised"))
    assert len(history.history_membership.rows) == 2
    assert len(history.history_membership.revisions[0].selected_candidates) == 2
    earlier, _ = resolve_revisions((history,), ordered("first", "revised", as_of="first"))
    assert earlier.issue_id == "first"
    assert earlier.rows[0]["source_issue"] == "first"
    assert earlier.rows[0]["source_cell"] == "first!A1"
    assert verify_history_certificates(earlier, lambda certificate: certificate.identity in trusted)
    assert {issue for issue, _ in exact_candidates(earlier).values()} == {"first", "revised"}


def test_latest_earliest_latest_preserves_view_coverage_and_all_candidates():
    policy = ordered("first", "revised", expected_issues=("first", "revised"))
    original = (part("first", 1), part("revised", 2))
    latest, _ = resolve_revisions(original, policy)
    earlier, _ = resolve_revisions((latest,), replace(policy, as_of="first"))
    assert not earlier.assessment.complete
    later, _ = resolve_revisions((earlier,), policy)
    assert later.rows == latest.rows
    assert later.assessment == latest.assessment
    assert later.history_membership.candidates == latest.history_membership.candidates
    assert later.history_membership.rows == latest.history_membership.rows


def test_a_new_policy_recomputes_view_expectations_without_erasing_source_limits():
    history, _ = resolve_revisions((part("first"),), RevisionPolicy(expected_issues=("first", "missing")))
    assert not history.assessment.complete
    changed, _ = resolve_revisions((history,), RevisionPolicy(expected_issues=("first",)))
    assert changed.assessment.complete
    partial_source = replace(part("first"), assessment=Assessment("partial", ("unreviewed source geometry",)))
    partial, _ = resolve_revisions((partial_source,), RevisionPolicy())
    repeated, _ = resolve_revisions((partial,), RevisionPolicy())
    assert not repeated.assessment.complete
    assert "unreviewed source geometry" in repeated.assessment.findings


def test_disjoint_merge_resolution_equivalence_includes_provenance_and_coverage():
    policy = ordered("first", "revised")
    left, _ = resolve_revisions((part("first", 1), part("revised", 2)), policy)
    right, _ = resolve_revisions((part("first", 3, period="2026-02"),
        part("revised", 4, period="2026-02")), policy)
    earlier = replace(policy, as_of="first")
    combined, _ = resolve_revisions((merge_histories((left, right)),), earlier)
    parts = tuple(resolve_revisions((item,), earlier)[0] for item in (left, right))
    separate = merge_histories(parts)
    assert combined.rows == separate.rows
    assert combined.history_membership.candidates == separate.history_membership.candidates
    assert combined.history_membership.revisions == separate.history_membership.revisions
    assert combined.assessment.complete == separate.assessment.complete
    assert combined.history_membership.missing_expectations == separate.history_membership.missing_expectations


def test_coordinate_projection_never_resurrects_an_excluded_period():
    policy = ordered("first", "revised")
    history, _ = resolve_revisions((part("first", 1), part("revised", 2),
        part("first", 10, period="2026-02"), part("revised", 20, period="2026-02")), policy)
    selected = select_observations(history, ObservationQuery(periods=("2026-01",)))
    old, _ = resolve_revisions((selected,), replace(policy, as_of="first"))
    new, _ = resolve_revisions((old,), policy)
    assert [row["value"] for row in old.rows] == [1]
    assert [row["value"] for row in new.rows] == [2]
    assert {row.value["period"] for row in new.history_membership.rows} == {"2026-01"}
    assert new.history_membership.selection_scopes
    assert new.assessment.coverage.parent_identity == history.identity


def test_value_filter_is_literal_and_reselection_is_explicit():
    policy = ordered("first", "revised")
    latest, _ = resolve_revisions((part("first", -1), part("revised", 1)), policy)
    selected = select_observations(latest, ObservationQuery(filters={"value": (Decimal(1),)}))
    earlier, _ = resolve_revisions((selected,), replace(policy, as_of="first"))
    assert earlier.rows[0]["value"] == -1
    reapplied = select_observations(earlier, ObservationQuery(filters={"value": (Decimal(1),)}))
    assert not reapplied.rows
    repeated, _ = resolve_revisions((reapplied,), policy)
    assert not repeated.rows and repeated.assessment.complete


def test_exact_candidate_union_is_idempotent_but_strict_merge_rejects_equal_overlap():
    original = part("first")
    once, _ = resolve_revisions((original,), RevisionPolicy())
    twice, _ = resolve_revisions((original, original, once), RevisionPolicy(equal_duplicates="reject"))
    assert twice.history_membership.candidates == once.history_membership.candidates
    assert len(twice.history_membership.members) == 1
    with pytest.raises(ValueError, match="duplicate_grain"):
        merge_histories((once, once))


def test_second_validation_rule_adds_witness_without_changing_candidates():
    first = qualify(part("first"), "rule.one")
    second = qualify(first, "rule.two")
    assert dataset_content_identity(first) == dataset_content_identity(second)
    history, _ = resolve_revisions((first, second), RevisionPolicy())
    assert len(history.history_membership.members) == 1
    assert len(history.history_membership.candidates) == 1
    assert len(history.history_membership.members[0].certificate_ids) == 2
    second_id = second.validation_certificates[-1].identity
    assert verify_history_certificates(history, lambda certificate: certificate.identity == second_id)


def test_same_issue_revisions_need_explicit_qualified_revision_keys():
    first_key = PublicationRevision("source", "report", "initial")
    second_key = PublicationRevision("source", "report", "correction")
    first = bind_publication_revision(part("report", 1), first_key)
    second = bind_publication_revision(part("report", 2), second_key)
    with pytest.raises(ValueError, match="ambiguous_same_revision"):
        resolve_revisions((first, second), ordered("report"))
    policy = RevisionPolicy(conflicts="latest", ordered_revisions=(first_key.identity, second_key.identity),
        ordering_basis="publisher.correction_notices")
    latest, _ = resolve_revisions((first, second), policy)
    earlier, _ = resolve_revisions((latest,), replace(policy, as_of=first_key.identity))
    assert latest.rows[0]["value"] == 2 and earlier.rows[0]["value"] == 1


def test_different_values_at_one_qualified_revision_remain_ambiguous():
    key = PublicationRevision("source", "report", "initial")
    policy = RevisionPolicy(conflicts="latest", ordered_revisions=(key.identity,), ordering_basis="publisher.notice")
    with pytest.raises(ValueError, match="ambiguous_same_revision"):
        resolve_revisions(tuple(bind_publication_revision(part("report", value), key) for value in (1, 2)), policy)


def test_a_b_a_occurrences_share_payloads_without_collapsing_evidence():
    keys = tuple(PublicationRevision("source", "report", revision, occurrence_id=str(index))
        for index, revision in enumerate(("A", "B", "A")))
    datasets = tuple(bind_publication_revision(part("report", value), key)
        for value, key in zip((1, 2, 1), keys))
    policy = RevisionPolicy(conflicts="latest", ordered_revisions=tuple(key.identity for key in keys),
        ordering_basis="installation.observation_order")
    history, _ = resolve_revisions(datasets, policy)
    assert len(history.history_membership.members) == 3
    assert len(history.history_membership.candidates) == 3
    assert len(history.history_membership.rows) == 2
    middle, _ = resolve_revisions((history,), replace(policy, as_of=keys[1].identity))
    assert middle.rows[0]["value"] == 2
    last, _ = resolve_revisions((middle,), policy)
    assert last.rows[0]["value"] == 1


def test_expectations_do_not_borrow_same_issue_from_another_source_or_asset():
    expectations = (HistoryExpectation("source", "report", "main"),
        HistoryExpectation("source", "report", "annex"), HistoryExpectation("other", "report"))
    history, _ = resolve_revisions((part("report", asset="main"),), RevisionPolicy(expected_members=expectations))
    missing = history.history_membership.missing_expectations
    assert {(item.source_id, item.asset_id) for item in missing} == {("source", "annex"), ("other", "")}
    assert not history.assessment.complete


def test_revision_asset_binding_cannot_replace_source_content_scope():
    with pytest.raises(ValueError, match="revision_asset_mismatch"):
        bind_publication_revision(part("report", asset="main"), PublicationRevision("source", "report", "v1", "annex"))


def test_declared_missing_selected_coordinate_stays_missing_through_resolution():
    missing = observation_key(part("first", period="2026-02").rows[0])
    selected = select_observations(part("first"), ObservationQuery(expected_members=(missing,)))
    repeated, _ = resolve_revisions((selected,), RevisionPolicy())
    assert repeated.history_membership.missing_coordinates == (missing,)
    assert not repeated.assessment.complete
    assert repeated.assessment.coverage.missing == (missing,)


def test_merge_keeps_selected_parent_evidence_without_reopening_coordinates():
    history = merge_histories((part("first"), part("second", period="2026-02")))
    selected = select_observations(history, ObservationQuery(periods=("2026-01",)))
    merged = merge_histories((selected, part("third", period="2026-03")))
    assert merged.history_membership.selection_scopes == selected.history_membership.selection_scopes
    assert {row.value["period"] for row in merged.history_membership.rows} == {"2026-01", "2026-03"}


@pytest.mark.parametrize("field,value,error", (
    ("max_candidates", 1, "candidate_limit"),
    ("max_members", 1, "member_limit"),
    ("max_payload_bytes", 1, "payload_limit"),
    ("max_encoded_bytes", 1, "encoded_limit"),
    ("max_witnesses", 1, "witness_limit"),
))
def test_limits_bound_hidden_evidence_even_with_one_displayed_row(field, value, error):
    limits = replace(HistoryLimits(), **{field: value})
    with pytest.raises(ValueError, match=error):
        resolve_revisions((qualify(part("first")), qualify(part("revised"))), RevisionPolicy(limits=limits))


def test_projection_preserves_custom_limits_and_rejects_forged_visible_values():
    policy = RevisionPolicy(limits=replace(HistoryLimits(), max_candidates=5))
    history, _ = resolve_revisions((part("first"),), policy)
    selected = select_observations(history, ObservationQuery())
    assert selected.history_membership.limits.max_candidates == 5
    forged = replace(history, rows=({**history.rows[0], "value": 999},))
    with pytest.raises(ValueError, match="view_binding_mismatch"):
        resolve_revisions((forged,), RevisionPolicy())
    with pytest.raises(ValueError, match="semantic_binding_mismatch"):
        validate_history_view(replace(history, semantics={"unit": "USD"}))


def test_economic_fields_cannot_be_declared_as_display_provenance():
    with pytest.raises(ValueError, match="economic_field_is_not_provenance"):
        RevisionPolicy(provenance_fields=("value",))


def test_empty_original_preserves_scientific_limits_and_publication_presence():
    original = SourceDataset("source", (), issue_id="empty", assessment=Assessment("partial", ("unobserved rows",)))
    result, _ = resolve_revisions((original,), RevisionPolicy(expected_issues=("empty",)))
    assert not result.history_membership.missing_issues
    assert not result.assessment.complete
    assert "unobserved rows" in result.assessment.findings


def test_optional_native_acceleration_is_not_a_history_or_selection_authority():
    original = replace(part("first"), native=object())
    history, _ = resolve_revisions((original,), RevisionPolicy())
    selected = select_observations(original, ObservationQuery())
    assert history.native is None and selected.native is None
    assert history.rows == selected.rows == original.rows
    assert selected.assessment.coverage.parent_identity == replace(original, native=None).identity


def test_certificate_dependencies_follow_retained_candidate_scope_without_granting_authority():
    january, february = qualify(part("first")), qualify(part("second", period="2026-02"))
    history = merge_histories((january, february))
    selected = select_observations(history, ObservationQuery(periods=("2026-01",)))
    assert history_certificate_dependencies(january) == (january.validation_certificates[0].identity,)
    assert len(history_certificate_dependencies(history)) == 2
    assert history_certificate_dependencies(selected) == (january.validation_certificates[0].identity,)
    assert not verify_history_certificates(selected, lambda certificate: False)


def test_empty_selected_history_does_not_turn_untrusted_certificate_into_authority():
    original = qualify(part("first"))
    selected = select_observations(original, ObservationQuery(metrics=()))
    assert selected.rows == ()
    assert not verify_history_certificates(selected, lambda certificate: False)
    assert verify_history_certificates(selected, lambda certificate: True)
    assert history_certificate_dependencies(selected) == history_certificate_dependencies(original)
    empty = qualify(SourceDataset("source", (), issue_id="empty"))
    history, _ = resolve_revisions((empty,), RevisionPolicy())
    assert verify_history_certificates(history, lambda certificate: True)
