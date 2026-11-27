"""Atomic subscription checkpoints, consumed-position evidence and pending intents."""
from __future__ import annotations
from pathlib import Path
from threading import RLock
import json
import sqlite3
from contextlib import contextmanager
from uuid import uuid4
from collections.abc import Mapping

from stratbox.shared.data.values import canonical_tree, restore_tree, fingerprint, immutable
from .consumption import NotificationRejected, normalize, prepare_consumption


def _policy(selector, route):
    return fingerprint((dict(selector or {}), route))


def _selector(value):
    if value is None: return immutable({})
    if not isinstance(value,Mapping) or any(not isinstance(key,str) or not key for key in value):
        raise NotificationRejected('notification.invalid_selector')
    return immutable(dict(value))


def _intent(fact, subscription_id, policy, route):
    payload = dict(kind=fact.kind, run_id=fact.run_id, scope_id=fact.scope_id,
        command_id=fact.command_id, output_name=fact.output_name, fact_sequence=fact.sequence,
        data=dict(fact.data), stream_id=fact.stream_id)
    return immutable({'id': fingerprint((subscription_id, policy, fact.stream_id, fact.run_id, fact.sequence,fingerprint(payload))),
        'subscription_id': subscription_id, 'route': route, 'payload': payload})


class MemoryNotificationState:
    provider_id = 'notifications.memory'

    def __init__(self, capacity=10000, *, history_limit=10000):
        if type(capacity) is not int or capacity < 1 or type(history_limit) is not int or history_limit < 1:
            raise NotificationRejected('notification.invalid_capacity')
        self.capacity, self.history_limit = capacity, history_limit
        self._lock, self._subscriptions = RLock(), {}
        self.scope_id = uuid4().hex

    def register(self, subscription_id, *, stream_id, after=0, selector=None, route=None):
        _initial_checkpoint(subscription_id,stream_id,after)
        selector=_selector(selector)
        policy=_policy(selector,route)
        with self._lock:
            previous=self._subscriptions.get(subscription_id)
            if previous is not None:
                if (previous['policy']!=policy or previous['stream']!=stream_id
                        or previous['initial_after']!=after):
                    raise NotificationRejected('notification.initial_checkpoint_conflict')
            else:
                if len(self._subscriptions)>=self.capacity:
                    raise NotificationRejected('notification.subscription_capacity_exhausted')
                self._subscriptions[subscription_id]={'policy':policy,'cursor':after,'initial_after':after,
                    'stream':stream_id,'intents':{},'seen':{}}
            return self.checkpoint(subscription_id)

    def prepare(self, facts, *, subscription_id='default', selector=None, route=None):
        _subscription_id(subscription_id)
        selector = _selector(selector)
        page = normalize(facts, selector)
        policy = _policy(selector, route)
        with self._lock:
            previous = self._subscriptions.get(subscription_id)
            if previous is None and len(self._subscriptions) >= self.capacity:
                raise NotificationRejected('notification.subscription_capacity_exhausted')
            if previous is not None and previous['policy'] != policy:
                raise NotificationRejected('notification.policy_changed_requires_new_subscription')
            state = previous or {'policy': policy, 'cursor': 0, 'initial_after':0, 'intents': {}, 'stream': None, 'seen': {}}
            cursor, stream, updates, additions = prepare_consumption(page, cursor=state['cursor'],
                previous_stream=state['stream'], seen=state['seen'], selector=selector)
            intents = dict(state['intents'])
            selected = tuple(_intent(fact, subscription_id, policy, route) for fact in additions)
            for intent in selected:
                intents.setdefault(intent['id'], intent)
            occupied = sum(len(value['intents']) for key, value in self._subscriptions.items() if key != subscription_id)
            if occupied + len(intents) > self.capacity:
                raise NotificationRejected('notification.capacity_exhausted')
            seen = {**state['seen'], **updates}
            subscriptions = dict(self._subscriptions)
            subscriptions.pop(subscription_id, None)
            subscriptions[subscription_id] = {'policy': policy, 'cursor': cursor,
                'initial_after':state['initial_after'],'intents': intents, 'stream': stream, 'seen': seen}
            overflow = sum(len(value['seen']) for value in subscriptions.values()) - self.history_limit
            for key, value in tuple(subscriptions.items()):
                if overflow <= 0: break
                removed = min(overflow, len(value['seen']))
                keep = sorted(value['seen'])[removed:]
                subscriptions[key] = {**value, 'seen': {sequence:value['seen'][sequence] for sequence in keep}}
                overflow -= removed
            self._subscriptions = subscriptions
            return selected

    def preparation_basis(self, subscription_id='default'):
        with self._lock:
            state = self._subscriptions.get(subscription_id)
            return {'checkpoint':None if state is None else (state['cursor'],state['stream']),
                'pending_count':sum(len(value['intents']) for value in self._subscriptions.values()),
                'capacity':self.capacity}

    def checkpoint(self, subscription_id='default'):
        with self._lock:
            state = self._subscriptions.get(subscription_id)
            return None if state is None else {'sequence': state['cursor'], 'stream_id': state['stream']}

    def pending(self, subscription_id='default', *, after_sequence=0, limit=1000):
        _page_limits(after_sequence, limit)
        with self._lock:
            state = self._subscriptions.get(subscription_id)
            return () if state is None else tuple(sorted((item for item in state['intents'].values()
                if item['payload']['fact_sequence'] > after_sequence),
                key=lambda item: (item['payload']['fact_sequence'], item['id'])))[:limit]

    def intent(self, subscription_id, intent_id):
        with self._lock:
            state=self._subscriptions.get(subscription_id)
            return None if state is None else state['intents'].get(intent_id)

    def acknowledge(self, subscription_id, intent_id, receipt):
        _confirmed_intent(intent_id, receipt)
        with self._lock:
            state = self._subscriptions.get(subscription_id)
            removed = state is not None and state['intents'].pop(intent_id, None) is not None
            return {'removed': bool(removed), 'intent_id': intent_id}


