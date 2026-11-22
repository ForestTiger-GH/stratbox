"""Verified I/O independent of a domain and of the role of a serialized value."""
from stratbox.core.execution import Completion, OperationFailure, run
from stratbox.core.operations.source.original_definitions import OriginalDestination
from stratbox.core.operations.source.originals import _copy_material, _store, _stored_completion, read_material
from stratbox.core.storage.bytes import read_bounded_bytes
from stratbox.core.storage.staging import current_revision, storage_scope, store_identity
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import MaterialReference, SourcePayload, UsedInputReceipt
from stratbox.shared.materials import ArtifactReference, MAX_DESCRIPTOR_BYTES, MaterialArtifact, restore_artifact

from . import definitions as D


def _selections(**roles):
    return {role: value for role, value in roles.items() if value is not None}


def _addressable(store):
    # Durable references require a real provider namespace and location scope.
    if not isinstance(getattr(store, "store_id", None), str) or not store.store_id or not callable(getattr(store, "storage_scope", None)):
        raise OperationFailure("provider.addressable_store_required")


def read_location(request: D.ReadLocationRequest, *, store=None, selection=None, context=None):
    def work(req, invocation):
        reader = invocation.provider("filestore", store)
        _addressable(reader)
        if (not isinstance(req.locator, str) or not req.locator or "\x00" in req.locator
                or type(req.limit) is not int or not 0 <= req.limit <= D.MAX_BYTES):
            raise OperationFailure("input.location_invalid")
        invocation.stage("read_location")
        try:
            before = current_revision(reader, req.locator)
            if req.expected_revision is not None and before != req.expected_revision:
                raise OperationFailure("input.material_version_changed")
            data = read_bounded_bytes(req.locator, store=reader, limit=req.limit,
                                      budget=invocation.budget, checkpoint=invocation.check_cancelled)
            if before != current_revision(reader, req.locator):
                raise OperationFailure("input.material_version_changed")
            payload = SourcePayload(data, req.media_type, req.source_id, charset=req.charset)
            if req.expected_identity is not None and payload.identity != req.expected_identity:
                raise OperationFailure("input.identity_mismatch")
            ref = MaterialReference(req.locator, store_identity(reader), payload.identity, payload.media_type,
                                    payload.source_id, before, payload.charset, storage_scope(reader, req.locator))
        except ValueError:
            raise OperationFailure("input.material_invalid") from None
        except OSError:
            raise OperationFailure("input.material_unavailable") from None
        invocation.use(UsedInputReceipt.for_payload(payload, "material"))
        invocation.account_output(payload.identity)
        return D.LocatedMaterial(payload, ref)
    return run(D.READ_LOCATION, request, work, context=context, providers={"filestore": store},
               provider_selections=_selections(filestore=selection))


def transfer_material(request: D.TransferMaterialRequest, *, source_store=None, output_store=None,
                      source_selection=None, output_selection=None, context=None):
    def work(req, invocation):
        reader = invocation.provider("filestore", source_store)
        writer = invocation.provider("output_filestore", output_store)
        _addressable(reader)
        _addressable(writer)
        def produce(sink):
            _copy_material(req.material, reader, invocation, sink)
            item = req.material
            invocation.use(UsedInputReceipt("material", item.identity, item.media_type, "reference_only", item.source_id))
            return item.identity, item.media_type, item.source_id, item.charset, None
        return _stored_completion(_store(invocation, req.destination, writer, produce))
    return run(D.TRANSFER, request, work, context=context,
               providers={"filestore": source_store, "output_filestore": output_store},
               provider_selections=_selections(filestore=source_selection, output_filestore=output_selection))


def _bytes(data, media_type, source_id, target, writer, invocation, charset=None):
    payload = SourcePayload(data, media_type, source_id, charset=charset)
    def produce(sink):
        for offset in range(0, len(data), 65536):
            invocation.check_cancelled()
            sink.write(data[offset:offset + 65536])
        return payload.identity, payload.media_type, payload.source_id, payload.charset, None
    return _store(invocation, target, writer, produce)


def _save(artifact, destination, writer, invocation, *, account_input=True):
    if not isinstance(artifact, MaterialArtifact) or not isinstance(destination, D.ArtifactDestination):
        raise OperationFailure("material.artifact_required")
    _addressable(writer)
    if storage_scope(writer, destination.locator) == storage_scope(writer, destination.descriptor):
        raise OperationFailure("material.descriptor_destination_conflict")
    try:
        descriptor = artifact.descriptor
    except (ValueError, TypeError):
        raise OperationFailure("material.descriptor_invalid") from None
    rep = artifact.representation
    if account_input:
        invocation.budget.charge("input_bytes", rep.identity.size + len(descriptor))
    invocation.use(UsedInputReceipt("artifact", artifact.identity, "application/json", "inline", artifact.series_id))
    for receipt in artifact.inputs:
        invocation.use(receipt)
    if artifact.computation is not None:
        invocation.parents.append(("artifact", artifact.computation))
    data = _bytes(rep.data, rep.media_type, artifact.series_id, OriginalDestination(destination.locator),
                  writer, invocation, rep.encoding)
    if data.material is None:
        return Completion(D.StoredArtifact(None, (data.storage,)), data.storage.status, data.storage.diagnostic_code)
    metadata = _bytes(descriptor, "application/json", artifact.series_id, OriginalDestination(destination.descriptor), writer, invocation, "utf-8")
    receipts = (data.storage, metadata.storage)
    if metadata.material is None:
        return Completion(D.StoredArtifact(None, receipts), metadata.storage.status, metadata.storage.diagnostic_code)
    return D.StoredArtifact(ArtifactReference(data.material, metadata.material, artifact.contract, artifact.identity), receipts)


