"""Exact observation comparison with explicit semantic comparability boundaries."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext, MAX_EMAX, MIN_EMIN

from stratbox.shared.data.observations import Observation, ObservationBatch
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True, slots=True)
class ObservationChange:
    before: Observation | None
    after: Observation | None
    kind: str
    delta: Decimal | int | None
    qualification: str | None = None


@dataclass(frozen=True, slots=True)
class ObservationComparison:
    before_identity: ByteIdentity
    after_identity: ByteIdentity
    changes: tuple[ObservationChange, ...]
    comparable: int
    qualifications: tuple[str, ...]


def _key(item):
    # Matching names never bridge a changed definition, scale, period or perimeter.
    return item.subject, item.metric, item.period, tuple(sorted(item.dimensions)), item.perimeter


def exact_difference(before, after):
    """Subtract finite exact numbers independently of the ambient Decimal context."""
    if type(before) is int and type(after) is int:
        return after - before
    a, b = Decimal(before), Decimal(after)
    precision = max(a.adjusted(), b.adjusted(), 0) - min(a.as_tuple().exponent, b.as_tuple().exponent, 0) + 3
    if precision > 100_000:
        raise ValueError("calculation.exact_precision_limit")
    with localcontext() as context:
        context.prec, context.Emax, context.Emin = max(precision, 28), MAX_EMAX, MIN_EMIN
        return b - a


def compare_observations(before: ObservationBatch, after: ObservationBatch):
    identities = observation_snapshot(before).identity, observation_snapshot(after).identity
    if before.dataset_id != after.dataset_id:
        raise ValueError("calculation.dataset_mismatch")
    sides = []
    for batch in (before, after):
        indexed = {}
        for item in batch.observations:
            key = _key(item)
            if key in indexed:
                raise ValueError("calculation.ambiguous_duplicate_observation")
            indexed[key] = item
        sides.append(indexed)
    left, right = sides
    changes, comparable = [], 0
    for key in dict.fromkeys((*left, *right)):
        a, b = left.get(key), right.get(key)
        if a is None or b is None:
            changes.append(ObservationChange(a, b, "added" if a is None else "removed", None,
                "No observation with the same full semantic key exists on the other side."))
            continue
        if a.metric.quantity_kind is None or a.metric.definition_version is None or a.metric.scale is None:
            changes.append(ObservationChange(a, b, "unqualified", None,
                "Quantity kind, definition version and scale are required for arithmetic."))
            continue
        numeric = type(a.value) in {int, Decimal} and type(b.value) in {int, Decimal}
        delta = exact_difference(a.value, b.value) if numeric else None
        comparable += int(numeric)
        changes.append(ObservationChange(a, b, "unchanged" if (a.value, a.value_status) == (b.value, b.value_status)
            else "changed", delta, None if numeric else "Missing, suppressed or text values are never converted to zero."))
    return ObservationComparison(*identities, tuple(changes), comparable,
        ("Differences compare matching subjects, periods, definitions, units, scales, dimensions and perimeters.",
         "No cross-period growth, rebasing, seasonal adjustment or vintage bridging is inferred."))
