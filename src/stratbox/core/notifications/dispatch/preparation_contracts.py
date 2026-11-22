"""Requests and reports for journal-based notification preparation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from stratbox.core.observability.journal.sources import JournalCursor, JournalHead, JournalReadLimits
from stratbox.core.notifications.state.contracts import CheckpointKey

@dataclass(frozen=True, slots=True)
class PrepareRequest:
    key: CheckpointKey
    limits: JournalReadLimits = field(default_factory=JournalReadLimits)
    mode: Literal["live", "catch_up", "replay"] = "live"
    max_pages: int = 1

    def __post_init__(self) -> None:
        if (self.mode not in {"live", "catch_up", "replay"}
                or (self.mode == "replay") != (self.key.replay_id is not None)
                or type(self.max_pages) is not int or not 1 <= self.max_pages <= 50
                or (self.mode == "live" and self.max_pages != 1)):
            raise ValueError("notification.preparation_mode_invalid")


@dataclass(frozen=True, slots=True)
class InspectRequest:
    key: CheckpointKey
    after: JournalCursor | None = None
    limits: JournalReadLimits = field(default_factory=JournalReadLimits)


@dataclass(frozen=True, slots=True)
class PreparationReport:
    checkpoint: JournalCursor
    head: JournalHead
    target_offset: int
    examined: int
    matched: int
    prepared: int
    duplicate: int
    skipped: int
    reasons: tuple[tuple[str, int], ...]
    storage_coverage: str
    capture_coverage: str
    domain_coverage: str
    blocked_at: int | None = None
    reason_code: str | None = None

    @property
    def caught_up(self) -> bool:
        return self.checkpoint.last_offset == self.target_offset and self.blocked_at is None

    @property
    def no_matching_observed(self) -> bool:
        return (
            self.caught_up and self.examined > 0 and self.matched == 0
            and self.storage_coverage == self.capture_coverage == "complete"
            and self.domain_coverage in {"complete", "not_applicable"}
            and not any(code in {"notification.access_denied", "notification.projection_unavailable"}
                        for code, _ in self.reasons)
        )


@dataclass(frozen=True, slots=True)
class Inspection:
    """A read-only prediction. Its candidate checkpoint carries no commit authority."""
    subscription_revision: int
    report: PreparationReport
    candidates: tuple[bytes, ...] = field(repr=False)


