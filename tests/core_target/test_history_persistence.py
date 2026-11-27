"""Portable history replay admits exact views and refuses missing evidence."""
from dataclasses import replace
from decimal import Decimal

import pytest

from stratbox.core.storage.datasets.stores import FileDatasetStore, MemoryDatasetStore
from stratbox.shared.data.history import (HistoryCandidate, HistoryRow, RevisionPolicy,
    make_validation_certificate, merge_histories, resolve_revisions, verify_history_certificates)
from stratbox.shared.data.selection import ObservationQuery, select_observations
from stratbox.shared.data.values import SourceDataset, canonical_tree, fingerprint, restore_tree


def history():
    datasets = []
    for issue, value in (("first", 1), ("revised", 2)):
        dataset = SourceDataset("source", ({"period": "2026-01", "metric": "x", "value": Decimal(value),
            "source_issue": issue},), issue_id=issue)
        certificate = make_validation_certificate(dataset, rule_id="reviewed.source", method_identity="method", build_identity="build")
        datasets.append(replace(dataset, validation_certificates=(certificate,)))
    policy = RevisionPolicy(conflicts="latest", ordered_issues=("first", "revised"), ordering_basis="publisher.order")
    return resolve_revisions(tuple(datasets), policy)[0], policy


@pytest.mark.parametrize("provider", ("memory", "file"))
def test_retained_selected_history_round_trip_reconstructs_exact_vintage(tmp_path, provider):
    original, policy = history()
    selected = select_observations(original, ObservationQuery(periods=("2026-01",)))
    store = MemoryDatasetStore(scope_id="history") if provider == "memory" else FileDatasetStore(tmp_path)
    reference = store.ingest(selected, destination="histories", identity=fingerprint(selected))
    if provider == "file":
        store = FileDatasetStore(tmp_path)
    restored = store.query(reference, None)
    assert restored == selected
    assert restored.native is None
    earlier, _ = resolve_revisions((restored,), replace(policy, as_of="first"))
    assert earlier.rows[0]["value"] == 1 and earlier.rows[0]["source_issue"] == "first"
    trusted = {certificate.identity for certificate in original.validation_certificates}
    assert verify_history_certificates(earlier, lambda certificate: certificate.identity in trusted)
    assert not verify_history_certificates(earlier, lambda certificate: False)


def test_portable_replay_rejects_a_view_that_disagrees_with_its_ledger():
    original, _ = history()
    forged = replace(original, rows=({**original.rows[0], "value": 999},))
    with pytest.raises(ValueError, match="view_binding_mismatch"):
        restore_tree(canonical_tree(forged))


def test_old_membership_envelope_requires_explicit_cutover():
    original, _ = history()
    tree = canonical_tree(original)
    del tree["fields"]["history_membership"]["fields"]["schema"]
    with pytest.raises(ValueError, match="unsupported_schema"):
        restore_tree(tree)


def test_declared_unknown_history_schema_is_rejected():
    original, _ = history()
    tree = canonical_tree(original)
    tree["fields"]["history_membership"]["fields"]["schema"] = "history.old.lossy"
    with pytest.raises(ValueError, match="unsupported_schema"):
        restore_tree(tree)


def test_row_and_candidate_ids_are_verified_on_construction():
    with pytest.raises(ValueError, match="row_identity_mismatch"):
        HistoryRow({"value": 1}, "caller-invented-id")
    with pytest.raises(ValueError, match="candidate_identity_mismatch"):
        HistoryCandidate("member", "coordinate", "row", 0, "caller-invented-id")


def test_missing_alternative_reference_cannot_restore_as_complete_history():
    original, _ = history()
    ledger = original.history_membership
    with pytest.raises(ValueError, match="decision_evidence_incomplete"):
        replace(ledger, revisions=(replace(ledger.revisions[0], alternative_candidates=()),))


def test_member_witness_cannot_be_borrowed_from_another_equal_coordinate():
    original, _ = history()
    ledger = original.history_membership
    first, second = ledger.members
    replaced = replace(ledger, members=(replace(first, certificate_ids=second.certificate_ids), second))
    forged = replace(original, history_membership=replaced)
    assert not verify_history_certificates(forged, lambda certificate: True)


def test_changed_row_identity_cannot_reuse_a_competent_certificate():
    original, _ = history()
    # Even a structurally consistent newly built ledger has no authority for a
    # changed value merely because the old certificate was copied onto it.
    changed = SourceDataset("source", ({"period": "2026-01", "metric": "x", "value": Decimal(999)},),
        issue_id="first", validation_certificates=original.validation_certificates)
    result, _ = resolve_revisions((changed,), RevisionPolicy())
    assert not verify_history_certificates(result, lambda certificate: True)
