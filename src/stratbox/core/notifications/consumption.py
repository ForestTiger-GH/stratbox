"""Contiguous journal consumption proofs and content-pinned replay admission."""
from dataclasses import dataclass, replace
from collections.abc import Mapping
from itertools import islice

from stratbox.shared.data.journal import JournalFact, JournalPage
from stratbox.core.storage.filestore.types import MutationRejected
from stratbox.shared.data.values import fingerprint, immutable

MAX_PAGE_POSITIONS = 10000


class NotificationRejected(MutationRejected, ValueError):
    def __init__(self, code):
        super().__init__(code, code=code)


@dataclass(frozen=True)
class Consumption:
    stream_id: str | None
    after: int
    through: int
    facts: tuple[JournalFact, ...]
    retained_after: int = 0


def selected(fact, selector):
    if fact.data.get('origin') == 'notification' and selector.get('origin') != 'notification':
        return False
    return all(getattr(fact, key, fact.data.get(key)) == value for key, value in selector.items())


def normalize(source, selector):
    """Bare facts certify only their own contiguous extent; a page certifies its scan."""
    if not isinstance(selector, Mapping):
        raise NotificationRejected('notification.invalid_selector')
    if isinstance(source, JournalPage):
        if source.scanned_through - source.after > MAX_PAGE_POSITIONS:
            raise NotificationRejected('notification.page_limit')
        if any(selector.get(key) != value for key, value in source.filters.items()):
            raise NotificationRejected('notification.page_filter_not_bound')
        facts = source.facts
        stream, after, through, retained = source.stream_id, source.after, source.scanned_through, source.retained_after
    else:
        facts = tuple(islice(iter(source), MAX_PAGE_POSITIONS + 1))
        if len(facts) > MAX_PAGE_POSITIONS:
            raise NotificationRejected('notification.page_limit')
        stream, after, through, retained = None, 0, 0, 0
    snapshots = []
    previous = None
    for fact in facts:
        if not isinstance(fact, JournalFact) or type(fact.sequence) is not int or fact.sequence < 1:
            raise NotificationRejected('notification.invalid_fact')
        if not isinstance(fact.stream_id, str) or not fact.stream_id:
            raise NotificationRejected('notification.mixed_or_unknown_fact_stream')
        if previous is not None and fact.sequence <= previous:
            raise NotificationRejected('notification.duplicate_or_reordered_fact')
        if not isinstance(source, JournalPage) and previous is not None and fact.sequence != previous + 1:
            raise NotificationRejected('notification.sequence_gap')
        if stream is not None and fact.stream_id != stream:
            raise NotificationRejected('notification.mixed_or_unknown_fact_stream')
        stream, previous = fact.stream_id, fact.sequence
        snapshots.append(replace(fact, data=immutable(fact.data)))
    if not isinstance(source, JournalPage) and snapshots:
        after, through = snapshots[0].sequence - 1, snapshots[-1].sequence
    return Consumption(stream, after, through, tuple(snapshots), retained)


def prepare_consumption(page, *, cursor, previous_stream, seen, selector):
    """Return a staged cursor and ledger delta without mutating any owner."""
    if page.stream_id is not None and previous_stream is not None and page.stream_id != previous_stream:
        raise NotificationRejected('notification.journal_stream_changed')
    if cursor < page.retained_after:
        raise NotificationRejected('notification.cursor_expired')
    if page.after > cursor:
        raise NotificationRejected('notification.sequence_gap')
    supplied = {fact.sequence: fact for fact in page.facts}
    updates, additions = {}, []
    for sequence in range(page.after + 1, page.through + 1):
        fact = supplied.get(sequence)
        admitted = fact is not None and selected(fact, selector)
        identity = fingerprint(fact) if fact is not None else None
        if sequence <= cursor:
            if sequence not in seen:
                raise NotificationRejected('notification.replay_expired')
            previous_identity, previous_selected = seen[sequence]
            if fact is None:
                if previous_selected:
                    raise NotificationRejected('notification.replay_content_conflict')
            elif previous_identity is None:
                if admitted:
                    raise NotificationRejected('notification.replay_content_conflict')
                updates[sequence] = identity, False
            elif previous_identity != identity:
                raise NotificationRejected('notification.replay_content_conflict')
        else:
            updates[sequence] = identity, admitted
            if admitted:
                additions.append(fact)
    return max(cursor, page.through), page.stream_id or previous_stream, updates, tuple(additions)
