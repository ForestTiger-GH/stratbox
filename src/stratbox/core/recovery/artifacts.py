"""Explicit immutable dependency restoration with its own durable occurrence."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from stratbox.shared.data.values import ImmutableMaterialRef, SnapshotRef, restore_tree, fingerprint
from stratbox.shared.identity import ByteIdentity
from stratbox.core.storage.readable import open_provider, scan_identity, copy_stream
from .packages import RecoveryLimits, validate_recovery_package, _relative, _file_identity


def restore_recovery_artifacts(directory, *, providers, state_directory, occurrence_id, limits=None):
    """Fulfil backed-up immutable dependencies in their original provider scopes.

    ``occurrence_id`` is explicit authorization for this restoration occurrence.
    A separate durable ledger records it; the original historical effect ledger
    is untouched. Unknown restoration attempts may replay only the qualified
    immutable create-if-absent operation. Named delivery destinations are absent
    from this protocol and require their ordinary explicit repair operation.
    """
    from stratbox.core.execution.service import EffectReceipt
    from stratbox.core.execution.effect_state import FileEffectState
    from stratbox.core.execution.effect_evidence import admit_evidence, evidence_summary
    from stratbox.core.commands._storage import _provider_scope
    if not isinstance(occurrence_id, str) or not occurrence_id or len(occurrence_id) > 1024:
        raise ValueError('recovery.occurrence_required')
    root, limits = Path(directory).resolve(), limits or RecoveryLimits()
    manifest = validate_recovery_package(root, limits=limits)
    ledger = FileEffectState(state_directory)
    restored = existing = count = size = 0
    with (root / 'dependencies.jsonl').open('rb') as index:
        while raw := index.readline(1024**2 + 1):
            count += 1; size += len(raw)
            if len(raw) > 1024**2 or count > limits.max_files or size > limits.max_index_bytes:
                raise ValueError('recovery.dependency_index_limit')
            item = json.loads(raw)
            reference = restore_tree(item['reference'])
            expected = ByteIdentity(item['sha256'], item['size'])
            incoming = _relative(root, item['path'])
            if _file_identity(incoming, limits.max_file_bytes) != expected:
                raise ValueError('recovery.dependency_identity_conflict')
            dataset_provider = None
            if isinstance(reference, ImmutableMaterialRef):
                provider = providers.get('filestore')
                if (provider is None or reference.provider_scope != _provider_scope(provider, reference.location)
                        or expected != reference.identity):
                    raise ValueError('recovery.artifact_scope_mismatch')
                location = reference.location
            elif isinstance(reference, SnapshotRef):
                dataset_provider = providers.get('datasets')
                if (dataset_provider is None or reference.provider_id != getattr(dataset_provider, 'provider_id', None)
                        or reference.provider_scope != getattr(dataset_provider, 'scope_id', None)):
                    raise ValueError('recovery.dataset_scope_mismatch')
                provider, location = getattr(dataset_provider, 'store', None), reference.snapshot_id
            else:
                raise ValueError('recovery.reference_invalid')
            if (not getattr(provider, 'immutable_content', False)
                    or not callable(getattr(provider, 'stage_write', None))
                    or Path(location).name != expected.sha256):
                raise ValueError('recovery.immutable_restore_provider_required')
            effect_id = fingerprint(('recovery.immutable.restore', manifest['package_id'], occurrence_id,
                                     fingerprint(reference)))
            if isinstance(reference, ImmutableMaterialRef):
                action_reference = replace(reference, effect_id=effect_id)
                effect_kind, intent = 'storage.write', action_reference
            else:
                action_reference = reference
                effect_kind, intent = 'dataset.write', {'provider_id': reference.provider_id,
                    'provider_scope': reference.provider_scope, 'identity': reference.identity,
                    'destination': reference.snapshot_id}
            claim, fresh = ledger.begin(EffectReceipt(effect_id, effect_kind, 'unknown',
                                                      resource=str(location), intent=intent))
            if claim.status == 'confirmed':
                try:
                    with open_provider(provider, location) as stream:
                        actual = scan_identity(stream, limit=expected.size)
                except FileNotFoundError:
                    raise ValueError('recovery.new_restore_occurrence_required') from None
                if actual != expected:
                    raise ValueError('recovery.new_restore_occurrence_required')
                existing += 1
                continue
            # Atomic immutable creation makes replay safe even if a process died
            # after creation and before receipt settlement. No overwrites occur.
            with incoming.open('rb') as source, provider.stage_write(location) as stage:
                copy_stream(source, stage.stream, expected=expected, limit=expected.size)
                created = stage.commit('immutable', None)
                if type(created) is not bool:
                    raise ValueError('recovery.commit_acknowledgement_invalid')
            with open_provider(provider, location) as stream:
                if scan_identity(stream, limit=expected.size) != expected:
                    raise ValueError('recovery.immutable_content_conflict')
            if dataset_provider is not None:
                dataset_provider.query(reference, None)
            admitted = admit_evidence(claim, action_reference, source='action')
            if admitted.outcome != 'confirmed':
                raise ValueError(admitted.finding or 'recovery.receipt_not_admitted')
            ledger.put(replace(claim, status='confirmed', value=admitted.value,
                               evidence=evidence_summary(admitted.evidence)))
            ledger.archive((effect_id,))
            restored += int(created)
            existing += int(not created)
    return {'package_id': manifest['package_id'], 'occurrence_id': occurrence_id,
            'restored': restored, 'already_present': existing, 'ledger_scope_id': ledger.scope_id}
