"""Content-addressed computational methods, independent of API versions."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Mapping

from stratbox.shared.identifiers import safe_token
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes


@dataclass(frozen=True, slots=True)
class MethodDescriptor:
    """A semantic contract qualified by substantive algorithms and resources.

    The method's logical name remains stable. Its fingerprint changes when its
    declared computational meaning or any admitted algorithm dependency changes.
    Package releases, comments, paths and invocation history carry no meaning.
    """

    method_id: str
    contract: bytes
    algorithms: tuple[tuple[str, ByteIdentity], ...]
    resources: tuple[tuple[str, ByteIdentity], ...] = ()

    def __post_init__(self):
        safe_token(self.method_id)
        if not isinstance(self.contract, bytes):
            raise ValueError("method.contract_invalid")
        try:
            contract = json.loads(self.contract)
        except (ValueError, UnicodeError):
            raise ValueError("method.contract_invalid") from None
        if not isinstance(contract, dict) or canonical_manifest_bytes(contract) != self.contract:
            raise ValueError("method.contract_invalid")
        for entries in (self.algorithms, self.resources):
            if not isinstance(entries, tuple) or any(
                not isinstance(item, tuple) or len(item) != 2
                or not isinstance(item[0], str) or not item[0]
                or not isinstance(item[1], ByteIdentity) for item in entries
            ) or tuple(sorted(entries, key=lambda item: item[0])) != entries or len({name for name, _ in entries}) != len(entries):
                raise ValueError("method.dependencies_invalid")
        if not self.algorithms:
            raise ValueError("method.algorithm_required")

    @classmethod
    def build(cls, method_id: str, contract: Mapping[str, object], *,
              algorithms: Mapping[str, ByteIdentity], resources: Mapping[str, ByteIdentity] | None = None):
        return cls(method_id, canonical_manifest_bytes(contract), tuple(sorted(algorithms.items())),
                   tuple(sorted((resources or {}).items())))

    @property
    def manifest(self) -> bytes:
        def identities(entries):
            return {name: {"sha256": identity.sha256, "size": identity.size}
                    for name, identity in entries}
        return canonical_manifest_bytes({"schema": "stratbox.method", "method_id": self.method_id,
            "contract": json.loads(self.contract), "algorithms": identities(self.algorithms),
            "resources": identities(self.resources)})

    @property
    def identity(self) -> ByteIdentity:
        return ByteIdentity.of(self.manifest)
