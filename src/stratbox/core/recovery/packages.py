"""A quiescent cross-owner cut with explicit dependencies and replay fencing.

The package is a recovery copy, not a second live owner. It preserves historical
provider scopes. Restoration verifies immutable dependencies in those scopes;
it never rewrites a past delivery receipt to describe a relocated destination.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import ExitStack, closing
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from stratbox.core.storage.readable import copy_stream, scan_identity, open_provider
from stratbox.shared.data.values import ImmutableMaterialRef, SnapshotRef, canonical_tree, restore_tree, fingerprint
from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True, slots=True)
class RecoveryLimits:
    max_files: int = 1000000
    max_bytes: int = 64 * 1024**3
    max_file_bytes: int = 64 * 1024**3
    max_index_bytes: int = 256 * 1024**2
    max_manifest_bytes: int = 4 * 1024**2

    def __post_init__(self):
        if any(type(getattr(self, field.name)) is not int or getattr(self, field.name) < 1 for field in fields(self)):
            raise ValueError('recovery.limits_invalid')


def _json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode()


def _metadata(value):
    if is_dataclass(value):
        return {field.name: _metadata(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {key: _metadata(part) for key, part in value.items()}
    if isinstance(value, (tuple, list)):
        return [_metadata(part) for part in value]
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise ValueError('recovery.metadata_type_invalid')


def _relative(root, name):
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError('recovery.path_invalid')
    path = Path(name)
    if path.is_absolute() or any(part in {'', '.', '..'} for part in path.parts):
        raise ValueError('recovery.path_invalid')
    result = root / path
    if not result.resolve().is_relative_to(root.resolve()) or any(part.is_symlink() for part in (result, *result.parents) if part != root.parent):
        raise ValueError('recovery.path_invalid')
    return result


def _read_json(path, limit):
    with Path(path).open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('recovery.manifest_limit')
    return json.loads(raw)


def _file_identity(path, limit):
    with Path(path).open('rb') as stream:
        return scan_identity(stream, limit=limit)


def _copy_file(source, target, limit, expected=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    with Path(source).open('rb') as incoming, target.open('xb') as outgoing:
        identity = copy_stream(incoming, outgoing, limit=limit, expected=expected)
        outgoing.flush(); os.fsync(outgoing.fileno())
    return identity


def _write_json(path, value, limit):
    raw = _json(value)
    if len(raw) > limit:
        raise ValueError('recovery.manifest_limit')
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def _index_files(root, limits):
    count = size = index_size = 0
    with (root / 'files.jsonl').open('xb') as index:
        for directory, directories, files in os.walk(root):
            directories.sort()
            for name in sorted(files):
                path = Path(directory) / name
                relative = path.relative_to(root).as_posix()
                if relative in {'manifest.json', 'files.jsonl'}:
                    continue
                if path.is_symlink() or not path.is_file():
                    raise ValueError('recovery.regular_file_required')
                identity = _file_identity(path, limits.max_file_bytes)
                count += 1; size += identity.size
                raw = _json({'path': relative, 'sha256': identity.sha256, 'size': identity.size}) + b'\n'
                index_size += len(raw)
                if count > limits.max_files or size > limits.max_bytes or index_size > limits.max_index_bytes:
                    raise ValueError('recovery.package_limit')
                index.write(raw)
        index.flush(); os.fsync(index.fileno())
    return count, size, _file_identity(root / 'files.jsonl', limits.max_index_bytes)


def _export_remaining(root, limits):
    """Apply aggregate data-file limits before starting another owner copy."""
    count = size = 0
    for directory, _directories, files in os.walk(root):
        for name in files:
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                raise ValueError('recovery.regular_file_required')
            file_size = path.stat().st_size
            count += 1; size += file_size
            if (file_size > limits.max_file_bytes or count >= limits.max_files
                    or size >= limits.max_bytes):
                raise ValueError('recovery.package_limit')
    return limits.max_files - count, limits.max_bytes - size


def _references(value, *, depth=0):
    if depth > 32:
        raise ValueError('recovery.dependency_nesting_limit')
    if isinstance(value, (ImmutableMaterialRef, SnapshotRef)):
        yield value
    elif isinstance(value, Mapping):
        for part in value.values():
            yield from _references(part, depth=depth + 1)
    elif isinstance(value, (tuple, list)):
        for part in value:
            yield from _references(part, depth=depth + 1)
    elif is_dataclass(value):
        for field in fields(value):
            yield from _references(getattr(value, field.name), depth=depth + 1)


def _dependency_stream(state, effects, supplied):
    yield from state.retained_references()
    after = ''
    while page := effects.page(after=after, limit=256):
        for item in page:
            receipt = effects.get(item['effect_id'])
            # A receipt can be durable even when the following journal append
            # or output acceptance fails. Projection-only discovery would lose
            # those confirmed retained bytes from an otherwise valid backup.
            if receipt.status == 'confirmed':
                yield from _references(receipt.value)
                if isinstance(receipt.intent, (ImmutableMaterialRef, SnapshotRef)):
                    yield receipt.intent
            # Unresolved/rejected actions can depend on retained ancestors and
            # prerequisite artifacts. Their proposed destination is not proof
            # of available content and must never enter this dependency set.
            intent = receipt.intent
            ancestor = (intent.get('retained_ancestor') if isinstance(intent, Mapping)
                        else getattr(intent, 'retained_ancestor', None))
            if ancestor is not None:
                yield from _references(ancestor)
            prerequisites = (intent.get('prerequisites', ()) if isinstance(intent, Mapping)
                             else getattr(intent, 'prerequisites', ()))
            yield from _references(prerequisites)
        after = page[-1]['effect_id']
    yield from supplied


def _export_dependencies(root, state, effects, providers, supplied, limits):
    from stratbox.core.commands._storage import _provider_scope
    available_files, available_bytes = _export_remaining(root, limits)
    # A disk-backed exact set bounds memory even for a large immutable archive.
    db = sqlite3.connect(root / 'dependency-set.sqlite')
    db.execute('CREATE TABLE seen(identity TEXT PRIMARY KEY)')
    db.execute('CREATE TABLE verified(identity TEXT PRIMARY KEY,sha256 TEXT NOT NULL,size INTEGER NOT NULL)')
    db.execute('CREATE TABLE objects(sha256 TEXT PRIMARY KEY,size INTEGER NOT NULL)')
    count = total = index_bytes = object_count = 0
    try:
        with (root / 'dependencies.jsonl').open('xb') as index:
            for reference in _dependency_stream(state, effects, supplied):
                if not isinstance(reference, (ImmutableMaterialRef, SnapshotRef)):
                    raise TypeError('recovery.retained_reference_required')
                key = fingerprint(reference)
                if not db.execute('INSERT OR IGNORE INTO seen VALUES(?)', (key,)).rowcount:
                    continue
                if isinstance(reference, ImmutableMaterialRef):
                    provider = providers.get('filestore')
                    if provider is None or reference.provider_scope != _provider_scope(provider, reference.location):
                        raise ValueError('recovery.artifact_scope_mismatch')
                    location, expected, kind = reference.location, reference.identity, 'material'
                else:
                    provider = providers.get('datasets')
                    if (provider is None or reference.provider_id != getattr(provider, 'provider_id', None)
                            or reference.provider_scope != getattr(provider, 'scope_id', None)):
                        raise ValueError('recovery.dataset_scope_mismatch')
                    if not hasattr(provider, 'store'):
                        raise ValueError('recovery.dataset_export_unsupported')
                    location, expected, kind = reference.snapshot_id, None, 'dataset'
                physical_key = fingerprint((kind, reference.provider_id, reference.provider_scope, location,
                                            reference.identity))
                verified = db.execute('SELECT sha256,size FROM verified WHERE identity=?', (physical_key,)).fetchone()
                if verified is not None:
                    identity = ByteIdentity(*verified)
                else:
                    if kind == 'dataset':
                        # Qualify semantic identity once per actual snapshot,
                        # independently of reference/witness attachment aliases.
                        provider.query(reference, None)
                        provider = provider.store
                        cached_size = db.execute('SELECT size FROM objects WHERE sha256=?', (Path(location).name,)).fetchone()
                        if cached_size is not None:
                            expected = ByteIdentity(Path(location).name, cached_size[0])
                    known_object = db.execute('SELECT size FROM objects WHERE sha256=?',
                        (expected.sha256,)).fetchone() if expected is not None else None
                    if known_object is not None:
                        with open_provider(provider, location) as incoming:
                            identity = scan_identity(incoming, limit=expected.size)
                        if identity != expected:
                            raise ValueError('recovery.artifact_identity_conflict')
                    else:
                        if object_count + 2 > available_files:
                            raise ValueError('recovery.dependency_limit')
                        partial = root / 'objects' / ('.partial-' + key)
                        partial.parent.mkdir(exist_ok=True)
                        with open_provider(provider, location) as incoming, partial.open('xb') as outgoing:
                            identity = copy_stream(incoming, outgoing, expected=expected,
                                limit=min(limits.max_file_bytes, available_bytes - total - index_bytes))
                            outgoing.flush(); os.fsync(outgoing.fileno())
                        target = root / 'objects' / identity.sha256
                        if target.exists():
                            partial.unlink()
                        else:
                            partial.rename(target)
                            total += identity.size
                            object_count += 1
                        db.execute('INSERT OR IGNORE INTO objects VALUES(?,?)', (identity.sha256, identity.size))
                    db.execute('INSERT INTO verified VALUES(?,?,?)', (physical_key, identity.sha256, identity.size))
                name = 'objects/' + identity.sha256
                count += 1
                if count > limits.max_files or total + index_bytes > available_bytes:
                    raise ValueError('recovery.dependency_limit')
                raw = _json({'kind': kind, 'reference': canonical_tree(reference), 'path': name,
                             'sha256': identity.sha256, 'size': identity.size}) + b'\n'
                index_bytes += len(raw)
                if len(raw) > 1024**2 or index_bytes > limits.max_index_bytes:
                    raise ValueError('recovery.dependency_index_limit')
                if total + index_bytes > available_bytes:
                    raise ValueError('recovery.dependency_limit')
                index.write(raw)
            index.flush(); os.fsync(index.fileno())
    finally:
        db.close()
        (root / 'dependency-set.sqlite').unlink(missing_ok=True)
    return count, total


def _validate_cut(owners):
    journal = owners['journal']['checkpoint']
    stream, floor, tail = journal['stream_id'], journal['retained_after'], journal['tail']
    checkpoints = owners['source_state']['checkpoints']
    selected = [item for item in checkpoints if item['stream_id'] == stream]
    if len(selected) != 1 or selected[0]['applied_through'] != tail or not selected[0]['coverage_complete']:
        raise ValueError('recovery.projection_cut_incomplete')
    if any(item['stream_id'] != stream for item in checkpoints):
        raise ValueError('recovery.foreign_projection_stream')
    for item in owners.get('notification_state', {}).get('subscriptions', ()):
        if item['stream_id'] != stream or not floor <= item['sequence'] <= tail:
            raise ValueError('recovery.notification_replay_gap')


def export_recovery_package(box, destination, *, timeout=60, limits=None, retained_references=()):
    """Pause admission, drain, commit projection coverage and export a verified cut."""
    from stratbox.core.observability.journal.stream import FileJournal
    from stratbox.core.observability.projections.source_state import SourceStateIndex
    from stratbox.core.storage.source_state import SQLiteSourceState
    from stratbox.core.execution.effect_state import FileEffectState
    from stratbox.core.notifications.state import FileNotificationState
    limits = limits or RecoveryLimits()
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(destination)
    session = box.session
    journal = session.journal
    state, effects = session.resolve_provider('source_state'), session.resolve_provider('effect_state')
    notifications = session.resolve_provider('notification_state') if 'notification_state' in session.providers else None
    if (not isinstance(journal, FileJournal) or not isinstance(state, SQLiteSourceState)
            or not isinstance(effects, FileEffectState)
            or notifications is not None and not isinstance(notifications, FileNotificationState)):
        raise ValueError('recovery.persistent_local_profile_required')
    source_roots = (journal.directory.resolve(), effects.directory.resolve(), state.path.parent.resolve())
    if any(destination.is_relative_to(root) for root in source_roots):
        raise ValueError('recovery.destination_inside_live_state')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='stratbox-recovery-', dir=destination.parent))
    try:
        with session.admission_pause(timeout=timeout):
            checkpoint = SourceStateIndex(state).advance(journal, max_pages=1000, page_limit=1000)
            if checkpoint.applied_through != journal.checkpoint().tail:
                raise ValueError('recovery.projection_lag_limit')
            owners = {'journal': _metadata(journal.recovery_metadata()),
                      'source_state': _metadata(state.recovery_metadata()),
                      'effect_state': _metadata(effects.recovery_metadata())}
            journal.export_checkpoint(temporary / 'journal', max_bytes=limits.max_bytes,
                max_files=limits.max_files, max_file_bytes=limits.max_file_bytes)
            _files, remaining = _export_remaining(temporary, limits)
            state.export_checkpoint(temporary / 'source-state.sqlite',
                max_bytes=min(remaining, limits.max_file_bytes))
            files, remaining = _export_remaining(temporary, limits)
            effects.export_checkpoint(temporary / 'effects', max_bytes=remaining,
                max_files=files, max_file_bytes=limits.max_file_bytes)
            if notifications is not None:
                owners['notification_state'] = _metadata(notifications.recovery_metadata())
                _files, remaining = _export_remaining(temporary, limits)
                notifications.export_checkpoint(temporary / 'notifications' / 'dispatch.sqlite',
                    max_bytes=min(remaining, limits.max_file_bytes))
            _validate_cut(owners)
            providers = {role: session.resolve_provider(role) for role in ('filestore', 'datasets') if role in session.providers}
            dependencies, dependency_bytes = _export_dependencies(temporary, state, effects, providers, retained_references, limits)
            if (_metadata(journal.recovery_metadata()) != owners['journal']
                    or _metadata(effects.recovery_metadata()) != owners['effect_state']
                    or _metadata(state.recovery_metadata()) != owners['source_state']
                    or notifications is not None and _metadata(notifications.recovery_metadata()) != owners['notification_state']):
                raise ValueError('recovery.owner_changed_during_export')
            count, total, index = _index_files(temporary, limits)
            from stratbox import __version__
            manifest = {'format': 'stratbox.recovery.v1', 'core_version': __version__,
                'created_at': datetime.now(timezone.utc).isoformat(), 'profile': 'local_single_coordinator',
                'owners': owners, 'files': count, 'bytes': total, 'index_sha256': index.sha256,
                'index_bytes': index.size, 'dependencies': dependencies, 'dependency_bytes': dependency_bytes,
                'completeness': 'verified_at_cut', 'restore_effect_policy': 'close_prior_occurrence_namespace',
                'artifact_policy': 'verify_original_provider_scopes',
                'limits': _metadata(limits)}
            manifest['package_id'] = sha256(_json(manifest)).hexdigest()
            _write_json(temporary / 'manifest.json', manifest, limits.max_manifest_bytes)
            validate_recovery_package(temporary, limits=limits)
            temporary.rename(destination)
        return manifest
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _file_entries(root, limits):
    total = 0
    with (root / 'files.jsonl').open('rb') as stream:
        while raw := stream.readline(1024**2 + 1):
            total += len(raw)
            if len(raw) > 1024**2 or total > limits.max_index_bytes:
                raise ValueError('recovery.index_limit')
            item = json.loads(raw)
            if set(item) != {'path', 'sha256', 'size'} or type(item['size']) is not int or not 0 <= item['size'] <= limits.max_file_bytes:
                raise ValueError('recovery.file_entry_invalid')
            yield item


def validate_recovery_package(directory, *, limits=None):
    """Verify identities and coverage before exposing any restored provider."""
    limits, root = limits or RecoveryLimits(), Path(directory).resolve()
    manifest = _read_json(root / 'manifest.json', limits.max_manifest_bytes)
    claimed = manifest.get('package_id')
    if (manifest.get('format') != 'stratbox.recovery.v1'
            or manifest.get('restore_effect_policy') != 'close_prior_occurrence_namespace'
            or manifest.get('artifact_policy') != 'verify_original_provider_scopes'
            or claimed != sha256(_json({key: value for key, value in manifest.items() if key != 'package_id'})).hexdigest()):
        raise ValueError('recovery.manifest_identity_invalid')
    index = _file_identity(root / 'files.jsonl', limits.max_index_bytes)
    if (index.sha256, index.size) != (manifest['index_sha256'], manifest['index_bytes']):
        raise ValueError('recovery.index_identity_conflict')
    count = total = 0
    # Exact duplicate-path detection uses a temporary disk index, not a growing
    # Python set. This validator accepts packages larger than process memory.
    with tempfile.TemporaryDirectory(prefix='stratbox-recovery-verify-') as temp:
        with sqlite3.connect(Path(temp) / 'paths.sqlite') as db:
            db.execute('CREATE TABLE paths(path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, size INTEGER NOT NULL)')
            for item in _file_entries(root, limits):
                if item['path'] in {'manifest.json', 'files.jsonl'}:
                    raise ValueError('recovery.file_entry_invalid')
                try:
                    db.execute('INSERT INTO paths VALUES(?,?,?)', (item['path'], item['sha256'], item['size']))
                except sqlite3.IntegrityError:
                    raise ValueError('recovery.duplicate_path') from None
                identity = _file_identity(_relative(root, item['path']), limits.max_file_bytes)
                if (identity.sha256, identity.size) != (item['sha256'], item['size']):
                    raise ValueError('recovery.file_identity_conflict')
                count += 1; total += identity.size
                if count > limits.max_files or total > limits.max_bytes:
                    raise ValueError('recovery.package_limit')
            required = ['journal/stream-id', 'journal/retention.json', 'source-state.sqlite',
                        'effects/effects.sqlite', 'effects/checkpoint.json', 'effects/cold-index.jsonl', 'dependencies.jsonl']
            if 'notification_state' in manifest['owners']:
                required.append('notifications/dispatch.sqlite')
            if any(db.execute('SELECT 1 FROM paths WHERE path=?', (name,)).fetchone() is None for name in required):
                raise ValueError('recovery.required_owner_missing')
            dependency_count = dependency_bytes = index_bytes = 0
            db.execute('CREATE TABLE used_objects(path TEXT PRIMARY KEY)')
            with (root / 'dependencies.jsonl').open('rb') as dependencies:
                while raw := dependencies.readline(1024**2 + 1):
                    index_bytes += len(raw)
                    if len(raw) > 1024**2 or index_bytes > limits.max_index_bytes:
                        raise ValueError('recovery.dependency_index_limit')
                    item = json.loads(raw)
                    if set(item) != {'kind', 'reference', 'path', 'sha256', 'size'}:
                        raise ValueError('recovery.dependency_invalid')
                    stored = db.execute('SELECT sha256,size FROM paths WHERE path=?', (item['path'],)).fetchone()
                    if stored != (item['sha256'], item['size']) or not item['path'].startswith('objects/'):
                        raise ValueError('recovery.dependency_not_in_inventory')
                    reference = restore_tree(item['reference'])
                    if (isinstance(reference, ImmutableMaterialRef) and
                            (item['kind'] != 'material' or reference.identity != ByteIdentity(item['sha256'], item['size']))
                            or isinstance(reference, SnapshotRef) and item['kind'] != 'dataset'
                            or not isinstance(reference, (ImmutableMaterialRef, SnapshotRef))):
                        raise ValueError('recovery.dependency_binding_invalid')
                    dependency_count += 1
                    if db.execute('INSERT OR IGNORE INTO used_objects VALUES(?)', (item['path'],)).rowcount:
                        dependency_bytes += item['size']
                    if dependency_count > limits.max_files or dependency_bytes > limits.max_bytes:
                        raise ValueError('recovery.dependency_limit')
            if (dependency_count, dependency_bytes) != (manifest['dependencies'], manifest['dependency_bytes']):
                raise ValueError('recovery.dependency_inventory_conflict')
    if (count, total) != (manifest['files'], manifest['bytes']):
        raise ValueError('recovery.package_inventory_conflict')
    _validate_cut(manifest['owners'])
    if (root / 'journal' / 'stream-id').read_text().strip() != manifest['owners']['journal']['checkpoint']['stream_id']:
        raise ValueError('recovery.journal_identity_conflict')
    return manifest


def _verify_dependencies(root, providers, limits):
    from stratbox.core.commands._storage import _provider_scope
    with (root / 'dependencies.jsonl').open('rb') as stream:
        count = size = 0
        while raw := stream.readline(1024**2 + 1):
            count += 1; size += len(raw)
            if len(raw) > 1024**2 or count > limits.max_files or size > limits.max_index_bytes:
                raise ValueError('recovery.dependency_index_limit')
            item = json.loads(raw)
            reference = restore_tree(item['reference'])
            packed = _relative(root, item['path'])
            expected = ByteIdentity(item['sha256'], item['size'])
            if _file_identity(packed, limits.max_file_bytes) != expected:
                raise ValueError('recovery.dependency_identity_conflict')
            if isinstance(reference, ImmutableMaterialRef):
                provider = providers.get('filestore')
                if provider is None or reference.provider_scope != _provider_scope(provider, reference.location):
                    raise ValueError('recovery.artifact_scope_mismatch')
                # Restore never repairs a historical external action as a side
                # effect. The caller must fulfil a new repair occurrence first.
                with open_provider(provider, reference.location) as incoming:
                    if scan_identity(incoming, limit=reference.identity.size) != reference.identity or expected != reference.identity:
                        raise ValueError('recovery.artifact_unavailable')
            elif isinstance(reference, SnapshotRef):
                provider = providers.get('datasets')
                if provider is None:
                    raise ValueError('recovery.dataset_provider_required')
                provider.query(reference, None)
            else:
                raise ValueError('recovery.reference_invalid')


def _restore_file(source, target, limits, expected=None):
    """Publish each copied file atomically so an interrupted restore can resume."""
    from stratbox.core.observability.journal.stream import _fsync_directory
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + '.restore-partial')
    partial.unlink(missing_ok=True)
    try:
        identity = _copy_file(source, partial, limits.max_file_bytes, expected)
        os.replace(partial, target)
        _fsync_directory(target.parent)
        return identity
    finally:
        partial.unlink(missing_ok=True)


def _same_journal_prefix(left, right, through):
    cursor = max(left.checkpoint().retained_after, right.checkpoint().retained_after)
    while cursor < through:
        limit = min(256, through - cursor)
        a = left.read_page(after=cursor, limit=limit, scan_limit=limit)
        b = right.read_page(after=cursor, limit=limit, scan_limit=limit)
        if (a.scanned_through != b.scanned_through or a.scanned_through <= cursor
                or fingerprint(a.facts) != fingerprint(b.facts)):
            raise ValueError('recovery.authoritative_journal_diverged')
        cursor = a.scanned_through


def _recover_journal_suffix(package, original, destination, manifest, limits):
    """Splice exact retained authority; source-state replay happens separately."""
    from stratbox.core.observability.journal.stream import FileJournal, _atomic_json
    config = manifest['owners']['journal']
    cutoff = config['checkpoint']['tail']
    with FileJournal(original, segment_size=config['segment_size'], max_record_bytes=config['max_record_bytes']) as live, \
            FileJournal(package / 'journal', segment_size=config['segment_size'], max_record_bytes=config['max_record_bytes']) as saved, \
            FileJournal(destination, segment_size=config['segment_size'], max_record_bytes=config['max_record_bytes']) as pending:
        current = live.checkpoint()
        if live.stream_id != saved.stream_id or pending.stream_id != saved.stream_id:
            raise ValueError('recovery.original_owner_identity_conflict')
        if current.tail < cutoff or current.tail < pending.checkpoint().tail:
            raise ValueError('recovery.authoritative_tail_behind_checkpoint')
        if current.retained_after > cutoff:
            raise ValueError('recovery.authoritative_suffix_expired')
        _same_journal_prefix(saved, live, cutoff)
        _same_journal_prefix(pending, live, pending.checkpoint().tail)
        copied = total = 0
        if current.tail > cutoff:
            for segment in range(cutoff // live.segment_size, (current.tail - 1) // live.segment_size + 1):
                source = live._segment(segment)
                if source is None:
                    raise ValueError('recovery.authoritative_suffix_missing')
                copied += 1
                if copied > limits.max_files:
                    raise ValueError('recovery.authoritative_suffix_limit')
                target = pending._active(segment)
                cold = pending._cold(segment)
                if cold.exists():
                    # A boundary segment containing a partial old tail is hot;
                    # an existing cold duplicate indicates an invalid geometry.
                    raise ValueError('recovery.authoritative_segment_conflict')
                copied_identity = _restore_file(source, target, limits)
                total += copied_identity.size
                if total > limits.max_bytes:
                    raise ValueError('recovery.authoritative_suffix_limit')
        retention = _read_json(package / 'journal' / 'retention.json', limits.max_manifest_bytes)
        retention['tail'] = current.tail
        # Host-defined consumers, including registrations after the package cut,
        # remain retention barriers. Missing registrations from the old cut stay
        # conservatively retained; a host may retire them explicitly afterwards.
        recovered_consumers = dict(retention['consumers'])
        for consumer, cursor in current.consumers.items():
            if consumer == 'source-state':
                continue
            if consumer in recovered_consumers and cursor < recovered_consumers[consumer]:
                raise ValueError('recovery.authoritative_consumer_regressed')
            recovered_consumers[consumer] = cursor
        # This derivative owner's cursor must describe its actual restored
        # replay, never the independently advanced original projection.
        if 'source-state' in pending.checkpoint().consumers:
            recovered_consumers['source-state'] = pending.checkpoint().consumers['source-state']
        retention['consumers'] = recovered_consumers
        _atomic_json(destination / 'retention.json', retention)
        return current.tail


def _verified_effect_checkpoint(package, manifest, cleanup, limits, *, admitted_types=None):
    """Prefer surviving exact ledger authority, with immutable overlap checks."""
    from stratbox.core.execution.effect_state import FileEffectState
    from stratbox.core.execution.effect_evidence import same_effect_intent, valid_intent_update
    saved_path = package / 'effects'
    saved = FileEffectState.checkpoint_view(saved_path, admitted_types=admitted_types)
    owner = manifest['owners']['effect_state']
    database = Path(owner['database'])
    if not database.is_file():
        return saved_path, False
    if database.name != 'effects.sqlite':
        raise ValueError('recovery.effect_owner_location_invalid')
    config = _read_json(saved_path / 'checkpoint.json', 65536)
    live = FileEffectState(database.parent, archive_directory=owner['archive_directory'],
        admitted_types=admitted_types, max_receipt_bytes=config['max_receipt_bytes'],
        max_hot_receipts=config['max_hot_receipts'], max_hot_bytes=config['max_hot_bytes'])
    if live.scope_id != saved.scope_id:
        raise ValueError('recovery.effect_owner_scope_conflict')
    before = dict(live.recovery_metadata())
    temporary = Path(cleanup.enter_context(tempfile.TemporaryDirectory(prefix='stratbox-effect-authority-')))
    current_path = temporary / 'checkpoint'
    live.export_checkpoint(current_path, max_bytes=limits.max_bytes, max_files=limits.max_files,
        max_file_bytes=limits.max_file_bytes)
    if dict(live.recovery_metadata()) != before:
        raise ValueError('recovery.effect_owner_changed_during_capture')
    current = FileEffectState.checkpoint_view(current_path, admitted_types=admitted_types)
    after = ''
    while page := saved.page(after=after, limit=256):
        for item in page:
            previous = saved.get(item['effect_id'])
            latest = current.get(item['effect_id'])
            if (latest is None or (latest.kind, latest.resource) != (previous.kind, previous.resource)
                    or latest.revision < previous.revision):
                raise ValueError('recovery.effect_authority_regressed')
            if previous.status == 'confirmed':
                if latest != previous:
                    raise ValueError('recovery.confirmed_effect_conflict')
            elif previous.status == 'unknown':
                if (latest.claim_id != previous.claim_id or not valid_intent_update(previous.intent, latest.intent)):
                    raise ValueError('recovery.unknown_effect_conflict')
            elif not same_effect_intent(previous.intent, latest.intent):
                raise ValueError('recovery.effect_intent_conflict')
        after = page[-1]['effect_id']
    return current_path, True


def _notification_metadata(value):
    """Database location changes on transfer; logical owner identity does not."""
    return {key: part for key, part in _metadata(value).items() if key != 'database'}


def _readonly_database(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)


def _verified_notification_checkpoint(package, manifest, cleanup, limits, effects, recovered_tail,
                                      *, admitted_types=None):
    """Preserve cursor, consumed evidence and exact pending intents together."""
    from stratbox.core.notifications.state import FileNotificationState
    from stratbox.core.execution.effect_state import FileEffectState
    config = manifest['owners']['notification_state']
    saved_path = package / 'notifications' / 'dispatch.sqlite'
    original = Path(config['database'])
    saved_effects = FileEffectState.checkpoint_view(package / 'effects', admitted_types=admitted_types)
    if not original.is_file():
        # A later journal with no surviving queue cannot establish that its
        # notification transactions left the older outbox unchanged, even if
        # their effect ledger was lost too. Keep the older owner untransferred.
        if recovered_tail > manifest['owners']['journal']['checkpoint']['tail']:
            raise ValueError('recovery.notification_owner_missing')
        after = ''
        while page := effects.page(after=after, limit=256):
            for item in page:
                receipt = effects.get(item['effect_id'])
                if (receipt.kind.startswith('notification.')
                        and receipt != saved_effects.get(receipt.effect_id)):
                    raise ValueError('recovery.notification_owner_missing')
            after = page[-1]['effect_id']
        return saved_path, False, _notification_metadata(config)
    if original.name != 'dispatch.sqlite':
        raise ValueError('recovery.notification_owner_location_invalid')
    live = FileNotificationState(original.parent, capacity=config['capacity'], history_limit=config['history_limit'])
    if live.scope_id != config['scope_id'] or live.provider_id != config['provider_id']:
        raise ValueError('recovery.notification_owner_scope_conflict')
    temporary = Path(cleanup.enter_context(tempfile.TemporaryDirectory(prefix='stratbox-notification-authority-')))
    current_path = temporary / 'dispatch.sqlite'
    with closing(_readonly_database(original)) as monitor:
        generation = monitor.execute('PRAGMA data_version').fetchone()[0]
        before = _notification_metadata(live.recovery_metadata())
        live.export_checkpoint(current_path, max_bytes=min(limits.max_bytes, limits.max_file_bytes))
        if (monitor.execute('PRAGMA data_version').fetchone()[0] != generation
                or _notification_metadata(live.recovery_metadata()) != before):
            raise ValueError('recovery.notification_owner_changed_during_capture')
    stream_id = manifest['owners']['journal']['checkpoint']['stream_id']
    with closing(_readonly_database(saved_path)) as saved, closing(_readonly_database(current_path)) as current:
        if current.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('recovery.notification_checkpoint_integrity')
        for subscription, policy, cursor, stream, initial in saved.execute(
                'SELECT id,policy,cursor,stream,initial_after FROM subscriptions ORDER BY id'):
            latest = current.execute('SELECT policy,cursor,stream,initial_after FROM subscriptions WHERE id=?',
                                     (subscription,)).fetchone()
            if (latest is None or (latest[0], latest[2], latest[3]) != (policy, stream, initial)
                    or latest[1] < cursor):
                raise ValueError('recovery.notification_subscription_regressed')
        for subscription, cursor, stream, initial in current.execute(
                'SELECT id,cursor,stream,initial_after FROM subscriptions ORDER BY id'):
            if (stream != stream_id or type(cursor) is not int or type(initial) is not int
                    or not 0 <= initial <= cursor <= recovered_tail):
                raise ValueError('recovery.notification_cursor_conflict')
        for subscription, sequence, identity, selected in saved.execute(
                'SELECT subscription,sequence,identity,selected FROM consumed ORDER BY subscription,sequence'):
            latest = current.execute('SELECT identity,selected FROM consumed WHERE subscription=? AND sequence=?',
                                     (subscription, sequence)).fetchone()
            # Bounded consumed-position history may expire. A surviving overlap
            # still has to identify exactly the same consumed fact and choice.
            if latest is not None and latest != (identity, selected):
                raise ValueError('recovery.notification_consumption_conflict')
        for intent_id, subscription, sequence, payload in saved.execute(
                'SELECT id,subscription,sequence,payload FROM intents ORDER BY id'):
            latest = current.execute('SELECT subscription,sequence,payload FROM intents WHERE id=?',
                                     (intent_id,)).fetchone()
            if latest is not None:
                if latest != (subscription, sequence, payload):
                    raise ValueError('recovery.notification_intent_conflict')
            else:
                receipt = effects.get(intent_id)
                if (receipt is None or receipt.kind != 'notification.deliver' or receipt.status != 'confirmed'
                        or fingerprint(receipt.intent) != fingerprint(restore_tree(json.loads(payload)))):
                    raise ValueError('recovery.notification_delivery_authority_missing')
        for intent_id, subscription, sequence, payload in current.execute(
                'SELECT id,subscription,sequence,payload FROM intents ORDER BY id'):
            intent = restore_tree(json.loads(payload))
            state = current.execute('SELECT policy,cursor,stream FROM subscriptions WHERE id=?',
                                    (subscription,)).fetchone()
            fact = intent.get('payload') if isinstance(intent, Mapping) else None
            if (state is None or not isinstance(fact, Mapping) or intent.get('id') != intent_id
                    or intent.get('subscription_id') != subscription or fact.get('fact_sequence') != sequence
                    or fact.get('stream_id') != state[2] or not 0 < sequence <= state[1]
                    or intent_id != fingerprint((subscription, state[0], fact['stream_id'],
                                                 fact.get('run_id'), sequence, fingerprint(fact)))):
                raise ValueError('recovery.notification_intent_conflict')
            receipt = effects.get(intent_id)
            if receipt is not None and (receipt.kind != 'notification.deliver'
                    or fingerprint(receipt.intent) != fingerprint(intent)):
                raise ValueError('recovery.notification_delivery_authority_conflict')
        # A confirmed preparation/acknowledgement cannot coexist with an older
        # queue merely because both have the same number of rows.
        after = ''
        while page := effects.page(after=after, limit=256, status='confirmed'):
            for item in page:
                receipt = effects.get(item['effect_id'])
                if receipt.kind != 'notification.state' or not isinstance(receipt.value, Mapping):
                    continue
                checkpoint = receipt.value.get('checkpoint')
                if isinstance(checkpoint, Mapping):
                    current_checkpoint = current.execute('SELECT cursor,stream FROM subscriptions WHERE id=?',
                                                         (receipt.resource,)).fetchone()
                    if (current_checkpoint is None or current_checkpoint[1] != checkpoint.get('stream_id')
                            or current_checkpoint[0] < checkpoint.get('sequence', recovered_tail + 1)):
                        raise ValueError('recovery.notification_preparation_authority_conflict')
                acknowledgement = receipt.value.get('acknowledgement')
                if isinstance(acknowledgement, Mapping) and current.execute(
                        'SELECT 1 FROM intents WHERE id=?', (acknowledgement.get('intent_id'),)).fetchone():
                    raise ValueError('recovery.notification_acknowledgement_authority_conflict')
            after = page[-1]['effect_id']
    return current_path, True, before


def _verify_projected_references(state, effects, providers, limits):
    from stratbox.core.commands._storage import _provider_scope, _same_physical_reference
    with tempfile.TemporaryDirectory(prefix='stratbox-restored-dependencies-') as temporary:
        with sqlite3.connect(Path(temporary) / 'seen.sqlite') as db:
            db.execute('CREATE TABLE seen(identity TEXT PRIMARY KEY)')
            db.execute('CREATE TABLE snapshots(identity TEXT PRIMARY KEY)')
            after = ''
            while page := effects.page(after=after, limit=256, status='confirmed'):
                for item in page:
                    receipt = effects.get(item['effect_id'])
                    if receipt.kind == 'dataset.write' and isinstance(receipt.value, SnapshotRef):
                        db.execute('INSERT OR IGNORE INTO snapshots VALUES(?)', (fingerprint(receipt.value),))
                after = page[-1]['effect_id']
            count = total = 0
            for reference in _dependency_stream(state, effects, ()):
                # Every logical binding needs its own exact occurrence proof.
                # Only the expensive physical-byte verification is deduplicated.
                if isinstance(reference, ImmutableMaterialRef):
                    receipt = effects.get(reference.effect_id) if reference.effect_id else None
                    if (receipt is None or receipt.status != 'confirmed'
                            or not _same_physical_reference(reference, receipt.value)):
                        raise ValueError('recovery.retained_effect_authority_missing')
                elif isinstance(reference, SnapshotRef):
                    if db.execute('SELECT 1 FROM snapshots WHERE identity=?', (fingerprint(reference),)).fetchone() is None:
                        raise ValueError('recovery.retained_effect_authority_missing')
                else:
                    raise ValueError('recovery.reference_invalid')
                location = getattr(reference, 'location', getattr(reference, 'snapshot_id', None))
                key = fingerprint((type(reference).__name__, reference.provider_id,
                    reference.provider_scope, location, reference.identity))
                if not db.execute('INSERT OR IGNORE INTO seen VALUES(?)', (key,)).rowcount:
                    continue
                count += 1
                if count > limits.max_files:
                    raise ValueError('recovery.projected_dependency_limit')
                if isinstance(reference, ImmutableMaterialRef):
                    provider = providers.get('filestore')
                    if provider is None or reference.provider_scope != _provider_scope(provider, reference.location):
                        raise ValueError('recovery.artifact_scope_mismatch')
                    if reference.identity.size > limits.max_file_bytes:
                        raise ValueError('recovery.projected_dependency_limit')
                    with open_provider(provider, reference.location) as incoming:
                        if scan_identity(incoming, limit=reference.identity.size) != reference.identity:
                            raise ValueError('recovery.artifact_unavailable')
                    total += reference.identity.size
                elif isinstance(reference, SnapshotRef):
                    provider = providers.get('datasets')
                    if (provider is None or reference.provider_id != getattr(provider, 'provider_id', None)
                            or reference.provider_scope != getattr(provider, 'scope_id', None)):
                        raise ValueError('recovery.dataset_scope_mismatch')
                    provider.query(reference, None)
                    with open_provider(provider.store, reference.snapshot_id) as incoming:
                        total += scan_identity(incoming, limit=limits.max_file_bytes).size
                if total > limits.max_bytes:
                    raise ValueError('recovery.projected_dependency_limit')


def restore_recovery_package(directory, destination, *, providers=None, limits=None, admitted_types=None):
    """Restore state only after excluding the original local journal writer.

    Available authoritative journal suffixes are preserved and genuinely replayed
    into source state. Missing or divergent suffixes fail closed. Old occurrence
    authority remains fenced even after the exact journal tail is recovered.
    """
    from stratbox.core.storage.ownership_lock import held_anchor
    from stratbox.core.execution.effect_state import FileEffectState
    from stratbox.core.observability.journal.stream import FileJournal
    from stratbox.core.storage.source_state import SQLiteSourceState
    from stratbox.core.notifications.state import FileNotificationState
    from stratbox.core.observability.projections.source_state import SourceStateIndex
    from stratbox.core.observability.journal.stream import _atomic_json
    root, destination, limits = Path(directory).resolve(), Path(destination).resolve(), limits or RecoveryLimits()
    manifest = validate_recovery_package(root, limits=limits)
    if destination.is_relative_to(root):
        raise ValueError('recovery.destination_inside_package')
    marker = destination / 'restore-in-progress.json'
    resuming = destination.exists()
    progress = _read_json(marker, limits.max_manifest_bytes) if resuming and marker.is_file() else {}
    if resuming and progress.get('package_id') != manifest['package_id']:
        raise FileExistsError(destination)
    original = Path(manifest['owners']['journal']['directory'])
    if not original.is_dir() or not (original / 'stream-id').is_file():
        raise ValueError('recovery.original_owner_exclusion_required')
    if (original / 'stream-id').read_text().strip() != manifest['owners']['journal']['checkpoint']['stream_id']:
        raise ValueError('recovery.original_owner_identity_conflict')
    if destination.is_relative_to(original):
        raise ValueError('recovery.destination_inside_live_owner')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with held_anchor(original / 'writer.lock'):
        transfer_path = original / 'writer-closed.json'
        if transfer_path.exists():
            transfer = _read_json(transfer_path, limits.max_manifest_bytes)
            if (not resuming or transfer.get('package_id') != manifest['package_id']
                    or transfer.get('transferred_to') != str(destination / 'journal')
                    or transfer.get('stream_id') != manifest['owners']['journal']['checkpoint']['stream_id']):
                raise ValueError('recovery.writer_already_transferred')
        _verify_dependencies(root, dict(providers or {}), limits)
        destination.mkdir(exist_ok=resuming)
        if not resuming:
            progress = {'package_id': manifest['package_id'], 'phase': 'copy'}
            _write_json(marker, progress, limits.max_manifest_bytes)
        with held_anchor(destination / 'profile.lock'), ExitStack() as cleanup, ExitStack() as temporary:
            for item in _file_entries(root, limits):
                name = item['path']
                if name == 'source-state.sqlite' or name.startswith(('journal/', 'notifications/')):
                    outgoing, expected = destination / name, ByteIdentity(item['sha256'], item['size'])
                    if outgoing.exists():
                        replay_owner = name == 'source-state.sqlite' or name.startswith(('journal/', 'notifications/'))
                        if (not replay_owner or progress.get('phase', 'copy') == 'copy') and _file_identity(outgoing, limits.max_file_bytes) != expected:
                            raise ValueError('recovery.partial_owner_changed')
                    else:
                        _restore_file(_relative(root, name), outgoing, limits, expected)
            progress = {**progress, 'phase': 'journal_merging'}
            _atomic_json(marker, progress)
            recovered_tail = _recover_journal_suffix(root, original, destination / 'journal', manifest, limits)
            progress = {**progress, 'phase': 'journal_ready', 'recovered_tail': recovered_tail}
            _atomic_json(marker, progress)
            authoritative_effects, recovered_effects = _verified_effect_checkpoint(root, manifest, temporary, limits,
                admitted_types=admitted_types)
            if (destination / 'effects').exists():
                config = _read_json(authoritative_effects / 'checkpoint.json', 65536)
                effects = FileEffectState(destination / 'effects', admitted_types=admitted_types,
                    max_receipt_bytes=config['max_receipt_bytes'], max_hot_receipts=config['max_hot_receipts'],
                    max_hot_bytes=config['max_hot_bytes'])
                metadata = effects.recovery_metadata()
                if metadata['namespace_state'] != 'closed' or metadata['recovery_manifest_id'] != manifest['package_id']:
                    raise ValueError('recovery.partial_effect_owner_conflict')
                # A resumed restore must still represent this captured exact
                # authority. Any intervening original settlement requires a
                # fresh explicit restore instead of an unnoticed mixed cut.
                current = FileEffectState.checkpoint_view(authoritative_effects, admitted_types=admitted_types)
                after = ''
                seen = 0
                while page := current.page(after=after, limit=256):
                    for item in page:
                        if effects.get(item['effect_id']) != current.get(item['effect_id']):
                            raise ValueError('recovery.partial_effect_authority_changed')
                        seen += 1
                    after = page[-1]['effect_id']
                existing = effects.recovery_metadata()
                if seen != sum(existing[name] for name in ('unknown_count', 'confirmed_count', 'rejected_count')):
                    raise ValueError('recovery.partial_effect_authority_changed')
            else:
                effects = FileEffectState.restore_checkpoint(authoritative_effects, destination / 'effects',
                    recovery_manifest_id=manifest['package_id'], admitted_types=admitted_types)
            result = dict(providers or {})
            if 'datasets' in result:
                for role in ('dataset_reader', 'dataset_writer'):
                    if role in result and result[role] is not result['datasets']:
                        raise ValueError('recovery.dataset_owner_role_conflict')
                    result[role] = result['datasets']
            result['effect_state'] = effects
            state = SQLiteSourceState(destination / 'source-state.sqlite',
                **manifest['owners']['source_state'].get('limits', {}))
            cleanup.callback(state.close)
            result['source_state'] = state
            stream_id = manifest['owners']['journal']['checkpoint']['stream_id']
            restored_checkpoints = _metadata(state.recovery_metadata())['checkpoints']
            cutoff = manifest['owners']['journal']['checkpoint']['tail']
            if (len(restored_checkpoints) != 1 or restored_checkpoints[0]['stream_id'] != stream_id
                    or not cutoff <= restored_checkpoints[0]['applied_through'] <= recovered_tail
                    or not restored_checkpoints[0]['coverage_complete']):
                raise ValueError('recovery.projection_owner_conflict')
            if 'notification_state' in manifest['owners']:
                config = manifest['owners']['notification_state']
                notification_checkpoint, recovered_notifications, expected_notification = _verified_notification_checkpoint(
                    root, manifest, temporary, limits, effects, recovered_tail, admitted_types=admitted_types)
                _restore_file(notification_checkpoint, destination / 'notifications' / 'dispatch.sqlite', limits)
                result['notification_state'] = FileNotificationState(destination / 'notifications',
                    capacity=config['capacity'], history_limit=config['history_limit'])
                if _notification_metadata(result['notification_state'].recovery_metadata()) != expected_notification:
                    raise ValueError('recovery.notification_owner_conflict')
            journal = FileJournal(destination / 'journal',
                max_record_bytes=manifest['owners']['journal']['max_record_bytes'])
            cleanup.callback(journal.close)
            if journal.stream_id != stream_id or journal.checkpoint().tail != recovered_tail:
                raise ValueError('recovery.journal_owner_conflict')
            checkpoint = state.checkpoint(stream_id)
            while checkpoint.applied_through < recovered_tail:
                before = checkpoint.applied_through
                checkpoint = SourceStateIndex(state).advance(journal, max_pages=1000, page_limit=1000)
                if checkpoint.applied_through <= before:
                    raise ValueError('recovery.projection_replay_incomplete')
            if checkpoint.applied_through != recovered_tail:
                raise ValueError('recovery.projection_replay_incomplete')
            # Acquire the transferred writer even for an empty/no-new-facts cut.
            journal._before_mutation()
            _verify_projected_references(state, effects, result, limits)
            recovery = {'original_cut_tail': cutoff, 'recovered_tail': recovered_tail,
                'source_state_applied_through': checkpoint.applied_through,
                'effect_authority': 'surviving_original' if recovered_effects else 'backup_cut'}
            if 'notification_state' in manifest['owners']:
                recovery['notification_authority'] = 'surviving_original' if recovered_notifications else 'backup_cut'
            _atomic_json(marker, {**progress, 'phase': 'projection_ready', **recovery})
            # Exclusion lasts beyond this call: the old journal remains readable
            # but cannot reopen as a competing writer of the restored namespace.
            _atomic_json(original / 'writer-closed.json', {'stream_id': journal.stream_id,
                'package_id': manifest['package_id'], 'transferred_to': str(destination / 'journal'),
                'recovered_tail': recovered_tail})
            _atomic_json(destination / 'recovery.json', {'package_id': manifest['package_id'],
                'state': 'ready', 'effect_namespace': 'closed', 'restored_at': datetime.now(timezone.utc).isoformat(), **recovery})
            marker.unlink()
            cleanup.pop_all()
            return {'providers': result, 'journal': journal, 'manifest': manifest, 'recovery': recovery,
                'recovered_tail': recovered_tail}
