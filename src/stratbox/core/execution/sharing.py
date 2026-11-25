"""Execution-time work eligibility over one compiler-supplied semantic basis.

Connection pooling and byte deduplication have separate owners. This module
assesses command work and preserves the evidence required by each consumer;
unsupported content executes independently rather than asserting equality.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass, replace
from hashlib import sha256

from stratbox.capabilities.model.reuse import (
    ConsumerEligibility, ReuseContract, WorkIdentity, build_work_identity, fingerprint,
)
from stratbox.core.execution.handoff import PreparedInput, ProjectedOutput
from stratbox.core.execution.values import argument_identity, plain
from stratbox.shared.evidence import AcquisitionReceipt
from stratbox.shared.data.source_context import SourceUse
from stratbox.shared.data.assessment import (
    CalculationEvidence, CoverageAssessment, ProcessingFinding, ValueEvidence,
)


_EVIDENCE_FIELDS = frozenset({
    "used_inputs", "input_receipts", "input_computations", "input_provenance",
    "input_transports", "input_source_contexts", "input_source_operation",
    "computation", "member_computations", "source_context", "source_uses",
    "lineage", "provenance", "effects", "qualifications", "coverage", "evidence",
    "source_id", "dataset_id", "release_id", "series_id", "family_id",
    "source_group_id", "issue_id", "asset_id", "layout_edition", "semantic_profile_edition",
})
_CONTENT_FIELDS = frozenset({"data", "rows", "cells", "tables", "observations"})


def _evidence(value, active):
    """Keep full evidence that content signatures intentionally leave separate."""
    if isinstance(value, (SourceUse, AcquisitionReceipt, ValueEvidence, CalculationEvidence,
                          CoverageAssessment, ProcessingFinding)):
        return plain(value)
    if isinstance(value, (PreparedInput, ProjectedOutput)):
        return {"type": type(value).__name__,
            "envelope": {field.name: plain(getattr(value, field.name))
                         for field in fields(value) if field.name != "value"},
            "payload_evidence": _evidence(value.value, active)}
    if isinstance(value, (str, bytes, int, float, bool, type(None))):
        return None
    identity = id(value)
    if identity in active:
        raise ValueError("reuse.cyclic_evidence")
    active.add(identity)
    try:
        if isinstance(value, Mapping):
            parts = {name: plain(item) if name in _EVIDENCE_FIELDS else _evidence(item, active)
                     for name, item in value.items()}
            return {name: item for name, item in parts.items() if item is not None} or None
        if isinstance(value, (tuple, list)):
            parts = tuple(_evidence(item, active) for item in value)
            return parts if any(item is not None for item in parts) else None
        if is_dataclass(value):
            result = {}
            for field in fields(value):
                item = getattr(value, field.name)
                if field.name in _EVIDENCE_FIELDS:
                    result[field.name] = plain(item)
                elif field.name not in _CONTENT_FIELDS:
                    nested = _evidence(item, active)
                    if nested is not None:
                        result[field.name] = nested
            return result or None
        if type(value).__module__.split(".")[0] == "pandas":
            return _evidence(getattr(value, "attrs", {}), active)
        return None
    finally:
        active.remove(identity)


def input_evidence_fingerprint(value):
    """Equal content alone never supplies another consumer's input ancestry."""
    return fingerprint(_evidence(value, set()))