def save_artifact(request: D.SaveArtifactRequest, *, store=None, selection=None, context=None):
    def work(req, invocation):
        return _save(req.artifact, req.destination, invocation.provider("output_filestore", store), invocation)
    return run(D.SAVE_ARTIFACT, request, work, context=context, providers={"output_filestore": store},
               provider_selections=_selections(output_filestore=selection))


def _read(reference, limit, reader, descriptor_reader, invocation):
    if not isinstance(reference, ArtifactReference):
        raise OperationFailure("material.reference_required")
    metadata = read_material(reference.descriptor, descriptor_reader, invocation, limit=MAX_DESCRIPTOR_BYTES, role="artifact_descriptor")
    payload = read_material(reference.material, reader, invocation, limit=limit, role="representation")
    try:
        artifact = restore_artifact(metadata.data, payload.data)
    except (ValueError, TypeError):
        raise OperationFailure("material.descriptor_invalid") from None
    if (artifact.identity != reference.identity or artifact.contract != reference.contract
            or artifact.representation.media_type != reference.material.media_type
            or artifact.representation.encoding != reference.material.charset
            or artifact.series_id != reference.material.source_id
            or artifact.series_id != reference.descriptor.source_id):
        raise OperationFailure("material.reference_mismatch")
    if artifact.computation is not None:
        invocation.parents.append(("artifact", artifact.computation))
    return artifact


def read_artifact(request: D.ReadArtifactRequest, *, store=None, descriptor_store=None,
                  selection=None, descriptor_selection=None, context=None):
    def work(req, invocation):
        reader = invocation.provider("filestore", store)
        metadata = (invocation.provider("descriptor_filestore", descriptor_store)
                    if descriptor_store is not None or descriptor_selection is not None else reader)
        artifact = _read(req.artifact, req.limit, reader, metadata, invocation)
        invocation.account_output(artifact.representation.identity, key="representation")
        invocation.account_output(artifact.identity, key="descriptor")
        return artifact
    return run(D.READ_ARTIFACT, request, work, context=context, providers={"filestore": store},
               provider_selections=_selections(filestore=selection, descriptor_filestore=descriptor_selection))


def transfer_artifact(request: D.TransferArtifactRequest, *, source_store=None, output_store=None,
                      descriptor_store=None, source_selection=None, output_selection=None,
                      descriptor_selection=None, context=None):
    def work(req, invocation):
        reader = invocation.provider("filestore", source_store)
        metadata = (invocation.provider("descriptor_filestore", descriptor_store)
                    if descriptor_store is not None or descriptor_selection is not None else reader)
        # Decoding is bounded and verifies the metadata before any new publication.
        artifact = _read(req.artifact, D.MAX_BYTES, reader, metadata, invocation)
        return _save(artifact, req.destination, invocation.provider("output_filestore", output_store), invocation, account_input=False)
    return run(D.TRANSFER_ARTIFACT, request, work, context=context,
               providers={"filestore": source_store, "output_filestore": output_store},
               provider_selections=_selections(filestore=source_selection, output_filestore=output_selection,
                                               descriptor_filestore=descriptor_selection))


def artifact_from_output(result, output_name, *, series_id=None, source_asset=None):
    """Wrap an admitted encoded output without concealing a semantic conversion."""
    from stratbox.core.execution.handoff import project_output
    projected = project_output(result, output_name)
    value = projected.value
    if isinstance(value, SourcePayload):
        value = Representation("source.bytes", 1, value.media_type, value.data, value.charset)
    if not isinstance(value, Representation):
        raise ValueError("material.encoder_required")
    return MaterialArtifact(projected.contract, value, result.used_inputs, series_id,
                            source_asset, result.computation)


def project_artifact(result):
    """Expose an encoded value using its verified retained semantic contract.

    This unwraps metadata; the domain's decoder still owns interpretation.
    Origin/coverage guarantees are never inferred from a storage location.
    """
    from dataclasses import replace
    from stratbox.core.execution.handoff import project_output
    projected = project_output(result, "artifact")
    artifact = projected.value
    if not isinstance(artifact, MaterialArtifact):
        raise ValueError("material.artifact_required")
    return replace(projected, contract=artifact.contract, value=artifact.representation,
                   qualifications=frozenset(), coverage=frozenset(),
                   used_inputs=tuple(dict.fromkeys((*artifact.inputs, *result.used_inputs))),
                   computation=artifact.computation, identity=artifact.representation.identity)
