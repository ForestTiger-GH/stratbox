"""Portable archive inventory and explicit physical member dispositions."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True, slots=True)
class ArchiveMemberSelection:
    """Exact names and/or physical suffixes over one observed inventory."""

    names: tuple[str, ...] | None = None
    suffixes: tuple[str, ...] = ()
    exclude_names: tuple[str, ...] = ()
    allow_empty: bool = True

    def __post_init__(self):
        if any(isinstance(values, str) for values in (self.names, self.suffixes, self.exclude_names)):
            raise ValueError("archive.selection_invalid")
        if self.names is not None:
            object.__setattr__(self, "names", tuple(self.names))
        object.__setattr__(self, "suffixes", tuple(self.suffixes))
        object.__setattr__(self, "exclude_names", tuple(self.exclude_names))
        for values in (self.names or (), self.suffixes, self.exclude_names):
            if any(not isinstance(value, str) or not value for value in values) or len(set(values)) != len(values):
                raise ValueError("archive.selection_invalid")
        if (type(self.allow_empty) is not bool
                or any(not suffix.startswith(".") or "/" in suffix or "\\" in suffix
                       for suffix in self.suffixes)):
            raise ValueError("archive.selection_invalid")


@dataclass(frozen=True, slots=True)
class ArchiveInventoryMember:
    name: str
    size: int
    compressed_size: int | None = None
    kind: str = "file"
    encrypted: bool = False
    compression: str | None = None
    disposition: str = "available"
    identity: ByteIdentity | None = None

    def __post_init__(self):
        if (not isinstance(self.name, str) or not self.name
                or type(self.size) is not int or self.size < 0
                or self.compressed_size is not None and (type(self.compressed_size) is not int or self.compressed_size < 0)
                or self.kind not in {"file", "directory", "nonregular"}
                or type(self.encrypted) is not bool
                or self.disposition not in {"available", "selected", "excluded", "verified", "directory"}):
            raise ValueError("archive.inventory_member_invalid")
        if self.identity is not None and (not isinstance(self.identity, ByteIdentity) or self.identity.size != self.size):
            raise ValueError("archive.inventory_identity_invalid")
        if self.disposition == "verified" and self.identity is None:
            raise ValueError("archive.verified_identity_required")


@dataclass(frozen=True, slots=True)
class ArchiveInventory:
    parent_identity: ByteIdentity
    format: str
    members: tuple[ArchiveInventoryMember, ...]
    coverage: str = "complete_inventory"

    def __post_init__(self):
        object.__setattr__(self, "members", tuple(self.members))
        if (not isinstance(self.parent_identity, ByteIdentity) or self.format not in {"zip", "rar"}
                or any(not isinstance(member, ArchiveInventoryMember) for member in self.members)
                or len({member.name for member in self.members}) != len(self.members)
                or self.coverage not in {"complete_inventory", "selected_members_verified", "all_members_verified"}):
            raise ValueError("archive.inventory_invalid")


__all__ = ("ArchiveInventory", "ArchiveInventoryMember", "ArchiveMemberSelection")
