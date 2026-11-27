"""Bounded retention, conditional named delivery and qualified reconciliation."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from stratbox.core.execution.service import ExecutionFailure
from stratbox.core.execution.errors import error_code
from stratbox.core.storage.filestore import MutationRejected
from stratbox.core.storage.readable import copy_stream
from stratbox.shared.data.materials import NamedEffectIntent, NamedMaterialReceipt
from stratbox.shared.data.values import Assessment, ImmutableMaterialRef, fingerprint
from stratbox.shared.identity import ByteIdentity
from ._physical import material_properties, open_material, physical_material
from ._settings import _option
from ._storage import _compact_reference, _provider_scope, _read_identity, _same_physical_reference


def _unique(values):
    selected, seen = [], set()
    for value in values:
        identity = fingerprint(value)
        if identity not in seen:
            selected.append(value)
            seen.add(identity)
    return tuple(selected)


def _destination(value):
    if value is None or not str(value) or "\x00" in str(value):
        raise ExecutionFailure("storage.destination_required")
    return str(value)


def _settled(receipt, prefix="storage"):
    if receipt.status != "confirmed":
        raise ExecutionFailure(prefix + "." + receipt.status,
                               outcome="unknown" if receipt.status == "unknown" else "failed")


def _copy_source(value, stream, context, identity):
    with open_material(value, context) as source:
        return copy_stream(source, stream, expected=identity, limit=identity.size,
            checkpoint=context.checkpoint, budget=getattr(context, "budget", None), resource="temporary_bytes")


def artifact_commit(inputs, settings, context):
    value, store = inputs["material"], context.provider("filestore")
    material, properties = physical_material(value), material_properties(value)
    identity = material.identity
    destination = _destination(inputs.get("destination") or _option(context, settings, "destination"))
    if not getattr(store, "immutable_content", False) or not callable(getattr(store, "stage_content", None)):
        raise ExecutionFailure("storage.streaming_immutable_provider_required")
    if identity.size > _option(context, settings, "max_bytes", 64 * 1024**3):
        raise ExecutionFailure("storage.output_limit")
    path = str(Path(destination) / identity.sha256)
    scope = _provider_scope(store, path)
    accepted = context.accepted_input("material")
    effect_id = fingerprint(("storage.write", scope, path, identity))
    repair_id = _option(context, settings, 'repair_id', None)
    if repair_id is not None:
        if not isinstance(repair_id, str) or not repair_id or len(repair_id) > 1024:
            raise ExecutionFailure('storage.repair_identity_invalid')
        previous = context.service.lookup_effect(effect_id)
        if (previous is None or previous.status != 'confirmed' or previous.kind != 'storage.write'
                or not isinstance(previous.intent, ImmutableMaterialRef)
                or previous.intent.identity != identity or previous.intent.location != path
                or previous.intent.provider_scope != scope):
            raise ExecutionFailure('storage.confirmed_repair_basis_required')
        # An availability repair is a new physical occurrence. The old receipt
        # stays a historical confirmation even if its former bytes disappeared.
        effect_id = fingerprint(('storage.repair', effect_id, repair_id))
    if getattr(context, "budget", None):
        context.budget.account_output(effect_id, identity)
    metadata = {**properties["metadata"], "media_type": getattr(material, "media_type", "application/octet-stream"),
        "charset": getattr(material, "charset", None), "source_id": properties["source_id"]}
    reference = ImmutableMaterialRef(path, identity, str(getattr(store, "provider_id", "filestore")),
        _unique((*properties["lineage"], *(accepted["basis"] if accepted else ()))),
        accepted_value_id=accepted["id"] if accepted else None, effect_id=effect_id, provider_scope=scope,
        source_uses=_unique((*properties["source_uses"], *(accepted["source_uses"] if accepted else ()))),
        metadata=metadata, assessment=getattr(value, "assessment", None) or getattr(material, "assessment", None))

    def action():
        with store.stage_content(destination) as stage:
            if not callable(getattr(stage, "location", None)) or stage.location(identity) != path:
                raise MutationRejected("Unqualified content address", code="storage.retained_location_conflict")
            try:
                _copy_source(value, stage.stream, context, identity)
            except Exception as error:
                # Only private staging has changed here. The immutable commit
                # has not been attempted, so a copy failure is known rejection.
                raise MutationRejected("Input could not be copied and verified", code=error_code(error)) from error
            if stage.commit(identity, checkpoint=context.checkpoint) != path:
                raise ExecutionFailure("storage.retained_location_conflict")
        if _read_identity(store, path, identity, checkpoint=context.checkpoint) != identity:
            raise ExecutionFailure("storage.identity_mismatch")
        return reference

    receipt = context.effect("storage.write", effect_id, action, resource=path, intent=reference)
    _settled(receipt)
    if not _same_physical_reference(receipt.value, receipt.intent):
        raise ExecutionFailure("storage.retention_receipt_conflict")
    # The durable receipt keeps its original accepted provenance when a later
    # logical caller reuses the same physical storage obligation.
    try:
        available = _read_identity(store, path, identity, checkpoint=context.checkpoint) == identity
    except (OSError, ValueError):
        available = False
    if not available:
        raise ExecutionFailure("storage.retained_postcondition_changed")
    return {"reference": receipt.value, "receipt": receipt}


def _missing(store, path):
    stat = getattr(store, "stat", None)
    if not callable(stat):
        raise ExecutionFailure("storage.existence_observation_required")
    try:
        stat(path)
    except FileNotFoundError:
        return True
    return False


def _verified_ancestor(reference, identity, context):
    if not isinstance(reference, ImmutableMaterialRef) or reference.identity != identity:
        raise ExecutionFailure("storage.retained_ancestor_identity_mismatch")
    with open_material(reference, context):
        pass
    return reference


def _copy_named(value, intent, context, *, update_intent=None, source_opener=None, effect_id=None):
    store = context.provider("filestore")
    validate = getattr(store, "validate_named_destination", None)
    if callable(validate):
        validate(intent.destination)
    if not callable(getattr(store, "stage_write", None)):
        raise ExecutionFailure("storage.conditional_staging_required")
    if intent.policy == "create_only":
        try:
            existing = _read_identity(store, intent.destination, intent.identity,
                                      checkpoint=context.checkpoint)
        except FileNotFoundError:
            existing = None
        except ValueError as error:
            raise MutationRejected("Destination differs from the requested bytes",
                                   code="storage.destination_conflict") from error
        if existing is not None:
            if existing != intent.identity:
                raise MutationRejected("Destination contains other bytes", code="storage.destination_conflict")
            return NamedMaterialReceipt(intent.destination, intent.identity, intent.provider_scope,
                guarantee="verified_existing_postcondition")
    revision = intent.expected_destination_revision
    if intent.policy == "replace_if_matches":
        inspect = getattr(store, "inspect_file", None)
        if not callable(inspect) or not callable(getattr(store, "guard_directory", None)):
            raise ExecutionFailure("storage.conditional_provider_required")
        try:
            observed = inspect(intent.destination)
        except FileNotFoundError:
            raise MutationRejected("Expected destination is absent", code="storage.destination_conflict") from None
        if observed.identity != intent.expected_destination or revision is not None and observed.revision != revision:
            raise MutationRejected("Destination changed", code="storage.destination_conflict")
        revision = observed.revision
        if update_intent is not None:
            intent = replace(intent, expected_destination_revision=revision)
            update_intent(intent)
    with store.stage_write(intent.destination) as stage:
        try:
            if source_opener is None:
                _copy_source(value, stage.stream, context, intent.identity)
            else:
                # Maintenance supplies an identity-qualified local
                # source; named delivery still owns the one atomic writer.
                with source_opener() as source:
                    copy_stream(source, stage.stream, expected=intent.identity,
                        limit=intent.identity.size, checkpoint=context.checkpoint,
                        budget=getattr(context, "budget", None), resource="temporary_bytes")
        except Exception as error:
            raise MutationRejected("Input could not be copied and verified", code=error_code(error)) from error
        created = stage.commit("immutable" if intent.policy == "create_only" else "replace_expected_revision", revision)
    if not isinstance(created, bool):
        raise ExecutionFailure("storage.commit_protocol_invalid")
    if not created and intent.policy == 'replace_if_matches':
        raise MutationRejected('Conditional replacement rejected', code='storage.destination_conflict')
    try:
        actual = _read_identity(store, intent.destination, intent.identity, checkpoint=context.checkpoint)
    except (OSError, ValueError) as error:
        if not created:
            raise MutationRejected("Destination differs from the requested bytes", code="storage.destination_conflict") from error
        raise
    if actual != intent.identity:
        if not created:
            raise MutationRejected("Destination contains other bytes", code="storage.destination_conflict")
        raise ExecutionFailure("storage.named_readback_mismatch")
    receipt = NamedMaterialReceipt(intent.destination, intent.identity, intent.provider_scope,
        guarantee=("atomic_create" if intent.policy == "create_only" else "compare_and_replace_under_directory_guard")
                  if created else "verified_existing_postcondition")
    record = getattr(store, 'record_named_transition', None)
    if intent.policy == 'replace_if_matches' and effect_id is not None and callable(record):
        try:
            record(effect_id, intent, receipt)
        except Exception as error:
            raise OSError('Conditional replacement acknowledgement is unavailable') from error
    return receipt


def artifact_materialize(inputs, settings, context):
    value, store = inputs["material"], context.provider("filestore")
    material = physical_material(value)
    destination = _destination(inputs.get("destination") or _option(context, settings, "destination"))
    policy = _option(context, settings, "policy", "create_only")
    if not callable(getattr(store, "stage_write", None)):
        raise ExecutionFailure("storage.conditional_staging_required")
    validate = getattr(store, "validate_named_destination", None)
    if callable(validate):
        validate(destination)
    expected = inputs.get("expected_destination", _option(context, settings, "expected_destination", None))
    if policy not in {"create_only", "replace_if_matches"} or (policy == "replace_if_matches" and not isinstance(expected, ByteIdentity)):
        raise ExecutionFailure("storage.conditional_policy_required")
    if policy == "create_only" and expected is not None:
        raise ExecutionFailure("storage.create_only_precondition_conflict")
    if material.identity.size > _option(context, settings, "max_bytes", 64 * 1024**3):
        raise ExecutionFailure("storage.output_limit")
    ancestor = inputs.get("retained_ancestor", material if isinstance(material, ImmutableMaterialRef) else None)
    if ancestor is not None:
        ancestor = _compact_reference(_verified_ancestor(ancestor, material.identity, context))
    scope = _provider_scope(store, destination)
    intent = NamedEffectIntent("copy", scope, destination, material.identity,
        source=ancestor.location if ancestor is not None else None,
        expected_source=material.identity, expected_destination=expected, policy=policy,
        retained_ancestor=ancestor, source_provider_scope=ancestor.provider_scope if ancestor is not None else None)
    delivery_id = _option(context, settings, "delivery_id", context.run_id)
    effect_id = fingerprint(("named.copy", intent, delivery_id))
    if getattr(context, "budget", None):
        context.budget.account_output(effect_id, material.identity)
    receipt = context.effect("storage.write", effect_id,
        lambda: _copy_named(value, intent, context,
            update_intent=lambda enriched: context.update_effect_intent(effect_id, enriched), effect_id=effect_id),
        resource=destination, intent=intent)
    _settled(receipt)
    if _read_identity(store, destination, material.identity, checkpoint=context.checkpoint) != material.identity:
        raise ExecutionFailure("storage.named_postcondition_changed")
    return {"receipt": receipt}


def _named_observation(effect_id, intent, context):
    store = context.provider("filestore")
    if intent.provider_scope != _provider_scope(store, intent.destination):
        return None
    if intent.source is not None and intent.source_provider_scope is not None and intent.source_provider_scope != _provider_scope(store, intent.source):
        return None
    if intent.operation in {"copy", "move"}:
        try:
            if _read_identity(store, intent.destination, intent.identity, checkpoint=context.checkpoint) != intent.identity:
                return None
        except (OSError, ValueError):
            return None
    if intent.operation == "copy" and intent.policy == 'create_only':
        return NamedMaterialReceipt(intent.destination, intent.identity, intent.provider_scope,
                                    guarantee="verified_current_postcondition")
    if intent.operation in {'move', 'delete'} and not _missing(store, intent.source):
        return None
    if intent.prerequisites:
        from .maintenance import _verify_prerequisites
        _verify_prerequisites(intent.prerequisites, context)
    known = context.service.lookup_effect(effect_id)
    if known is not None and known.status == "confirmed" and isinstance(known.value, NamedMaterialReceipt):
        proof = known.value
        if (proof.operation, proof.destination, proof.provider_scope, proof.identity) == (
                intent.operation, intent.destination, intent.provider_scope, intent.identity):
            return proof
    lookup = getattr(store, "inspect_named_transition", None)
    if not callable(lookup):
        return None
    proof = lookup(effect_id, intent)
    if (not isinstance(proof, NamedMaterialReceipt) or proof.operation != intent.operation
            or proof.destination != intent.destination or proof.provider_scope != intent.provider_scope
            or proof.identity != intent.identity):
        return None
    return proof


def artifact_reconcile(inputs, settings, context):
    submitted, provider = inputs["effect"], context.provider("filestore")
    effect_id = getattr(submitted, "effect_id", None)
    known = context.service.lookup_effect(effect_id) if effect_id else None
    if known is None or known.kind != "storage.write":
        raise ExecutionFailure("storage.effect_not_found")
    expected = known.intent

    def lookup(_):
        if isinstance(expected, ImmutableMaterialRef):
            if not getattr(provider, "immutable_content", False) or expected.provider_scope != _provider_scope(provider, expected.location):
                return None
            try:
                actual = _read_identity(provider, expected.location, expected.identity, checkpoint=context.checkpoint)
            except (OSError, ValueError):
                return None
            return expected if actual == expected.identity else None
        if isinstance(expected, NamedEffectIntent):
            return _named_observation(effect_id, expected, context)
        return None

    observed = lookup(effect_id)
    if _option(context, settings, 'retry_missing', False):
        raise ExecutionFailure('storage.explicit_repair_occurrence_required')
    if observed is not None:
        recovered = context.service.reconcile_effect(effect_id, lambda _: observed, context=context)
        complete = recovered.status == "confirmed"
    else:
        complete = False
    qualification = "exact_immutable_readback" if isinstance(expected, ImmutableMaterialRef) else "provider_qualified_named_postcondition"
    return {"assessment": Assessment("complete" if complete else "indeterminate",
        findings=() if complete else ("storage.postcondition_unresolved",),
        qualifications=frozenset({qualification}) if complete else frozenset())}
