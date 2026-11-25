"""Revision-bound file housekeeping and domain archive selection."""
from __future__ import annotations
from stratbox.core.storage.filestore import FileMutation, FileStore, MutationRejected, StagedWriter
from stratbox.core.formats.archives.store import ArchiveEntry, PathArchiveReceipt, zip_to_store
from stratbox.core.operations.source.originals import storage_effect
from stratbox.core.storage.bytes import inspect_file_version, read_bounded_bytes, write_verified_bytes
from stratbox.core.formats.archives.members import ArchiveError, ArchiveLimits, zip_bytes
from stratbox.core.limits import BudgetError
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.material_collections import CollectionDisposition, CollectionManifest, CollectionMember, encode_collection
from stratbox.shared.source_publications import SourceAssetIdentity
from stratbox.core.execution import Completion, EffectReceipt, ExecutionContext, OperationFailure, OperationResult, run
from ..publications.cleanup import ApplyCleanupRequest, CleanupPlan, CleanupReceipt, PlanCleanupRequest, create_plan as _create_plan, validate_plan as _validate_plan
from .housekeeping_definitions import APPLY, ARCHIVE, PLAN, STREAM_ARCHIVE, StreamArchiveRequest

def _cleanup_bindings():
    from .bindings import bind_family, bind_source
    from ..publications.catalog import families
    groups = tuple((bind_family(item.family_id) for item in families()))
    sources = {series.source_id: bind_source(series.source_id) for group in groups for series in group.source.series}
    return {'bound_families': groups, 'bound_sources': sources}

def create_plan(request, store, invocation):
    return _create_plan(request, store, invocation, **_cleanup_bindings())

def validate_plan(plan):
    return _validate_plan(plan, **_cleanup_bindings())

def _archive_manifest(plan: CleanupPlan, report_json: bytes | None=None) -> bytes:
    """Describe the logical selected originals independently of their source paths."""
    from .bindings import bind_source
    from ..publications.materials import MEDIA_TYPES
    from ..publications.naming import _canonical_period, build_internal_file_name
    members, inputs = ([], [])
    try:
        for action in sorted((item for item in plan.actions if item.kind != 'remove'), key=lambda item: (item.source_id, item.destination)):
            name = action.destination.replace('\\', '/').rsplit('/', 1)[-1]
            stem, extension = name.rsplit('.', 1)
            interpreted = _canonical_period(stem)
            bound = bind_source(action.source_id)
            if interpreted is None or interpreted[2] is None:
                raise ValueError('frg.archive.period_invalid')
            period = interpreted[2]
            if name != build_internal_file_name(period, bound.rule, format=extension, profile=bound.parent.naming):
                raise ValueError('frg.archive.name_mismatch')
            issue = period.snapshot_date.isoformat() if period.week_no is None else f'{period.snapshot_date:%Y-%m}-week-{period.week_no}'
            asset = SourceAssetIdentity(action.source_id, issue, extension)
            media_type = MEDIA_TYPES[extension]
            members.append(CollectionMember(action.source_id, name, DataContract('frg.original', 1, DataRole.ORIGINALS), action.source.identity, media_type, asset))
            inputs.append(UsedInputReceipt('selected_original', action.source.identity, media_type, 'reference_only', source_id=action.source_id))
        if not members:
            raise ValueError('archive.selection_invalid')
        if report_json is not None:
            if not isinstance(report_json, bytes):
                raise ValueError('archive.extra_invalid')
            identity = ByteIdentity.of(report_json)
            members.append(CollectionMember('selection_report', 'selection_report.json', DataContract('frg.selection_report', 1), identity, 'application/json'))
        version = ByteIdentity.of(canonical_manifest_bytes([{'key': member.key, 'name': member.name, 'sha256': member.identity.sha256, 'size': member.identity.size, 'issue': member.source_asset.issue_id if member.source_asset else None} for member in members])).sha256
        value = CollectionManifest('frg.selected-reports', version, tuple(members), tuple((CollectionDisposition(member.key, 'completed') for member in members)), SnapshotCoverage('complete', 'All selected archive members; publisher-wide report inventory is unspecified.'), tuple(inputs))
        return encode_collection(value)
    except (ValueError, TypeError, KeyError, AttributeError):
        raise OperationFailure('archive.manifest_invalid') from None