class FileNotificationState:
    """A SQLite transaction commits cursor, consumed identities and dispatches together."""
    provider_id = 'notifications.sqlite'

    def __init__(self, directory, *, capacity=10000, history_limit=10000):
        if any(type(value) is not int or value<1 for value in (capacity,history_limit)):
            raise NotificationRejected('notification.invalid_capacity')
        self.capacity, self.history_limit = capacity, history_limit
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._database = self.directory / 'dispatch.sqlite'
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS state_identity (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute("INSERT OR IGNORE INTO state_identity VALUES ('identity',?)", (uuid4().hex,))
            self.scope_id = db.execute("SELECT value FROM state_identity WHERE key='identity'").fetchone()[0]
            db.execute('CREATE TABLE IF NOT EXISTS subscriptions (id TEXT PRIMARY KEY, policy TEXT NOT NULL, cursor INTEGER NOT NULL, stream TEXT, initial_after INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS intents (id TEXT PRIMARY KEY, subscription TEXT NOT NULL, sequence INTEGER NOT NULL, payload TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS intents_page ON intents(subscription, sequence, id)')
            db.execute('CREATE TABLE IF NOT EXISTS consumed (subscription TEXT NOT NULL, sequence INTEGER NOT NULL, identity TEXT, selected INTEGER NOT NULL, PRIMARY KEY(subscription, sequence))')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self._database, timeout=30)
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def register(self, subscription_id, *, stream_id, after=0, selector=None, route=None):
        _initial_checkpoint(subscription_id,stream_id,after)
        selector=_selector(selector)
        policy=_policy(selector,route)
        with self._lock,self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous=db.execute('SELECT policy,cursor,stream,initial_after FROM subscriptions WHERE id=?',(subscription_id,)).fetchone()
            if previous is not None:
                if previous[0]!=policy or previous[2]!=stream_id or previous[3]!=after:
                    raise NotificationRejected('notification.initial_checkpoint_conflict')
                return {'sequence':previous[1],'stream_id':previous[2]}
            if db.execute('SELECT count(*) FROM subscriptions').fetchone()[0]>=self.capacity:
                raise NotificationRejected('notification.subscription_capacity_exhausted')
            db.execute('INSERT INTO subscriptions VALUES (?,?,?,?,?)',(subscription_id,policy,after,stream_id,after))
            return {'sequence':after,'stream_id':stream_id}

    def prepare(self, facts, *, subscription_id='default', selector=None, route=None):
        _subscription_id(subscription_id)
        selector = _selector(selector)
        page = normalize(facts, selector)
        policy = _policy(selector, route)
        with self._lock, self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT policy,cursor,stream,initial_after FROM subscriptions WHERE id=?', (subscription_id,)).fetchone()
            if previous is None and db.execute('SELECT count(*) FROM subscriptions').fetchone()[0]>=self.capacity:
                raise NotificationRejected('notification.subscription_capacity_exhausted')
            if previous is not None and previous[0] != policy:
                raise NotificationRejected('notification.policy_changed_requires_new_subscription')
            seen = {sequence: (identity, bool(selected)) for sequence, identity, selected in db.execute(
                'SELECT sequence,identity,selected FROM consumed WHERE subscription=? AND sequence>? AND sequence<=?',
                (subscription_id, page.after, page.through)).fetchall()}
            cursor, stream, updates, additions = prepare_consumption(page,
                cursor=previous[1] if previous else 0, previous_stream=previous[2] if previous else None,
                seen=seen, selector=selector)
            selected = tuple(_intent(fact, subscription_id, policy, route) for fact in additions)
            if db.execute('SELECT count(*) FROM intents').fetchone()[0]+len(selected)>self.capacity:
                raise NotificationRejected('notification.capacity_exhausted')
            for intent in selected:
                raw = json.dumps(canonical_tree(intent), sort_keys=True, separators=(',', ':'))
                db.execute('INSERT OR IGNORE INTO intents VALUES (?,?,?,?)',
                    (intent['id'], subscription_id, intent['payload']['fact_sequence'], raw))
            for sequence, (identity, admitted) in updates.items():
                db.execute('INSERT INTO consumed VALUES (?,?,?,?) ON CONFLICT(subscription,sequence) DO UPDATE SET identity=excluded.identity,selected=excluded.selected',
                    (subscription_id, sequence, identity, int(admitted)))
            db.execute('INSERT INTO subscriptions VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET cursor=excluded.cursor,stream=excluded.stream',
                (subscription_id, policy, cursor, stream,previous[3] if previous else 0))
            db.execute('DELETE FROM consumed WHERE rowid IN (SELECT rowid FROM consumed ORDER BY rowid DESC LIMIT -1 OFFSET ?)',
                (self.history_limit,))
            return selected

    def preparation_basis(self, subscription_id='default'):
        with self._lock, self._connect() as db:
            checkpoint=db.execute('SELECT cursor,stream FROM subscriptions WHERE id=?',(subscription_id,)).fetchone()
            return {'checkpoint':checkpoint,'pending_count':db.execute('SELECT count(*) FROM intents').fetchone()[0],
                'capacity':self.capacity}

    def checkpoint(self, subscription_id='default'):
        with self._lock, self._connect() as db:
            row = db.execute('SELECT cursor,stream FROM subscriptions WHERE id=?', (subscription_id,)).fetchone()
            return None if row is None else {'sequence': row[0], 'stream_id': row[1]}

    def pending(self, subscription_id='default', *, after_sequence=0, limit=1000):
        _page_limits(after_sequence, limit)
        with self._lock, self._connect() as db:
            rows = db.execute('SELECT payload FROM intents WHERE subscription=? AND sequence>? ORDER BY sequence,id LIMIT ?',
                (subscription_id, after_sequence, limit)).fetchall()
            return tuple(restore_tree(json.loads(row[0])) for row in rows)

    def intent(self, subscription_id, intent_id):
        with self._lock,self._connect() as db:
            row=db.execute('SELECT payload FROM intents WHERE subscription=? AND id=?',(subscription_id,intent_id)).fetchone()
            return None if row is None else immutable(restore_tree(json.loads(row[0])))

    def acknowledge(self, subscription_id, intent_id, receipt):
        _confirmed_intent(intent_id, receipt)
        with self._lock, self._connect() as db:
            cursor = db.execute('DELETE FROM intents WHERE subscription=? AND id=?', (subscription_id, intent_id))
            return {'removed': bool(cursor.rowcount), 'intent_id': intent_id}

    def recovery_metadata(self):
        """Subscription cuts and pending counts without loading intent bodies."""
        with self._lock, self._connect() as db:
            rows = db.execute('SELECT id,cursor,stream,initial_after FROM subscriptions ORDER BY id LIMIT 10001').fetchall()
            if len(rows) > 10000:
                raise NotificationRejected('notification.recovery_subscription_limit')
            return {'provider_id': self.provider_id, 'scope_id': self.scope_id,
                    'database': str(self._database.resolve()),
                    'subscriptions': tuple({'subscription_id': row[0], 'sequence': row[1],
                                            'stream_id': row[2], 'initial_after': row[3]} for row in rows),
                    'pending_count': db.execute('SELECT count(*) FROM intents').fetchone()[0],
                    'capacity': self.capacity, 'history_limit': self.history_limit}

    def export_checkpoint(self, destination, *, max_bytes=None):
        """Export cursor and outbox in the same SQLite snapshot."""
        if max_bytes is not None and (type(max_bytes) is not int or max_bytes < 1):
            raise NotificationRejected('notification.checkpoint_limit_invalid')
        destination = Path(destination).resolve()
        if destination.exists() or destination == self._database.resolve():
            raise NotificationRejected('notification.checkpoint_destination_exists')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connect() as source:
            page_size = source.execute('PRAGMA page_size').fetchone()[0]
            def check_size(_status, _remaining, total):
                if max_bytes is not None and total * page_size > max_bytes:
                    raise NotificationRejected('notification.checkpoint_size_limit')
            check_size(None, None, source.execute('PRAGMA page_count').fetchone()[0])
            target = sqlite3.connect(destination)
            try:
                source.backup(target, pages=64, progress=check_size)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise NotificationRejected('notification.checkpoint_integrity')
            except BaseException:
                target.close()
                destination.unlink(missing_ok=True)
                raise
            finally:
                target.close()
        return str(destination)


def _page_limits(after_sequence, limit):
    if type(after_sequence) is not int or after_sequence < 0 or type(limit) is not int or not 0 < limit <= 10000:
        raise NotificationRejected('notification.invalid_page')


def _subscription_id(value):
    if not isinstance(value, str) or not value or len(value)>4096:
        raise NotificationRejected('notification.invalid_subscription')


def _initial_checkpoint(subscription_id,stream_id,after):
    _subscription_id(subscription_id)
    if not isinstance(stream_id,str) or not stream_id or len(stream_id)>4096 or type(after) is not int or after<0:
        raise NotificationRejected('notification.invalid_initial_checkpoint')


def _confirmed_intent(intent_id, receipt):
    if (getattr(receipt, 'effect_id', None) != intent_id or getattr(receipt, 'status', None) != 'confirmed'
            or getattr(receipt, 'kind', None) != 'notification.deliver'):
        raise NotificationRejected('notification.confirmed_matching_receipt_required')