def _payload(value):
    if isinstance(value, (PreparedInput, ProjectedOutput)):
        return value.value
    if isinstance(value, Mapping):
        return {name: _payload(item) for name, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_payload(item) for item in value)
    if isinstance(value, list):
        return [_payload(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class WorkAssessment:
    identity: WorkIdentity | None
    consumer: ConsumerEligibility
    contract: ReuseContract
    effects: frozenset[str]
    attempt: int = 1
    reasons: tuple[str, ...] = ()

    @property
    def inflight_allowed(self):
        return (not self.reasons and self.identity is not None
                and self.contract.inflight_eligible
                and self.consumer.eligible_for(self.identity, self.effects))

    @property
    def completed_allowed(self):
        return self.inflight_allowed and self.contract.completed_eligible

    @property
    def key(self):
        if not self.inflight_allowed:
            return None
        return sha256((self.identity.fingerprint + ":" + str(self.attempt)).encode()).hexdigest()

    def can_consume(self, producer: WorkAssessment, *, completed=False):
        """Both promises must allow the selected phase of reuse."""
        return (isinstance(producer, WorkAssessment) and self.key is not None
                and self.key == producer.key
                and (self.completed_allowed and producer.completed_allowed if completed else
                     self.inflight_allowed and producer.inflight_allowed))


def assess_work(spec, *, inputs, parameters, context, run_id, effects=None, attempt=1):
    """Resolve exact inputs/context while retaining every prepared semantic ID.

    ``inputs`` and ``parameters`` retain PreparedInput/ProjectedOutput envelopes.
    Passing only values discards the evidence needed to assess a consumer. Exact
    provenance mismatch conservatively creates independent work; it does not
    fabricate new lineage for a reused producer's scientific receipt.
    """
    contract = getattr(spec, "reuse_contract", None) or ReuseContract()
    if not isinstance(contract, ReuseContract):
        return WorkAssessment(None, ConsumerEligibility(), ReuseContract(shareable=False),
            frozenset(), attempt, ("reuse.invalid_contract",))
    actual_effects = frozenset(contract.effects if effects is None else effects)
    empty_consumer = ConsumerEligibility()
    try:
        parameter_values = _payload(parameters)
        if not isinstance(parameter_values, Mapping):
            raise ValueError("reuse.parameter_mapping_required")
    except (ValueError, TypeError, AttributeError, RecursionError):
        return WorkAssessment(None, empty_consumer, contract, actual_effects, attempt,
                              ("reuse.exact_identity_unavailable",))
    reasons = []
    if not getattr(spec, "reuse_eligible", False) or not contract.inflight_eligible:
        reasons.append("reuse.producer_sharing_disabled")
    if actual_effects - {"network.receive"} or actual_effects and not contract.observation_scoped:
        reasons.append("reuse.effect_ineligible")
    if "network.receive" in actual_effects and not parameter_values.get("allow_network", True):
        reasons.append("reuse.network_disallowed")
    if "network.receive" in actual_effects and parameter_values.get("freshness") == "fresh":
        reasons.append("reuse.independent_observation_required")
    if reasons:
        return WorkAssessment(None, empty_consumer, contract, actual_effects, attempt, tuple(reasons))
    try:
        basis = getattr(spec, "reuse_identity", None)
        if basis is None:
            # Explicit local plans may opt in without a canonical snapshot.
            basis = build_work_identity(spec.operation_id, spec.method_fingerprint or "local",
                binding_identities={"method": spec.method_fingerprint or "local"})
        providers = tuple(sorted((binding.capability.role, binding.capability.version,
            tuple(sorted(binding.capability.guarantees)), binding.provider_id, binding.scope_id or "",
            binding.readiness, id(binding.provider),
            getattr(getattr(binding.provider, "scope", getattr(binding.provider, "access_scope", None)), "identity", None))
            for binding in context.bindings))
        access = fingerprint({"providers": providers, "profile": context.profile,
            "budgets": argument_identity((context.budget, context.ceiling)).sha256})
        observation = str(parameter_values.get("observation_id") or parameter_values.get("observation") or run_id) if "network.receive" in actual_effects else ""
        freshness, epoch = str(parameter_values.get("freshness", "")), str(parameter_values.get("state_epoch", ""))
        evidence = [(name, input_evidence_fingerprint(value)) for name, value in sorted(inputs.items())]
        evidence.append(("@parameters", input_evidence_fingerprint(parameters)))
        context_evidence = {name: getattr(context, name, None) for name in _EVIDENCE_FIELDS if name.startswith("input_")}
        evidence.append(("@context", fingerprint(plain(context_evidence))))
        identity = replace(basis,
            input_identities=tuple((name, argument_identity(_payload(value)).sha256)
                                   for name, value in sorted(inputs.items())),
            parameters_fingerprint=argument_identity(parameter_values).sha256,
            input_evidence_fingerprints=tuple(evidence), access_scope=access,
            freshness=freshness, observation=observation, state_epoch=epoch)
        consumer = ConsumerEligibility(parameter_values.get("allow_network", True), access, freshness, observation, epoch)
        return WorkAssessment(identity, consumer, contract, actual_effects, attempt)
    except (ValueError, TypeError, AttributeError, RecursionError):
        return WorkAssessment(None, empty_consumer, contract, actual_effects, attempt,
                              ("reuse.exact_identity_unavailable",))