def plan_cleanup(request: PlanCleanupRequest, *, store: FileStore | None=None, selection=None, context: ExecutionContext | None=None) -> OperationResult[CleanupPlan]:
    return run(PLAN, request, lambda req, invocation: _work_plan_cleanup(req, invocation, store=store), context=context, providers={'filestore': store}, provider_selections={'filestore': selection} if selection is not None else None)

def _mutate(action, store, invocation, intent):
    invocation.check_cancelled()
    managed = invocation.context.profile == 'managed'
    data = None
    if action.kind == 'copy':
        try:
            if inspect_file_version(action.source.path, store=store, budget=invocation.budget, checkpoint=invocation.check_cancelled) != action.source:
                return CleanupReceipt(action, 'failed', 'effect.source_changed')
            data = read_bounded_bytes(action.source.path, store=store, limit=action.source.identity.size, budget=invocation.budget, checkpoint=invocation.check_cancelled)
        except (OSError, ValueError):
            return CleanupReceipt(action, 'failed', 'effect.source_unreadable')
        if ByteIdentity.of(data) != action.source.identity:
            return CleanupReceipt(action, 'failed', 'effect.source_changed')
        invocation.account_output(action.source.identity, key=f'copy:{intent.effect_id}')
        invocation.check_cancelled()
        if not managed:
            invocation.effect(_cleanup_effect(intent, 'unknown'))
            written = write_verified_bytes(action.destination, data, store=store, expected_sha256=action.source.identity.sha256)
            if written.status in {'stored', 'already_present'}:
                return CleanupReceipt(action, 'confirmed')
            return CleanupReceipt(action, written.status, written.diagnostic_code)
    elif not managed:
        reads = 2 if action.kind == 'rename' else 1
        invocation.budget.charge('input_bytes', action.source.identity.size * reads)
        invocation.check_cancelled()
    invocation.check_cancelled()
    invocation.effect(_cleanup_effect(intent, 'unknown'))
    try:
        if managed:
            confirmed = store.commit_mutation(intent, data)
        elif action.kind == 'rename':
            confirmed = store.rename_expected(action.source, action.destination)
        else:
            confirmed = store.remove_expected(action.source)
    except MutationRejected:
        return CleanupReceipt(action, 'failed', 'effect.rejected')
    except Exception:
        return CleanupReceipt(action, 'unknown', 'effect.outcome_unknown')
    if confirmed is True:
        return CleanupReceipt(action, 'confirmed')
    if confirmed is False:
        return CleanupReceipt(action, 'failed', 'effect.conflict')
    return CleanupReceipt(action, 'unknown', 'effect.outcome_unknown')

def _cleanup_effect(intent, state):
    return EffectReceipt(f'storage.{intent.kind}', state, intent.destination or intent.source.path, intent.effect_id, 'commit', intent.content, 'revision_guarded', 'store')

def apply_cleanup(request: ApplyCleanupRequest, *, store: FileStore | None=None, selection=None, context: ExecutionContext | None=None) -> OperationResult[tuple[CleanupReceipt, ...]]:
    return run(APPLY, request, lambda req, invocation: _work_apply_cleanup(req, invocation, store=store), context=context, providers={'filestore': store}, provider_selections={'filestore': selection} if selection is not None else None)

def prepare_archive(request: CleanupPlan, *, store: FileStore | None=None, selection=None, context: ExecutionContext | None=None) -> OperationResult[Representation]:
    return run(ARCHIVE, request, lambda req, invocation: _work_prepare_archive(req, invocation, store=store), context=context, providers={'filestore': store}, provider_selections={'filestore': selection} if selection is not None else None)

