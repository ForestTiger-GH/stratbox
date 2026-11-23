"""Pure source-content groups, instance claims and actual material resolutions."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Protocol

from stratbox.shared.data.processing import DataContract
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.identifiers import safe_token


def _tokens(values):
    if not isinstance(values, tuple) or any(not isinstance(value, str) for value in values) or len(set(values)) != len(values):
        raise ValueError("source.invalid_tokens")
    for value in values:
        safe_token(value)


@dataclass(frozen=True, slots=True)
class SourceGroup:
    """One addressable dataset in a source; independent of processing groups."""

    group_id: str
    title: str
    contracts: tuple[DataContract, ...]
    profile_ids: tuple[str, ...] = ()
    formats: tuple[str, ...] = ()
    grain: tuple[str, ...] = ()
    period_model: str = "publisher_defined"
    source_table_code: str | None = None
    qualification: str = "conditional"
    layout_editions: tuple[str, ...] = ()
    semantic_profile_editions: tuple[str, ...] = ()

    def __post_init__(self):
        safe_token(self.group_id)
        safe_token(self.period_model)
        if not isinstance(self.title, str) or not self.title.strip() or self.qualification not in {"supported", "conditional", "source_only"}:
            raise ValueError("registry.source_group_invalid")
        if not isinstance(self.contracts, tuple) or not self.contracts or any(not isinstance(item, DataContract) for item in self.contracts) or len(set(self.contracts)) != len(self.contracts):
            raise ValueError("registry.source_group_contracts_invalid")
        for values in (self.profile_ids, self.formats, self.grain, self.layout_editions, self.semantic_profile_editions):
            _tokens(values)
        if self.source_table_code is not None:
            safe_token(self.source_table_code)


@dataclass(frozen=True, slots=True)
class SourceInstance:
    """Caller-supplied coordinates; an identity alone proves no availability.

    material_identity addresses concrete material bytes requested from a resolver.
    consumed_identity identifies the exact in-memory value being consumed.
    source_material_identity retains original provenance without claiming that
    those original bytes must be reacquired for a materialized typed input.
    """

    source_id: str
    contract: DataContract
    group_id: str | None = None
    report_date: str | None = None
    publication_step: float | None = None
    perimeter: str | None = None
    issue_id: str | None = None
    material_identity: ByteIdentity | None = None
    revision: str | None = None
    profile_id: str | None = None
    layout_edition: str | None = None
    semantic_profile_edition: str | None = None
    grain: tuple[str, ...] = ()
    format: str | None = None
    asset_id: str | None = None
    reference_editions: tuple[tuple[str, str], ...] = ()
    consumed_identity: ByteIdentity | None = None
    source_material_identity: ByteIdentity | None = None

    def __post_init__(self):
        safe_token(self.source_id)
        if not isinstance(self.contract, DataContract):
            raise ValueError("registry.source_instance_invalid")
        for token in (self.group_id, self.perimeter, self.issue_id, self.revision, self.profile_id,
                      self.layout_edition, self.semantic_profile_edition, self.format, self.asset_id):
            if token is not None:
                safe_token(token)
        if self.report_date is not None:
            try:
                date.fromisoformat(self.report_date)
            except (TypeError, ValueError):
                raise ValueError("registry.source_instance_date_invalid") from None
        if self.publication_step is not None and (isinstance(self.publication_step, bool)
                or not isinstance(self.publication_step, (int, float)) or not isfinite(self.publication_step) or self.publication_step <= 0):
            raise ValueError("registry.source_instance_step_invalid")
        if any(value is not None and not isinstance(value, ByteIdentity) for value in (self.material_identity, self.consumed_identity, self.source_material_identity)):
            raise ValueError("registry.source_instance_identity_invalid")
        _tokens(self.grain)
        if not isinstance(self.reference_editions, tuple) or any(not isinstance(pair, tuple) or len(pair) != 2 for pair in self.reference_editions):
            raise ValueError("registry.source_reference_editions_invalid")
        for pair in self.reference_editions:
            for token in pair:
                safe_token(token)


@dataclass(frozen=True, slots=True)
class ResolvedSourceInstance:
    """Actual value/material supplied by a host resolver, without admission flags.

    Core recomputes material identity and runs trusted admission callbacks. This
    record cannot assert that bytes or economic interpretation were verified.
    """

    instance: SourceInstance
    value: object
    material: SourcePayload | None = None
    receipt: UsedInputReceipt | None = None

    def __post_init__(self):
        if not isinstance(self.instance, SourceInstance) or self.value is None:
            raise ValueError("source.resolution_invalid")
        if self.material is not None and not isinstance(self.material, SourcePayload):
            raise ValueError("source.resolution_material_invalid")
        if self.receipt is not None and not isinstance(self.receipt, UsedInputReceipt):
            raise ValueError("source.resolution_receipt_invalid")


@dataclass(frozen=True, slots=True)
class MaterialAdmission:
    """Observed material check; generated by core after reading actual bytes."""

    state: str
    expected_identity: ByteIdentity | None = None
    actual_identity: ByteIdentity | None = None
    reasons: tuple[str, ...] = ()

    def __post_init__(self):
        if self.state not in {"verified", "mismatch", "unverified", "inaccessible", "not_required"}:
            raise ValueError("source.material_admission_invalid")
        if self.state == "verified" and (self.actual_identity is None or self.expected_identity is not None and self.actual_identity != self.expected_identity):
            raise ValueError("source.material_admission_invalid")


@dataclass(frozen=True, slots=True)
class DomainAdmission:
    state: str
    reasons: tuple[str, ...] = ()

    def __post_init__(self):
        if (self.state not in {"admitted", "conditional", "rejected", "unassessed", "not_required"}
                or not isinstance(self.reasons, tuple) or any(not isinstance(reason, str) or not reason for reason in self.reasons)):
            raise ValueError("source.domain_admission_invalid")


class SourceResolver(Protocol):
    """Host-owned access; implementations provide the actual selected material."""

    def resolve(self, instance: SourceInstance) -> ResolvedSourceInstance: ...
