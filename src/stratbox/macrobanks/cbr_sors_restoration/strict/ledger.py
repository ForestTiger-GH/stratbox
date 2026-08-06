from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.publication import (
    PublicationInterval,
    RoundingPolicy,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.certification import certify_interval

_PRECISION_RANK = {'NONE': 0, 'PUBLISHED': 1, 'EXACT': 2}


@dataclass
class SorsFactLedger:
    """Append-only evidence ledger for base RKVS quantities."""

    _records: list[dict[str, object]] = field(default_factory=list)
    _events: list[dict[str, object]] = field(default_factory=list)
    _current_by_quantity: dict[str, int] = field(default_factory=dict)
    _promotion_sequence: int = 0

    @property
    def current_quantity_ids(self) -> set[str]:
        return set(self._current_by_quantity)

    @staticmethod
    def _derivation_support(
        row,
        derivation_lookup: pd.DataFrame,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        derivation_id = getattr(row, 'last_derivation_id', None)
        if derivation_id is None or pd.isna(derivation_id) or derivation_lookup.empty:
            return (), ()
        key = str(derivation_id)
        if key not in derivation_lookup.index:
            return (), ()
        item = derivation_lookup.loc[key]
        if isinstance(item, pd.DataFrame):
            item = item.iloc[-1]
        relation_ids = (str(item.relation_id),) if 'relation_id' in item else ()
        supporting = (
            tuple(item.supporting_quantity_ids)
            if 'supporting_quantity_ids' in item
            and isinstance(item.supporting_quantity_ids, (tuple, list))
            else ()
        )
        return relation_ids, supporting

    def promote_from_quantities(
        self,
        quantities_grid: pd.DataFrame,
        target_catalog_grid: pd.DataFrame,
        derivations_grid: pd.DataFrame,
        *,
        policy: RoundingPolicy,
        point_tolerance: float,
        restoration_pass: int,
        evidence_layer: str = 'STRICT',
        uniqueness_basis: str | None = None,
        largest_horizon: str | None = None,
        attempt_id: str | None = None,
        proof_ids: tuple[str, ...] = (),
        quantity_ids: set[str] | None = None,
    ) -> tuple[set[str], pd.DataFrame]:
        quantities = quantities_grid[
            quantities_grid['quantity_kind'].eq('ATOMIC_COMPONENT')
        ].copy()
        if quantity_ids is not None:
            quantities = quantities[
                quantities['quantity_id'].astype(str).isin(quantity_ids)
            ]
        catalog = target_catalog_grid.set_index('quantity_id', drop=False)
        derivation_lookup = (
            derivations_grid.drop_duplicates('derivation_id', keep='last')
            .assign(derivation_id=lambda frame: frame['derivation_id'].astype(str))
            .set_index('derivation_id', drop=False)
            if not derivations_grid.empty
            else pd.DataFrame()
        )
        promoted: set[str] = set()
        event_rows: list[dict[str, object]] = []
        for row in quantities.itertuples(index=False):
            quantity_id = str(row.quantity_id)
            interval = PublicationInterval(
                float(row.lower_bound),
                float(row.upper_bound),
                bool(row.lower_attained),
                bool(row.upper_attained),
            )
            certification = certify_interval(
                interval,
                policy=policy,
                point_tolerance=point_tolerance,
            )
            if certification.value is None:
                continue
            precision = certification.value_precision
            previous_index = self._current_by_quantity.get(quantity_id)
            previous = self._records[previous_index] if previous_index is not None else None
            if (
                previous is not None
                and _PRECISION_RANK[str(previous['value_precision'])]
                >= _PRECISION_RANK[precision]
            ):
                continue
            target = catalog.loc[quantity_id]
            relation_ids, supporting_quantities = self._derivation_support(
                row, derivation_lookup
            )
            effective_basis = uniqueness_basis
            if effective_basis is None:
                derivation_id = getattr(row, 'last_derivation_id', None)
                effective_basis = (
                    'DETERMINISTIC_EQUATION_CLOSURE'
                    if derivation_id is not None and not pd.isna(derivation_id)
                    else 'INITIAL_PUBLICATION_BOUNDS'
                )
            self._promotion_sequence += 1
            fact_id = f'fact:{self._promotion_sequence:08d}'
            if previous_index is not None:
                self._records[previous_index]['is_current'] = False
            record = {
                'fact_id': fact_id,
                'supersedes_fact_id': None if previous is None else previous['fact_id'],
                'is_current': True,
                'promotion_sequence': self._promotion_sequence,
                'restoration_pass': restoration_pass,
                'quantity_id': quantity_id,
                'target_id': str(target.target_id),
                'region_code': str(target.region_code),
                'region_name': str(target.region_name),
                'federal_district_code': str(target.federal_district_code),
                'federal_district_name': str(target.federal_district_name),
                'class_code': str(target.class_code),
                'class_name': str(target.class_name),
                'section_code': str(target.section_code),
                'section_name': str(target.section_name),
                'component': str(target.component),
                'component_name': str(target.component_name),
                'value': certification.value,
                'exact_value': certification.exact_value,
                'published_value': certification.published_value,
                'value_precision': precision,
                'identification_status': certification.identification_status,
                'lower_bound': interval.lower,
                'upper_bound': interval.upper,
                'lower_attained': interval.lower_attained,
                'upper_attained': interval.upper_attained,
                'is_exact_zero': certification.is_exact_zero,
                'is_zero_at_published_precision': certification.is_zero_at_published_precision,
                'evidence_layer': evidence_layer,
                'feasibility_confirmed': True,
                'is_accepted_fact': True,
                'uniqueness_basis': effective_basis,
                'largest_horizon': largest_horizon,
                'attempt_id': attempt_id,
                'proof_ids': tuple(str(value) for value in proof_ids),
                'supporting_relation_ids': relation_ids,
                'supporting_quantity_ids': supporting_quantities,
                'derivation_id': getattr(row, 'last_derivation_id', None),
            }
            self._records.append(record)
            self._current_by_quantity[quantity_id] = len(self._records) - 1
            promoted.add(quantity_id)
            event = {
                'promotion_event_id': f'promotion:{self._promotion_sequence:08d}',
                'fact_id': fact_id,
                'quantity_id': quantity_id,
                'target_id': str(target.target_id),
                'restoration_pass': restoration_pass,
                'value': certification.value,
                'value_precision': precision,
                'uniqueness_basis': effective_basis,
                'largest_horizon': largest_horizon,
                'attempt_id': attempt_id,
                'supersedes_fact_id': None if previous is None else previous['fact_id'],
            }
            self._events.append(event)
            event_rows.append(event)
        return promoted, pd.DataFrame(event_rows)

    def facts_grid(self, *, current_only: bool = False) -> pd.DataFrame:
        grid = pd.DataFrame(self._records)
        if grid.empty:
            return grid
        if current_only:
            grid = grid[grid['is_current'].astype(bool)].copy()
        return grid.sort_values('promotion_sequence', kind='stable').reset_index(drop=True)

    def promotion_events_grid(self) -> pd.DataFrame:
        return pd.DataFrame(self._events)
