"""A shared archive operation over explicitly selected, possibly distributed inputs."""
from contextlib import contextmanager
from io import BytesIO

from stratbox.core.execution import Completion, OperationFailure, run
from stratbox.core.formats.archives.store import ArchiveEntry, PathArchiveReceipt, zip_to_store
from stratbox.core.formats.archives.members import ArchiveError
from stratbox.core.operations.source.originals import _material_admission, storage_effect
from stratbox.core.storage.staging import current_revision
from stratbox.shared.evidence import MaterialReference, SourcePayload, UsedInputReceipt

from .definitions import MAX_BYTES
from .operations import _addressable, _selections


from .archive_definitions import ARCHIVE, ArchiveMember, ArchiveRequest, StoredArchive


class _ArchiveSources:
    def __init__(self, members, readers, invocation):
        self.members, self.readers, self.invocation = members, readers, invocation

    @contextmanager
    def open_read(self, path):
        member = self.members[int(path)]
        source = member.source
        if isinstance(source, SourcePayload):
            with BytesIO(source.data) as stream:
                yield stream
            return
        reader = self.readers[int(path)]
        _material_admission(source, reader, self.invocation, MAX_BYTES)
        before = current_revision(reader, source.locator)
        if source.revision is not None and source.revision != before:
            raise OperationFailure("input.material_version_changed")
        with reader.open_read(source.locator) as stream:
            yield stream
        if before != current_revision(reader, source.locator):
            raise OperationFailure("input.material_version_changed")


def archive_materials(request: ArchiveRequest, *, source_store=None, output_store=None,
                      source_selection=None, output_selection=None, context=None):
    def work(req, invocation):
        if not isinstance(req.members, tuple) or not req.members or any(
            not isinstance(x, ArchiveMember) or not isinstance(x.source, (SourcePayload, MaterialReference))
            for x in req.members
        ):
            raise OperationFailure("archive.selection_invalid")
        if invocation.context.profile == "managed" and req.destination.mode == "best_effort_verified":
            raise OperationFailure("effect.mode_forbidden")
        writer = invocation.provider("output_filestore", output_store)
        _addressable(writer)
        from stratbox.core.storage.staging import storage_scope, store_identity
        # Reject aliases of retained members, even through different provider objects.
        target_scope = storage_scope(writer, req.destination.locator)
        readers = {}
        for index, member in enumerate(req.members):
            if not isinstance(member.source, MaterialReference):
                continue
            reader = invocation.provider("filestore", source_store, selection=member.selection)
            _addressable(reader)
            _material_admission(member.source, reader, invocation, MAX_BYTES)
            same_scope = (store_identity(reader) == store_identity(writer)
                          and storage_scope(reader, member.source.locator) == target_scope)
            source_path = getattr(reader, "checked_file_path", None)
            target_path = getattr(writer, "checked_file_path", None)
            same_path = (callable(source_path) and callable(target_path)
                         and source_path(member.source.locator) == target_path(req.destination.locator))
            if same_scope or same_path:
                raise OperationFailure("archive.source_destination_conflict")
            readers[index] = reader
        entries = tuple(ArchiveEntry(str(i), member.name, member.source.identity) for i, member in enumerate(req.members))
        invocation.stage("prepare_archive")
        try:
            value = zip_to_store(entries, req.destination.locator,
                source_store=_ArchiveSources(req.members, readers, invocation), output_store=writer,
                budget=invocation.budget, checkpoint=invocation.check_cancelled,
                mode=req.destination.mode, expected_revision=req.destination.expected_revision,
                compression=req.compression, operation_id=ARCHIVE.operation_id,
                plan_identity=_plan(req), require_admission=invocation.context.profile == "managed",
                on_effect=lambda receipt: storage_effect(invocation, receipt))
        except ArchiveError as error:
            raise OperationFailure(str(error)) from None
        except OSError:
            raise OperationFailure("archive.source_unavailable") from None
        members = []
        for item in req.members:
            receipt = UsedInputReceipt("archive_member", item.source.identity, item.source.media_type,
                                       "inline" if isinstance(item.source, SourcePayload) else "reference_only",
                                       item.source.source_id)
            invocation.use(receipt)
            members.append((item.name, UsedInputReceipt(receipt.role, receipt.identity, receipt.media_type,
                "reference_only", receipt.source_id, value.identity, item.name)))
        invocation.record(value.identity, parameters={"members": [x.name for x in req.members], "compression": req.compression})
        storage = value.storage
        ref = None
        if storage.status in {"stored", "already_present"}:
            ref = MaterialReference(value.path, storage.store_id, value.identity, "application/zip",
                                    revision=storage.observed_revision, store_scope=storage.store_scope)
        result = StoredArchive(value, ref, tuple(members))
        return result if ref is not None else Completion(result, storage.status, storage.diagnostic_code)
    return run(ARCHIVE, request, work, context=context, providers={"output_filestore": output_store},
               provider_selections=_selections(filestore=source_selection, output_filestore=output_selection))


def _plan(request):
    from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
    return ByteIdentity.of(canonical_manifest_bytes({"members": [
        {"name": x.name, "sha256": x.source.identity.sha256, "size": x.source.identity.size}
        for x in request.members], "compression": request.compression}))
