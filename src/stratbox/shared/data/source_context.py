"""Relational source coordinates and qualified uses, without runtime ownership."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True, slots=True)
class SourceCoordinate:
    source_id: str | None = None
    family_id: str | None = None
    source_group_id: str | None = None
    issue_id: str | None = None
    asset_id: str | None = None
    material_identity: ByteIdentity | None = None
    layout_identity: str | None = None
    semantic_identity: str | None = None

    def __post_init__(self):
        for name in ("source_id", "family_id", "source_group_id", "issue_id", "asset_id",
                     "layout_identity", "semantic_identity"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value or len(value) > 4096):
                raise ValueError("source.coordinate_invalid")
        if self.material_identity is not None and not isinstance(self.material_identity, ByteIdentity):
            raise ValueError("source.coordinate_invalid")
        if self.source_id is None and self.family_id is None:
            raise ValueError("source.coordinate_identity_missing")


@dataclass(frozen=True, slots=True)
class SourceUse:
    coordinate: SourceCoordinate
    input_role: str = "source"
    qualification: str = "declared"
    evidence_ref: str | None = None

    def __post_init__(self):
        if not isinstance(self.coordinate, SourceCoordinate):
            raise ValueError("source.use_invalid")
        for value in (self.input_role, self.qualification):
            if not isinstance(value, str) or not value or len(value) > 4096:
                raise ValueError("source.use_invalid")
        if self.evidence_ref is not None and (not isinstance(self.evidence_ref, str)
                or not self.evidence_ref or len(self.evidence_ref) > 8192):
            raise ValueError("source.use_invalid")


@dataclass(frozen=True, slots=True)
class ValueContext:
    """Coordinates are authoritative; set projections are discovery conveniences."""

    uses: tuple[SourceUse, ...] = ()

    def __post_init__(self):
        if not isinstance(self.uses, tuple) or any(not isinstance(use, SourceUse) for use in self.uses):
            raise ValueError("source.context_invalid")

    def _projection(self, *names):
        return tuple(sorted({getattr(use.coordinate, name) for use in self.uses for name in names
                             if getattr(use.coordinate, name) is not None}))

    @property
    def source_ids(self):
        return self._projection("source_id")

    @property
    def family_ids(self):
        return self._projection("family_id")

    @property
    def source_group_ids(self):
        return self._projection("source_group_id")

    @property
    def issue_ids(self):
        return self._projection("issue_id")

    @property
    def specification_identities(self):
        return self._projection("layout_identity", "semantic_identity")


def source_use_value(use: SourceUse) -> dict:
    if not isinstance(use, SourceUse):
        raise ValueError("source.use_invalid")
    coordinate = use.coordinate
    return {"coordinate": {
        name: (None if coordinate.material_identity is None else {
            "sha256": coordinate.material_identity.sha256, "size": coordinate.material_identity.size
        }) if name == "material_identity" else getattr(coordinate, name)
        for name in SourceCoordinate.__dataclass_fields__},
        "input_role": use.input_role, "qualification": use.qualification,
        "evidence_ref": use.evidence_ref}


def source_use_from(value: dict) -> SourceUse:
    if (not isinstance(value, dict) or set(value) != {"coordinate", "input_role", "qualification", "evidence_ref"}
            or not isinstance(value["coordinate"], dict)
            or set(value["coordinate"]) != set(SourceCoordinate.__dataclass_fields__)):
        raise ValueError("source.use_encoding_invalid")
    coordinate = dict(value["coordinate"])
    identity = coordinate["material_identity"]
    if identity is not None:
        if not isinstance(identity, dict) or set(identity) != {"sha256", "size"}:
            raise ValueError("source.use_encoding_invalid")
        coordinate["material_identity"] = ByteIdentity(identity["sha256"], identity["size"])
    return SourceUse(SourceCoordinate(**coordinate), value["input_role"],
                     value["qualification"], value["evidence_ref"])
