from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.evidence import (
    STRICT_OFFICIAL_TIER,
    closure_evidence_method,
    evidence_strength,
    evidence_tier,
    inheritance_evidence_method,
)
from stratbox.macrobanks.cbr_sors_restoration.publication.rounding import (
    PublicationInterval,
    RoundingPolicy,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.certification import certify_interval


class SorsPublicationFactConflict(ValueError):
    pass


@dataclass
class SorsPublicationLedger:
    """Append-only ledger of publication-level facts and their latent meaning.

    A publication fact may be exact at the published-million level without being
    an exact latent monetary amount.  ``assumption_tier`` records the weakest
    premise required for the fact, so feedback through interval closure can never
    upgrade source-preserving/optimized selections into apparently strict facts.
    """

    _records: list[dict[str, object]] = field(default_factory=list)
    _events: list[dict[str, object]] = field(default_factory=list)
    _current_by_quantity: dict[str, int] = field(default_factory=dict)
    _sequence: int = 0
    feasibility_confirmed: bool = False

    @property
    def current_quantity_ids(self) -> set[str]:
        return set(self._current_by_quantity)

    def current_record(self, quantity_id: str) -> dict[str, object] | None:
        index = self._current_by_quantity.get(str(quantity_id))
        return None if index is None else self._records[index]

    def current_published_value(self, quantity_id: str) -> float | None:
        row = self.current_record(quantity_id)
        return None if row is None else float(row['published_value'])

    def is_publication_zero(self, quantity_id: str) -> bool:
        value = self.current_published_value(quantity_id)
        return value is not None and value == 0.0

    def _promote(
        self,
        *,
        quantity_row,
        published_value: float,
        evidence_method: str,
        latent_status: str,
        latent_value: float | None = None,
        restoration_pass: int,
        optimization_round: int | None = None,
        source_observation_ids: tuple[str, ...] = (),
        supporting_partition_ids: tuple[str, ...] = (),
        supporting_fact_ids: tuple[str, ...] = (),
        proof_ids: tuple[str, ...] = (),
        details: str | None = None,
        assumption_tier: int | None = None,
    ) -> bool:
        quantity_id = str(quantity_row.quantity_id)
        value = float(published_value)
        method_tier = evidence_tier(evidence_method)
        if assumption_tier is None:
            assumption_tier = method_tier
        assumption_tier = max(int(assumption_tier), method_tier)
        strength = evidence_strength(evidence_method)

        previous_index = self._current_by_quantity.get(quantity_id)
        previous = self._records[previous_index] if previous_index is not None else None
        if previous is not None:
            previous_value = float(previous['published_value'])
            if previous_value != value:
                raise SorsPublicationFactConflict(
                    f'Conflicting publication facts for {quantity_id}: '
                    f'{previous_value} vs {value}'
                )
            previous_tier = int(previous.get('assumption_tier', 0))
            previous_strength = int(previous.get('evidence_strength', 0))
            # Prefer genuinely stronger premises first, then the stronger method
            # inside the same premise tier.  Feedback can therefore improve an
            # inherited fact if an independent strict proof is later found, but
            # can never weaken/"wash" provenance in the opposite direction.
            if (assumption_tier, -strength) >= (previous_tier, -previous_strength):
                return False
            self._records[previous_index]['is_current'] = False

        self._sequence += 1
        fact_id = f'publication_fact:{self._sequence:08d}'
        point_allowed = (
            str(latent_status) == 'POINT'
            and assumption_tier == STRICT_OFFICIAL_TIER
            and latent_value is not None
        )
        record = {
            'fact_id': fact_id,
            'supersedes_fact_id': None if previous is None else previous['fact_id'],
            'is_current': True,
            'promotion_sequence': self._sequence,
            'restoration_pass': int(restoration_pass),
            'optimization_round': optimization_round,
            'quantity_id': quantity_id,
            'quantity_kind': str(getattr(quantity_row, 'quantity_kind', 'UNKNOWN')),
            'portfolio_scope': getattr(quantity_row, 'portfolio_scope', None),
            'region_code': getattr(quantity_row, 'region_code', None),
            'class_code': getattr(quantity_row, 'class_code', None),
            'component': getattr(quantity_row, 'component', None),
            'metric': getattr(quantity_row, 'metric', None),
            'published_value': value,
            'publication_status': 'EXACT',
            'latent_status': 'POINT' if point_allowed else 'BOUNDED',
            'latent_value': float(latent_value) if point_allowed else None,
            'evidence_method': evidence_method,
            'evidence_strength': strength,
            'assumption_tier': assumption_tier,
            'source_observation_ids': tuple(str(v) for v in source_observation_ids),
            'supporting_partition_ids': tuple(str(v) for v in supporting_partition_ids),
            'supporting_fact_ids': tuple(str(v) for v in supporting_fact_ids),
            'proof_ids': tuple(str(v) for v in proof_ids),
            'details': details,
            'feasibility_confirmed': bool(self.feasibility_confirmed),
            'is_accepted_fact': bool(self.feasibility_confirmed),
            'can_drive_publication_closure': True,
            'latent_constraint_mode': 'POINT' if point_allowed else 'PUBLICATION_BUCKET',
        }
        self._records.append(record)
        self._current_by_quantity[quantity_id] = len(self._records) - 1
        self._events.append(
            {
                'promotion_event_id': f'publication_promotion:{self._sequence:08d}',
                'fact_id': fact_id,
                'quantity_id': quantity_id,
                'published_value': value,
                'evidence_method': evidence_method,
                'assumption_tier': assumption_tier,
                'restoration_pass': int(restoration_pass),
                'optimization_round': optimization_round,
                'supersedes_fact_id': record['supersedes_fact_id'],
            }
        )
        return True

    def seed_source_facts(self, quantities_grid: pd.DataFrame) -> set[str]:
        promoted: set[str] = set()
        source = quantities_grid[
            quantities_grid['quantity_kind'].astype(str).eq('PUBLISHED_AGGREGATE')
        ]
        for row in source.itertuples(index=False):
            if getattr(row, 'published_representative_status', None) != 'STABLE':
                continue
            value = getattr(row, 'published_representative', None)
            if value is None or pd.isna(value):
                continue
            changed = self._promote(
                quantity_row=row,
                published_value=float(value),
                evidence_method='SOURCE_PUBLISHED',
                latent_status='BOUNDED',
                restoration_pass=0,
                source_observation_ids=tuple(
                    getattr(row, 'source_observation_ids', ()) or ()
                ),
                details='Stable official published representative.',
                assumption_tier=STRICT_OFFICIAL_TIER,
            )
            if changed:
                promoted.add(str(row.quantity_id))
        return promoted

    def promote_interval_facts(
        self,
        quantities_grid: pd.DataFrame,
        *,
        policy: RoundingPolicy,
        point_tolerance: float,
        restoration_pass: int,
        optimization_round: int | None = None,
        proof_ids_by_quantity: dict[str, tuple[str, ...]] | None = None,
    ) -> set[str]:
        promoted: set[str] = set()
        for row in quantities_grid.itertuples(index=False):
            if str(row.quantity_kind) == 'PUBLISHED_AGGREGATE':
                continue
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
            tier = max(
                int(getattr(row, 'lower_assumption_tier', 0) or 0),
                int(getattr(row, 'upper_assumption_tier', 0) or 0),
            )
            is_point = certification.identification_status == 'POINT_IDENTIFIED'
            method = closure_evidence_method(
                assumption_tier=tier,
                point_identified=is_point,
            )
            # A point that depends on a publication-level premise is not claimed
            # as an exact hidden monetary amount.  It remains a publication fact
            # whose feedback mode is a publication bucket.
            latent_status = 'POINT' if is_point and tier == STRICT_OFFICIAL_TIER else 'BOUNDED'
            proof_ids = ()
            if proof_ids_by_quantity:
                proof_ids = proof_ids_by_quantity.get(str(row.quantity_id), ())
            changed = self._promote(
                quantity_row=row,
                published_value=float(certification.value),
                evidence_method=method,
                latent_status=latent_status,
                latent_value=(
                    float(certification.exact_value)
                    if latent_status == 'POINT' and certification.exact_value is not None
                    else None
                ),
                restoration_pass=restoration_pass,
                optimization_round=optimization_round,
                proof_ids=proof_ids,
                details='Publication value certified from current latent bounds.',
                assumption_tier=tier,
            )
            if changed:
                promoted.add(str(row.quantity_id))
        return promoted

    def promote_inherited(
        self,
        quantity_row,
        *,
        published_value: float,
        root_fact_id: str,
        supporting_partition_ids: tuple[str, ...],
        supporting_fact_ids: tuple[str, ...],
        assumption_tier: int,
        restoration_pass: int,
        optimization_round: int | None = None,
    ) -> bool:
        tier = max(1, int(assumption_tier))
        method = inheritance_evidence_method(tier)
        return self._promote(
            quantity_row=quantity_row,
            published_value=float(published_value),
            evidence_method=method,
            latent_status='BOUNDED',
            restoration_pass=restoration_pass,
            optimization_round=optimization_round,
            supporting_partition_ids=tuple(supporting_partition_ids),
            supporting_fact_ids=tuple(
                dict.fromkeys((str(root_fact_id), *supporting_fact_ids))
            ),
            details=(
                'One published mass token was independently localized through '
                'explicit equal-value/zero publication partitions until its support '
                'became one region×class cell.'
            ),
            assumption_tier=tier,
        )

    def promote_external_bucket(
        self,
        quantity_row,
        *,
        published_value: float,
        evidence_method: str,
        restoration_pass: int,
        optimization_round: int,
        proof_ids: tuple[str, ...],
        details: str,
        assumption_tier: int | None = None,
    ) -> bool:
        if evidence_method not in {
            'ROUNDING_OPTIMUM_IDENTIFIED',
            'ROUNDING_OPTIMUM_CLOSURE',
            'ROUNDING_PREFERRED',
            'ROUNDING_PREFERRED_CLOSURE',
            'ROUNDING_SELECTED',
            'ROUNDING_SELECTED_CLOSURE',
        }:
            raise ValueError(f'Unsupported external evidence method {evidence_method!r}')
        return self._promote(
            quantity_row=quantity_row,
            published_value=float(published_value),
            evidence_method=evidence_method,
            latent_status='BOUNDED',
            restoration_pass=restoration_pass,
            optimization_round=optimization_round,
            proof_ids=proof_ids,
            details=details,
            assumption_tier=(
                evidence_tier(evidence_method)
                if assumption_tier is None
                else max(evidence_tier(evidence_method), int(assumption_tier))
            ),
        )

    def apply_current_facts_to_quantities(
        self,
        quantities_grid: pd.DataFrame,
        *,
        policy: RoundingPolicy,
        tolerance: float,
    ) -> tuple[pd.DataFrame, set[str]]:
        """Intersect current publication facts with latent bounds in one array pass.

        The multi-scope model can hold tens of thousands of current publication
        facts.  Per-cell ``DataFrame.at`` access made every publication sweep scale
        very poorly once SME/SME-IE were added.  Quantity identity is stable, so we
        map it once and update NumPy arrays while preserving exactly the same
        endpoint/tier semantics.
        """

        out = quantities_grid.copy()
        if 'lower_assumption_tier' not in out:
            out['lower_assumption_tier'] = 0
        if 'upper_assumption_tier' not in out:
            out['upper_assumption_tier'] = 0

        quantity_ids = tuple(out['quantity_id'].astype(str))
        positions = {quantity_id: index for index, quantity_id in enumerate(quantity_ids)}
        lower = out['lower_bound'].astype(float).to_numpy(copy=True)
        upper = out['upper_bound'].astype(float).to_numpy(copy=True)
        lower_attained = out['lower_attained'].astype(bool).to_numpy(copy=True)
        upper_attained = out['upper_attained'].astype(bool).to_numpy(copy=True)
        lower_tier = out['lower_assumption_tier'].fillna(0).astype(int).to_numpy(copy=True)
        upper_tier = out['upper_assumption_tier'].fillna(0).astype(int).to_numpy(copy=True)
        fact_ids = (
            out['publication_fact_id'].astype(object).to_numpy(copy=True)
            if 'publication_fact_id' in out
            else __import__('numpy').full(len(out), None, dtype=object)
        )
        evidence = (
            out['publication_evidence_method'].astype(object).to_numpy(copy=True)
            if 'publication_evidence_method' in out
            else __import__('numpy').full(len(out), None, dtype=object)
        )
        changed: set[str] = set()

        def lower_intersection(index: int, candidate: float, attained: bool, tier: int):
            old = float(lower[index])
            old_attained = bool(lower_attained[index])
            old_tier = int(lower_tier[index])
            if candidate > old + tolerance:
                return candidate, attained, tier, True
            if abs(candidate - old) <= tolerance:
                if old_attained and not attained:
                    return old, False, tier, True
                if old_attained == attained and tier < old_tier:
                    return old, old_attained, tier, True
            return old, old_attained, old_tier, False

        def upper_intersection(index: int, candidate: float, attained: bool, tier: int):
            old = float(upper[index])
            old_attained = bool(upper_attained[index])
            old_tier = int(upper_tier[index])
            if candidate < old - tolerance:
                return candidate, attained, tier, True
            if abs(candidate - old) <= tolerance:
                if old_attained and not attained:
                    return old, False, tier, True
                if old_attained == attained and tier < old_tier:
                    return old, old_attained, tier, True
            return old, old_attained, old_tier, False

        for quantity_id, record_index in self._current_by_quantity.items():
            index = positions.get(str(quantity_id))
            if index is None:
                continue
            fact = self._records[record_index]
            fact_tier = int(fact.get('assumption_tier', 0))
            if fact['latent_constraint_mode'] == 'POINT' and fact['latent_value'] is not None:
                candidate = float(fact['latent_value'])
                new_lower, new_lower_attained, new_lower_tier, lower_changed = (
                    lower_intersection(index, candidate, True, STRICT_OFFICIAL_TIER)
                )
                new_upper, new_upper_attained, new_upper_tier, upper_changed = (
                    upper_intersection(index, candidate, True, STRICT_OFFICIAL_TIER)
                )
            else:
                interval = policy.interval(float(fact['published_value']))
                new_lower, new_lower_attained, new_lower_tier, lower_changed = (
                    lower_intersection(
                        index, interval.lower, interval.lower_attained, fact_tier
                    )
                )
                new_upper, new_upper_attained, new_upper_tier, upper_changed = (
                    upper_intersection(
                        index, interval.upper, interval.upper_attained, fact_tier
                    )
                )

            if new_lower > new_upper + tolerance:
                raise SorsPublicationFactConflict(
                    f'Publication fact for {quantity_id} is incompatible with latent bounds '
                    f'[{lower[index]}, {upper[index]}] -> [{new_lower}, {new_upper}]'
                )
            endpoint_empty = (
                abs(new_lower - new_upper) <= tolerance
                and not (new_lower_attained and new_upper_attained)
            )
            if endpoint_empty:
                raise SorsPublicationFactConflict(
                    f'Publication fact for {quantity_id} creates an empty open point interval'
                )
            if lower_changed or upper_changed:
                lower[index] = new_lower
                upper[index] = new_upper
                lower_attained[index] = new_lower_attained
                upper_attained[index] = new_upper_attained
                lower_tier[index] = int(new_lower_tier)
                upper_tier[index] = int(new_upper_tier)
                fact_ids[index] = fact['fact_id']
                evidence[index] = fact['evidence_method']
                changed.add(str(quantity_id))

        out['lower_bound'] = lower
        out['upper_bound'] = upper
        out['lower_attained'] = lower_attained
        out['upper_attained'] = upper_attained
        out['lower_assumption_tier'] = lower_tier.astype(int)
        out['upper_assumption_tier'] = upper_tier.astype(int)
        out['publication_fact_id'] = fact_ids
        out['publication_evidence_method'] = evidence
        return out, changed

    def confirm_feasibility(self, confirmed: bool) -> None:
        self.feasibility_confirmed = bool(confirmed)
        for record in self._records:
            record['feasibility_confirmed'] = bool(confirmed)
            record['is_accepted_fact'] = bool(confirmed)

    def current_zero_count(self) -> int:
        """Count current publication-zero facts without materializing a DataFrame."""

        return sum(
            1
            for index in self._current_by_quantity.values()
            if float(self._records[index]['published_value']) == 0.0
        )

    def facts_grid(self, *, current_only: bool = False) -> pd.DataFrame:
        """Materialize ledger rows in promotion order.

        Records are append-only and therefore already ordered by
        ``promotion_sequence``.  Building the complete frame and sorting/filtering
        it on every publication pass became very expensive once multi-scope closure
        produced ~90k facts.  Current rows can be selected by their record indices
        directly, while the full ledger needs no sort at all.
        """

        if not self._records:
            return pd.DataFrame()
        if current_only:
            indices = sorted(self._current_by_quantity.values())
            return pd.DataFrame([self._records[index] for index in indices]).reset_index(drop=True)
        return pd.DataFrame(self._records).reset_index(drop=True)

    def promotion_events_grid(self) -> pd.DataFrame:
        return pd.DataFrame(self._events)
