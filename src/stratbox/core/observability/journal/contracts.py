"""Journal scope, immutable write receipts and read-report contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from stratbox.shared.data import ByteIdentity
from stratbox.core.execution.contracts import safe_token
from stratbox.core.observability.records.contracts import JournalRecord

WriteState = Literal["confirmed", "failed", "unknown"]

@dataclass(frozen=True, slots=True)
class JournalWriteReceipt:
    state: WriteState
    segment_id: str
    content_identity: ByteIdentity
    record_ids: tuple[str, ...]
    guarantee: Literal["immutable_read_back"]
    locator: str = field(repr=False)
    diagnostic_code: str | None = None
    already_present: bool = False

    def __post_init__(self) -> None:
        if self.state not in {"confirmed", "failed", "unknown"} or self.guarantee != "immutable_read_back":
            raise ValueError("Invalid journal write receipt")
        safe_token(self.segment_id)
        for item in self.record_ids:
            safe_token(item)
        if self.diagnostic_code is not None:
            safe_token(self.diagnostic_code)
        if not isinstance(self.content_identity, ByteIdentity) or not isinstance(self.locator, str):
            raise ValueError("Invalid journal write identity")

    def confirms_batch(
        self, identity: ByteIdentity, record_ids: tuple[str, ...], *, segment_id: str | None = None,
    ) -> bool:
        return (self.state == "confirmed" and self.content_identity == identity and self.record_ids == record_ids
                and (segment_id is None or self.segment_id == segment_id))


class JournalBarrierError(Exception):
    def __init__(self, receipt: JournalWriteReceipt):
        self.receipt = receipt
        super().__init__(receipt.diagnostic_code or "journal.registration_unconfirmed")

@dataclass(frozen=True, slots=True)
class JournalNamespace:
    root: str
    writer_id: str
    format: str = "jsonl"

    def __post_init__(self):
        safe_token(self.writer_id)
        if not isinstance(self.root, str) or not self.root or "\\" in self.root or "\x00" in self.root:
            raise ValueError("Invalid logical journal root")
        if self.root.startswith("/") or ":" in self.root or any(part in {"", ".", ".."} for part in self.root.split("/")):
            raise ValueError("Journal root must be a relative, scoped logical path")
        if self.format not in {"json", "jsonl"}:
            raise ValueError("Invalid journal format")

    def segment_path(self, segment_id: str) -> str:
        safe_token(segment_id)
        return f"{self.root}/{self.writer_id}/{segment_id}.{self.format}"

    def manifest_path(self, manifest_id: str) -> str:
        safe_token(manifest_id)
        return f"{self.root}/{self.writer_id}/{manifest_id}.manifest.json"

    def admits(self, path: str) -> bool:
        if not isinstance(path, str) or "\\" in path or "\x00" in path:
            return False
        prefix = f"{self.root}/{self.writer_id}/"
        if not path.startswith(prefix):
            return False
        name = path[len(prefix):]
        if "/" in name or not name.endswith("." + self.format):
            return False
        try:
            safe_token(name[:-(len(self.format) + 1)])
        except ValueError:
            return False
        return True


@dataclass(frozen=True, slots=True)
class JournalReadIssue:
    locator: str = field(repr=False)
    code: str = "journal.unknown"
    line: int | None = None


@dataclass(frozen=True, slots=True)
class JournalReadReport:
    records: tuple[JournalRecord, ...]
    issues: tuple[JournalReadIssue, ...]
    storage_coverage: str
    capture_coverage: str
    manifest_id: str | None = None

    @property
    def complete(self) -> bool:
        return self.storage_coverage == "complete" and self.capture_coverage == "complete"