def prepare_archive_to_store(request: StreamArchiveRequest, *, store: FileStore | None=None, output_store: StagedWriter | None=None, selection=None, output_selection=None, context: ExecutionContext | None=None) -> OperationResult[PathArchiveReceipt]:
    """Stream selected inputs through a receiving store's staged commit."""
    return run(STREAM_ARCHIVE, request, lambda req, invocation: _work_prepare_archive_to_store(req, invocation, store=store, output_store=output_store), context=context, providers={'filestore': store, 'output_filestore': output_store}, provider_selections={k: v for k, v in {'filestore': selection, 'output_filestore': output_selection}.items() if v is not None})

def _work_plan_cleanup(req, invocation, *, store=None):
    store = invocation.provider('filestore', store)
    if any((not callable(getattr(store, name, None)) for name in ('inspect_file', 'directory_identity'))):
        raise OperationFailure('provider.capability_missing')
    invocation.stage('plan_cleanup')
    try:
        return create_plan(req, store, invocation)
    except (OSError, ValueError):
        raise OperationFailure('storage.catalog_unreadable') from None

def _work_apply_cleanup(req, invocation, *, store=None):
    store = invocation.provider('filestore', store)
    invocation.stage('authorize')
    if req.plan.request.directory != req.authorized_directory or req.plan.identity.sha256 != req.expected_sha256:
        raise OperationFailure('effect.plan_not_authorized')
    methods = ('guard_directory', 'directory_identity', 'inspect_file')
    if invocation.context.profile == 'managed':
        methods += ('commit_mutation',)
    else:
        methods += ('remove_expected', 'rename_expected', 'create_if_absent')
    for name in methods:
        if not callable(getattr(store, name, None)):
            raise OperationFailure('provider.capability_missing')
    receipts = []
    try:
        with store.guard_directory(req.authorized_directory):
            invocation.stage('revalidate')
            current = create_plan(req.plan.request, store, invocation)
            if current != req.plan:
                raise OperationFailure('effect.plan_stale')
            invocation.stage('apply')
            for index, action in enumerate(current.actions):
                if action.kind == 'keep':
                    receipts.append(CleanupReceipt(action, 'confirmed'))
                    continue
                effect_id = ByteIdentity.of(canonical_manifest_bytes({'plan': req.plan.identity.sha256, 'index': index, 'action': action.kind})).sha256
                intent = FileMutation(invocation.definition.operation_id, effect_id, current.identity, action.kind, directory=current.request.directory, source=action.source, destination=action.destination, content=action.source.identity)
                try:
                    receipt = _mutate(action, store, invocation, intent)
                except (OperationFailure, BudgetError) as error:
                    receipts.extend((CleanupReceipt(item, 'not_attempted') for item in current.actions[index:]))
                    if invocation.effects:
                        code = error.code if isinstance(error, BudgetError) else error.diagnostic.code
                        return Completion(tuple(receipts), 'partial', code)
                    raise
                receipts.append(receipt)
                invocation.effect(_cleanup_effect(intent, receipt.state))
                if receipt.state != 'confirmed':
                    receipts.extend((CleanupReceipt(item, 'not_attempted') for item in current.actions[index + 1:]))
                    prior_effects = any((effect.state == 'confirmed' for effect in invocation.effects))
                    outcome = 'unknown' if receipt.state == 'unknown' else 'partial' if prior_effects else 'failed'
                    return Completion(tuple(receipts), outcome, receipt.diagnostic)
    except (OSError, ValueError):
        if invocation.effects:
            return Completion(tuple(receipts), 'unknown', 'effect.guard_unconfirmed')
        raise OperationFailure('effect.directory_unavailable') from None
    return tuple(receipts)

