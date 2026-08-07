from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class PublicationSupport:
    region_codes: frozenset[str]
    class_codes: frozenset[str]
    metric: str

    @property
    def is_empty(self) -> bool:
        return not self.region_codes or not self.class_codes

    @property
    def is_single_cell(self) -> bool:
        return len(self.region_codes) == 1 and len(self.class_codes) == 1

    def intersect(self, other: 'PublicationSupport') -> 'PublicationSupport':
        if self.metric != other.metric:
            return PublicationSupport(frozenset(), frozenset(), self.metric)
        return PublicationSupport(
            self.region_codes.intersection(other.region_codes),
            self.class_codes.intersection(other.class_codes),
            self.metric,
        )


@dataclass(frozen=True)
class PublishedMassToken:
    token_id: str
    root_fact_id: str
    root_quantity_id: str
    portfolio_scope: str | None
    metric: str
    published_value: float
    support: PublicationSupport
    anchor_quantity_ids: frozenset[str]
    supporting_fact_ids: tuple[str, ...]
    supporting_partition_ids: tuple[str, ...]
    assumption_tier: int
    status: str = 'ACTIVE'

    def localize(
        self,
        *,
        child_quantity_id: str,
        child_support: PublicationSupport,
        partition_id: str,
        supporting_fact_ids: tuple[str, ...],
        assumption_tier: int,
    ) -> 'PublishedMassToken':
        support = self.support.intersect(child_support)
        return replace(
            self,
            support=support,
            anchor_quantity_ids=self.anchor_quantity_ids.union({str(child_quantity_id)}),
            supporting_fact_ids=tuple(
                dict.fromkeys((*self.supporting_fact_ids, *supporting_fact_ids))
            ),
            supporting_partition_ids=tuple(
                dict.fromkeys((*self.supporting_partition_ids, str(partition_id)))
            ),
            assumption_tier=max(int(self.assumption_tier), int(assumption_tier)),
            status='CONFLICTING_LOCALIZATIONS' if support.is_empty else 'ACTIVE',
        )
