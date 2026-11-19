"""Transient, invocation-scoped effect receipt accounting.

The resource owner supplies evidence. This accumulator only checks consistency;
it does not perform an effect, authenticate a receipt, or reconcile external state.
"""
from __future__ import annotations

from dataclasses import replace

from stratbox.core.execution.contracts import Diagnostic, EffectReceipt


class _EffectAccumulator:
    def __init__(self) -> None:
        self._items: list[EffectReceipt] = []
        self._indexes: dict[tuple[str, str], int] = {}
        self._conflicts: dict[tuple[str, str], Diagnostic] = {}

    @staticmethod
    def _consistent(previous: EffectReceipt, incoming: EffectReceipt) -> bool:
        # Stage is a changing observation label (commit -> verify), not identity.
        for field in ("reference", "identity", "guarantee", "reconciliation_owner"):
            old, new = getattr(previous, field), getattr(incoming, field)
            if old is not None and new is not None and old != new:
                return False
        return previous.state == "unknown" or previous.state == incoming.state

    def register(self, receipt: EffectReceipt) -> None:
        if receipt.effect_id is None:
            # Anonymous receipts are *independent* physical observations.
            self._items.append(receipt)
            return
        key = (receipt.kind, receipt.effect_id)
        position = self._indexes.get(key)
        if position is None:
            self._indexes[key] = len(self._items)
            self._items.append(receipt)
            return
        if key in self._conflicts:
            return  # Conflict is sticky until a separate authoritative reconciliation.
        previous = self._items[position]
        if not self._consistent(previous, receipt):
            self._items[position] = replace(previous, state="unknown")
            self._conflicts[key] = Diagnostic(
                "effect.receipt_conflict", component=receipt.kind, evidence_ref=receipt.effect_id,
                reconciliation_owner=previous.reconciliation_owner or receipt.reconciliation_owner,
                retry_disposition="reconcile",
            )
            return
        self._items[position] = replace(
            previous,
            state=receipt.state,
            stage=receipt.stage if receipt.stage is not None else previous.stage,
            reference=previous.reference if previous.reference is not None else receipt.reference,
            identity=previous.identity if previous.identity is not None else receipt.identity,
            guarantee=previous.guarantee if previous.guarantee is not None else receipt.guarantee,
            reconciliation_owner=(previous.reconciliation_owner if previous.reconciliation_owner is not None
                                  else receipt.reconciliation_owner),
        )

    def snapshot(self) -> tuple[EffectReceipt, ...]:
        return tuple(self._items)

    def integrity_diagnostics(self) -> tuple[Diagnostic, ...]:
        return tuple(self._conflicts.values())

    def conflict_keys(self) -> frozenset[tuple[str, str]]:
        return frozenset(self._conflicts)