def _work_prepare_archive(req, invocation, *, store=None):
    store = invocation.provider('filestore', store)
    invocation.stage('prepare_archive')
    validate_plan(req)
    if not callable(getattr(store, 'directory_identity', None)) or store.directory_identity(req.request.directory) != req.directory_identity:
        raise OperationFailure('effect.directory_scope_changed')
    files = {}
    limits = ArchiveLimits()
    total = 0
    for action in req.actions:
        invocation.check_cancelled()
        if action.kind == 'remove':
            continue
        source = action.source
        total += source.identity.size
        if total > limits.unpacked_bytes or source.identity.size > limits.member_bytes:
            raise OperationFailure('archive.size_limit')
        name = action.destination.replace('\\', '/').rsplit('/', 1)[-1]
        try:
            location = source.path if store.exists(source.path) else action.destination
            data = read_bounded_bytes(location, store=store, limit=source.identity.size, budget=invocation.budget, checkpoint=invocation.check_cancelled)
        except ValueError:
            raise OperationFailure('effect.source_changed') from None
        except OSError:
            raise OperationFailure('storage.source_unreadable') from None
        if ByteIdentity.of(data) != source.identity:
            raise OperationFailure('effect.source_changed')
        invocation.budget.charge('objects', 1)
        if name in files:
            raise OperationFailure('archive.selection_invalid')
        files[name] = data
        invocation.use(UsedInputReceipt.for_payload(SourcePayload(data, source_id=action.source_id), 'latest_file'))
    try:
        files['manifest.json'] = _archive_manifest(req)
        return Representation('frg.latest-zip', 2, 'application/zip', zip_bytes(files, limits=limits, budget=invocation.budget))
    except ArchiveError:
        raise OperationFailure('archive.preparation_failed') from None

def _work_prepare_archive_to_store(req, invocation, *, store=None, output_store=None):
    store = invocation.provider('filestore', store)
    output_store = invocation.provider('output_filestore', output_store)
    invocation.stage('revalidate')
    if any((not callable(getattr(store, name, None)) for name in ('directory_identity', 'inspect_file', 'open_read'))):
        raise OperationFailure('provider.capability_missing')
    if not req.destination or req.destination in {'.', '..'} or '\x00' in req.destination:
        raise OperationFailure('effect.destination_invalid')
    if invocation.context.profile == 'managed' and req.mode == 'best_effort_verified':
        raise OperationFailure('effect.mode_forbidden')
    try:
        if store.directory_identity(req.plan.request.directory) != req.plan.directory_identity:
            raise OperationFailure('effect.directory_scope_changed')
        current = create_plan(req.plan.request, store, invocation)
        if current != req.plan:
            raise OperationFailure('effect.plan_stale')
        entries = []
        for action in current.actions:
            invocation.check_cancelled()
            if action.kind == 'remove':
                continue
            if action.destination is None:
                raise OperationFailure('source.archive_name_missing')
            name = action.destination.replace('\\', '/').rsplit('/', 1)[-1]
            entries.append(ArchiveEntry(action.source.path, name, action.source.identity))
        invocation.stage('prepare_archive')
        extras = {'manifest.json': _archive_manifest(current, req.report_json)}
        if req.report_json is not None:
            extras['selection_report.json'] = req.report_json
        result = zip_to_store(tuple(entries), req.destination, source_store=store, output_store=output_store, budget=invocation.budget, checkpoint=invocation.check_cancelled, extras=extras, compression=req.compression, mode=req.mode, expected_revision=req.expected_revision, plan_identity=current.identity, operation_id=invocation.definition.operation_id, require_admission=invocation.context.profile == 'managed', source_directory=current.request.directory, on_effect=lambda receipt: storage_effect(invocation, receipt))
    except ArchiveError as error:
        raise OperationFailure(str(error)) from None
    except OSError:
        raise OperationFailure('storage.archive_unavailable') from None
    source_ids = {action.source.path: action.source_id for action in current.actions if action.kind != 'remove'}
    for entry in entries:
        invocation.use(UsedInputReceipt('frg_archive_file', entry.identity, 'application/octet-stream', 'reference_only', source_id=source_ids[entry.source]))
    receipt = result.storage
    state = {'stored': 'confirmed', 'already_present': 'confirmed', 'failed': 'failed', 'unknown': 'unknown'}[receipt.status]
    if state != 'confirmed':
        return Completion(result, state, receipt.diagnostic_code)
    return result
