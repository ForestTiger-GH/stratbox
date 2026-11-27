"""An explicitly owned local persistent profile; no hidden recurring workload."""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
import shutil

from .client import StrategyBox


@dataclass(frozen=True, slots=True)
class PersistentLimits:
    min_free_bytes: int = 64 * 1024**2
    projection_reserve_records: int = 100
    projection_reserve_bytes: int = 4 * 1024**2
    source_state: dict = field(default_factory=dict)
    effects: dict = field(default_factory=dict)
    notifications: dict = field(default_factory=dict)
    journal: dict = field(default_factory=dict)

    def __post_init__(self):
        from types import MappingProxyType
        for name in ('min_free_bytes', 'projection_reserve_records', 'projection_reserve_bytes'):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError('profile.reserve_invalid')
        for name in ('source_state', 'effects', 'notifications', 'journal'):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


class LocalProfile:
    """Own one coordinator and writer on one qualified local filesystem.

    The host chooses tasks, polling cadence, archive horizons and maintenance.
    Filesystem free-space admission is a reserve threshold; it cannot constrain
    unrelated writers or guarantee survival of hardware/power failure.
    """
    def __init__(self, directory, *, artifact_root, dataset_root=None, limits=None,
                 settings=None, providers=None, catalog=None, domains=None, observer=None):
        from stratbox.core.storage.ownership_lock import held_anchor
        from stratbox.core.storage.source_state import SQLiteSourceState
        from stratbox.core.storage.filestore import LocalFileStore
        from stratbox.core.storage.datasets import FileDatasetStore
        from stratbox.core.execution.effect_state import FileEffectState
        from stratbox.core.observability.journal.stream import FileJournal
        from stratbox.core.notifications.state import FileNotificationState
        self.directory, self.limits = Path(directory).resolve(), limits or PersistentLimits()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.artifact_root = Path(artifact_root).resolve()
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.dataset_root = Path(dataset_root).resolve() if dataset_root is not None else self.directory / 'datasets'
        self._stack, self._closed = ExitStack(), False
        try:
            self._stack.enter_context(held_anchor(self.directory / 'profile.lock'))
            if (self.directory / 'restore-in-progress.json').exists():
                raise ValueError('profile.restore_incomplete')
            if (self.directory / 'journal' / 'writer-closed.json').exists():
                raise ValueError('profile.writer_namespace_closed')
            state = SQLiteSourceState(self.directory / 'source-state.sqlite', **self.limits.source_state)
            self._stack.callback(state.close)
            journal = FileJournal(self.directory / 'journal', **self.limits.journal)
            self._stack.callback(journal.close)
            owned = {'source_state': state, 'effect_state': FileEffectState(self.directory / 'effects', **self.limits.effects),
                'notification_state': FileNotificationState(self.directory / 'notifications', **self.limits.notifications),
                'filestore': LocalFileStore(str(self.artifact_root)), 'datasets': FileDatasetStore(self.dataset_root)}
            owned['dataset_reader'] = owned['dataset_writer'] = owned['datasets']
            extra = dict(providers or {})
            if extra.keys() & owned.keys():
                raise ValueError('profile.owned_provider_override')
            self.providers, self.journal = {**owned, **extra}, journal
            self.box = StrategyBox(settings=settings, providers=self.providers, journal=journal, observer=observer,
                catalog=catalog, domains=domains, admission_guard=self._admit)
            # This registration is durable before work can consume journal space.
            checkpoint = state.checkpoint(journal.stream_id)
            applied = checkpoint.applied_through if checkpoint else 0
            journal_checkpoint = journal.checkpoint()
            if applied < journal_checkpoint.retained_after:
                raise ValueError('source_state.checkpoint_expired')
            registered = journal_checkpoint.consumers.get('source-state')
            if registered is not None and registered > applied:
                raise ValueError('source_state.acknowledgement_ahead')
            # A process may exit after the SQLite transaction and before the
            # journal acknowledgement. Preserve that older protected cursor so
            # normal projection replay can complete the original handshake.
            journal.register_consumer('source-state', after=applied if registered is None else registered)
        except BaseException:
            self._stack.close()
            raise

    def _admit(self, plan):
        from stratbox.core.execution.service import ExecutionFailure
        if self._closed:
            raise ExecutionFailure('profile.closed')
        # Receipt reconciliation consumes already reserved settlement capacity.
        # Blocking it at a low watermark would prevent the recovery that frees
        # that capacity. New claims still pass the effect owner's atomic gate.
        recovery_commands = {'command.artifact.reconcile', 'command.notification.reconcile'}
        if plan.tasks and all(getattr(task, 'kind', None) == 'command'
                              and task.command.id in recovery_commands for task in plan.tasks):
            return
        for root in (self.directory, self.artifact_root, self.dataset_root):
            if shutil.disk_usage(root).free < self.limits.min_free_bytes:
                raise ExecutionFailure('profile.settlement_disk_reserve')
        usage = self.providers['source_state'].storage_usage()
        if (usage['hot_records'] + self.limits.projection_reserve_records >= usage['max_hot_records']
                or usage['hot_bytes'] + self.limits.projection_reserve_bytes >= usage['max_hot_bytes']):
            raise ExecutionFailure('profile.projection_maintenance_required')
        # The effect owner atomically reserves each unknown receipt's maximum
        # terminal body at begin; settled work can complete below this threshold.
        effects = self.providers['effect_state'].usage()
        from .readiness import _commands
        effectful = any(task.command.effects for _, task, _ in _commands(plan))
        if effectful and effects.get('effective_hot_bytes', effects['hot_bytes']) >= effects['max_hot_bytes']:
            raise ExecutionFailure('profile.effect_maintenance_required')

    def maintain(self, *, disposition='archive', through=None, max_pages=10, page_limit=1000, prune_through=None,
                 retire_current_accepted_ids=(), protected_accepted_ids=(), protected_authority=(),
                 retire_persistent=False):
        """Bound projection, effect-body and journal maintenance independently."""
        from stratbox.core.storage.source_state import SourceStateRetention
        if type(max_pages) is not int or not 1 <= max_pages <= 1000 or type(page_limit) is not int or not 1 <= page_limit <= 10000:
            raise ValueError('profile.maintenance_limit_invalid')
        checkpoint = self.box.advance_source_state(max_pages=max_pages, page_limit=page_limit)
        through = checkpoint.applied_through if through is None else through
        reports = []
        for _ in range(max_pages):
            report = self.providers['source_state'].maintain(stream_id=self.journal.stream_id,
                policy=SourceStateRetention(through, disposition, page_limit,
                    retire_persistent=retire_persistent, protected_accepted_ids=protected_accepted_ids,
                    protected_authority=protected_authority, retire_current_accepted_ids=retire_current_accepted_ids))
            reports.append(report)
            if not report.has_more:
                break
        effects = self.providers['effect_state']
        archived_effects = 0
        for status in ('confirmed', 'rejected'):
            page = effects.page(limit=page_limit, status=status, archived=False)
            if page:
                effects.archive(tuple(item['effect_id'] for item in page))
                archived_effects += len(page)
        archived = self.journal.archive(through, max_segments=max_pages)
        pruned = self.journal.prune(prune_through, max_segments=max_pages) if prune_through is not None else None
        return {'projection': tuple(reports), 'effect_receipts_archived': archived_effects,
                'journal_archive': archived, 'journal_prune': pruned, 'usage': self.usage()}

    def usage(self):
        return {'source_state': self.providers['source_state'].storage_usage(),
                'effects': dict(self.providers['effect_state'].usage()),
                'notifications': self.providers['notification_state'].recovery_metadata(),
                'journal': self.journal.checkpoint(),
                'filesystem_free_bytes': shutil.disk_usage(self.directory).free}

    def export_recovery(self, destination, **kwargs):
        return self.box.export_recovery(destination, **kwargs)

    def close(self):
        if self._closed:
            return
        try:
            self.box.close(wait=True)
        finally:
            self._closed = True
            self._stack.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
