"""Explicit, bounded retention for the source projection's independent lifetime."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceStateRetention:
    """Move older facts to cold storage or retire a declared history prefix.

    Current records survive unless the host explicitly retires their accepted
    IDs. ``discard`` retires historical projection evidence, including its
    unreferenced authority. Retained artifacts themselves
    are outside this operation. Their externally required accepted IDs and
    authority IDs must be pinned by the host before retiring their index history.
    """
    through: int
    disposition: str = 'archive'
    limit: int = 1000
    retire_persistent: bool = False
    protected_accepted_ids: tuple[str, ...] = ()
    protected_authority: tuple[tuple[str, str], ...] = ()
    retire_current_accepted_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if (type(self.through) is not int or self.through < 0
                or self.disposition not in {'archive', 'discard'}
                or type(self.limit) is not int or not 1 <= self.limit <= 10000
                or type(self.retire_persistent) is not bool):
            raise ValueError('source_state.retention_invalid')
        ids = tuple(self.protected_accepted_ids)
        retired = tuple(self.retire_current_accepted_ids)
        authority = tuple(tuple(value) for value in self.protected_authority)
        if (len(ids) + len(authority) + len(retired) > 10000
                or any(not isinstance(value, str) or not value for value in (*ids, *retired))
                or any(len(value) != 2 or value[0] not in {'certificate', 'source_use', 'acquisition'}
                       or not isinstance(value[1], str) or not value[1] for value in authority)):
            raise ValueError('source_state.retention_pins_invalid')
        object.__setattr__(self, 'protected_accepted_ids', ids)
        object.__setattr__(self, 'protected_authority', authority)
        object.__setattr__(self, 'retire_current_accepted_ids', tuple(dict.fromkeys(retired)))


@dataclass(frozen=True, slots=True)
class SourceStateMaintenance:
    stream_id: str
    through: int
    disposition: str
    records: int = 0
    authority: int = 0
    retention_links: int = 0
    has_more: bool = False
    history_retained_after: int = 0
    retired_current: int = 0


def record_authority(value):
    """Index the evidence reachable from a projected record once at ingress."""
    from stratbox.shared.data.processing import SourceObservation, RetainedOutput
    from stratbox.shared.data.values import fingerprint
    if isinstance(value, SourceObservation):
        return (('acquisition', value.evidence_identity),)
    if isinstance(value, RetainedOutput):
        refs = {('certificate', identity) for identity in value.certificate_ids}
        for use in value.source_uses:
            refs.add(('source_use', fingerprint(use)))
            if use.evidence_ref:
                # Evidence references can name either accepted acquisition
                # evidence or a validator certificate; retain both namespaces.
                refs.add(('acquisition', use.evidence_ref))
                refs.add(('certificate', use.evidence_ref))
        return tuple(sorted(refs))
    return ()
