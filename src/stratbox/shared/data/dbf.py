"""Physical DBF preservation contracts, without publisher-specific rules."""
from __future__ import annotations

import codecs
from dataclasses import dataclass

from stratbox.shared.identity import ByteIdentity


def _encoding(value: str) -> str:
    try:
        return codecs.lookup(value).name
    except (LookupError, TypeError):
        raise ValueError("dbf.encoding_invalid") from None


@dataclass(frozen=True, slots=True)
class DBFHeaderEvidence:
    source_identity: ByteIdentity
    version: int
    header_date: bytes
    header_length: int
    record_length: int
    record_count: int
    language_driver: int
    encoding: str
    encoding_basis: str
    eof_marker: bool

    def __post_init__(self):
        if (not isinstance(self.source_identity, ByteIdentity)
                or type(self.version) is not int or not 0 <= self.version <= 255
                or type(self.header_date) is not bytes or len(self.header_date) != 3
                or type(self.language_driver) is not int or not 0 <= self.language_driver <= 255
                or type(self.eof_marker) is not bool
                or not isinstance(self.encoding_basis, str) or not self.encoding_basis
                or any(type(value) is not int or value < lower for value, lower in (
                    (self.header_length, 33), (self.record_length, 1), (self.record_count, 0)))):
            raise ValueError("dbf.header_evidence_invalid")
        if self.header_length + self.record_length * self.record_count + int(self.eof_marker) != self.source_identity.size:
            raise ValueError("dbf.file_geometry_invalid")
        object.__setattr__(self, "encoding", _encoding(self.encoding))


@dataclass(frozen=True, slots=True)
class DBFEncodingOverride:
    """A reviewed encoding choice for one source, issue and exact member path."""

    source_id: str
    issue_id: str
    member: str
    encoding: str
    basis: str
    asset_id: str | None = None

    def __post_init__(self):
        if any(not isinstance(value, str) or not value or len(value) > 4096
               for value in (self.source_id, self.issue_id, self.member, self.basis)):
            raise ValueError("dbf.encoding_override_scope_required")
        if self.asset_id is not None and (not isinstance(self.asset_id, str) or not self.asset_id or len(self.asset_id) > 4096):
            raise ValueError("dbf.encoding_override_scope_required")
        object.__setattr__(self, "encoding", _encoding(self.encoding))


@dataclass(frozen=True, slots=True)
class DBFPreservationPolicy:
    """Caller-selected strict lexical export; formatting never guesses types.

    Character fields lose only right space/NUL padding. N/F/D/L fields lose
    space/NUL padding at both ends. CSV uses UTF-8, comma, minimal double-quote
    quoting and LF. Binary and memo fields require separate admitted dialects.
    """

    encoding: str = "cp866"
    encoding_basis: str = "caller"
    overrides: tuple[DBFEncodingOverride, ...] = ()
    include_deleted: bool = True

    def __post_init__(self):
        object.__setattr__(self, "encoding", _encoding(self.encoding))
        object.__setattr__(self, "overrides", tuple(self.overrides))
        if (type(self.include_deleted) is not bool or not isinstance(self.encoding_basis, str)
                or not self.encoding_basis or any(not isinstance(item, DBFEncodingOverride)
                                                for item in self.overrides)):
            raise ValueError("dbf.preservation_policy_invalid")
        scopes = {}
        for item in self.overrides:
            assets = scopes.setdefault((item.source_id, item.issue_id, item.member), set())
            if item.asset_id in assets or None in assets or item.asset_id is None and assets:
                raise ValueError("dbf.encoding_override_ambiguous")
            assets.add(item.asset_id)

    def resolve(self, *, source_id=None, issue_id=None, member=None, asset_id=None) -> tuple[str, str]:
        for override in self.overrides:
            if ((source_id, issue_id, member) == (override.source_id, override.issue_id, override.member)
                    and override.asset_id in {None, asset_id}):
                return override.encoding, override.basis
        return self.encoding, self.encoding_basis


__all__ = ("DBFHeaderEvidence", "DBFEncodingOverride", "DBFPreservationPolicy")
