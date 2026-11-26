"""Reuse permission and exact dependency fingerprints."""
from dataclasses import dataclass
from .immutable import fingerprint

@dataclass(frozen=True, slots=True)
class ReuseContract:
    deterministic: bool = True
    shareable: bool = True
    completed: bool = True
    mutation: str = 'immutable'
    observation_scoped: bool = False

    def __post_init__(self):
        if self.mutation not in {'immutable','isolated','exclusive'}:
            raise ValueError('reuse.invalid_mutation')
        if any(type(getattr(self,name)) is not bool for name in
               ('deterministic','shareable','completed','observation_scoped')):
            raise TypeError('reuse.boolean_policy_required')

    @property
    def inflight_eligible(self):
        return self.shareable and (self.deterministic or self.observation_scoped) and self.mutation != 'exclusive'

    @property
    def completed_eligible(self):
        return self.inflight_eligible and self.completed
