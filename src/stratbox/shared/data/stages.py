"""Portable values for independent material, integration and comparison stages."""
from __future__ import annotations

from dataclasses import dataclass, replace

from stratbox.shared.data.assessment import ValueEvidence
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes


@dataclass(frozen=True, slots=True)
class QualifiedMaterial:
    """One byte identity can carry independent, explicitly admitted roles."""
    material: SourcePayload
    contract: DataContract
    evidence: ValueEvidence

    def __post_init__(self):
        if (not isinstance(self.material, SourcePayload) or not isinstance(self.contract, DataContract)
                or self.contract.role is None or not isinstance(self.evidence, ValueEvidence)):
            raise ValueError("material.qualification_invalid")

    @property
    def identity(self):
        return self.material.identity


@dataclass(frozen=True, slots=True)
class MaterialMember:
    name: str
    material: SourcePayload
    lineage: tuple[UsedInputReceipt, ...] = ()


@dataclass(frozen=True, slots=True)
class IntegratedBatch:
    """Alignment metadata is retained separately from physical ingestion."""
    batch: ObservationBatch
    mapping_identity: ByteIdentity
    reference_editions: tuple[tuple[str, ByteIdentity], ...] = ()
    contract: DataContract = DataContract("observations.integrated", 1, DataRole.INTEGRATED)

    def __post_init__(self):
        if (not isinstance(self.batch, ObservationBatch) or not isinstance(self.mapping_identity, ByteIdentity)
                or not isinstance(self.reference_editions, tuple)
                or any(not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[0], str)
                    or not item[0] or not isinstance(item[1], ByteIdentity) for item in self.reference_editions)
                or len({name for name, _ in self.reference_editions}) != len(self.reference_editions)
                or not isinstance(self.contract, DataContract) or self.contract.role != DataRole.INTEGRATED):
            raise ValueError("integration.value_invalid")

    @property
    def evidence(self):
        return self.batch.evidence

    @property
    def identity(self):
        from stratbox.shared.data.observation_snapshots import observation_snapshot
        return ByteIdentity.of(canonical_manifest_bytes({"batch": observation_snapshot(self.batch).identity.sha256,
            "mapping": self.mapping_identity.sha256, "references": [(key, value.sha256) for key, value in self.reference_editions],
            "contract": (self.contract.schema_id, self.contract.version, self.contract.role.value)}))


@dataclass(frozen=True, slots=True)
class ObservationDifference:
    coordinate: str
    before: object | None
    after: object | None


@dataclass(frozen=True, slots=True)
class ObservationComparison:
    before_identity: ByteIdentity
    after_identity: ByteIdentity
    kind: str
    differences: tuple[ObservationDifference, ...]
    qualifications: tuple[str, ...] = ()
