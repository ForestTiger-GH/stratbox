"""Deterministic bounded manifests for one immutable journal generation.

A manifest sharing the same writable root is self-consistency evidence only.
It cannot establish producer authenticity against an owner of that root.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Literal

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.core.execution.contracts import safe_token

from stratbox.core.observability.journal.contracts import JournalWriteReceipt
from stratbox.core.observability.records.contracts import require_utc
from stratbox.core.observability.assessment.coverage import CaptureCoverage, GenerationCaptureAssessment, SequenceRange, MAX_RANGES
from stratbox.core.observability.assessment.lifecycle import assess_generation_coverage
from stratbox.core.observability.records.contracts import JournalRecord

MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_MANIFEST_SEGMENTS = 10_000


def _ids_digest(ids: tuple[str, ...]) -> str:
    return sha256(canonical_manifest_bytes({"record_ids": list(ids)})).hexdigest()


@dataclass(frozen=True, slots=True)
class SegmentDescriptor:
    segment_id: str
    logical_locator: str
    identity: ByteIdentity
    record_count: int
    record_ids_digest: str
    write_state: Literal["confirmed", "failed", "unknown"]

    def __post_init__(self) -> None:
        safe_token(self.segment_id)
        if not isinstance(self.logical_locator, str) or self.logical_locator.startswith("/") or "\\" in self.logical_locator:
            raise ValueError("Invalid journal segment locator")
        if any(x in {"", ".", ".."} for x in self.logical_locator.split("/")):
            raise ValueError("Invalid journal segment path")
        if not isinstance(self.identity, ByteIdentity) or type(self.record_count) is not int or self.record_count < 0:
            raise ValueError("Invalid manifest segment content")
        if len(self.record_ids_digest) != 64 or any(c not in "0123456789abcdef" for c in self.record_ids_digest):
            raise ValueError("Invalid manifest IDs digest")
        if self.write_state not in {"confirmed", "failed", "unknown"}:
            raise ValueError("Invalid segment state")

    @classmethod
    def from_receipt(cls, receipt: JournalWriteReceipt) -> SegmentDescriptor:
        return cls(receipt.segment_id, receipt.locator, receipt.content_identity,
                   len(receipt.record_ids), _ids_digest(receipt.record_ids), receipt.state)


def _range_pairs(items: tuple[SequenceRange, ...]) -> list[list[int]]:
    return [[r.first, r.last] for r in items]


def _assessment_obj(value: GenerationCaptureAssessment) -> dict[str, object]:
    return {name: getattr(value, name) for name in (
        "scope_id", "generation_id", "status", "invocation_count", "complete_count",
        "incomplete_count", "indeterminate_count", "total_missing_events",
        "total_unknown_losses", "assessments_digest") } | {"reasons": list(value.reasons)}


def _coverage_obj(value: CaptureCoverage) -> dict[str, object]:
    return {
        "invocation_id": value.invocation_id, "scope_id": value.scope_id,
        "producer_last_sequence": value.producer_last_sequence,
        "seen_ranges": _range_pairs(value.seen_ranges),
        "policy_excluded_ranges": _range_pairs(value.policy_excluded_ranges),
        "lost_ranges": _range_pairs(value.lost_ranges),
        "unknown_loss_count": value.unknown_loss_count,
        "producer_dropped_count": value.producer_dropped_count,
        "terminal_seen": value.terminal_seen, "generation_id": value.generation_id,
        "evidence_quality": value.evidence_quality, "start_seen": value.start_seen,
    }


def _data(manifest: JournalManifest, *, include_id: bool) -> dict[str, object]:
    return {
        "schema_version": 2,
        **({"manifest_id": manifest.manifest_id} if include_id else {}),
        "writer_id": manifest.writer_id, "generation_id": manifest.generation_id,
        "scope_id": manifest.scope_id,
        "segments": [{"segment_id": s.segment_id, "logical_locator": s.logical_locator,
                      "identity": {"sha256": s.identity.sha256, "size": s.identity.size},
                      "record_count": s.record_count, "record_ids_digest": s.record_ids_digest,
                      "write_state": s.write_state} for s in manifest.segments],
        "capture_assessment": _assessment_obj(manifest.capture_assessment),
        "capture_evidence": [_coverage_obj(e) for e in manifest.capture_evidence],
        "sealed_at_utc": manifest.sealed_at_utc.isoformat(), "seal_state": manifest.seal_state,
        "origin_claim_id": manifest.origin_claim_id,
        "attestation_ref": manifest.attestation_ref,
    }


@dataclass(frozen=True, slots=True)
class JournalManifest:
    schema_version: int
    manifest_id: str
    writer_id: str
    generation_id: str
    scope_id: str
    segments: tuple[SegmentDescriptor, ...]
    capture_assessment: GenerationCaptureAssessment
    sealed_at_utc: datetime
    seal_state: Literal["sealed", "incomplete"]
    origin_claim_id: str | None = None
    attestation_ref: str | None = None
    capture_evidence: tuple[CaptureCoverage, ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != 2:
            raise ValueError("Unsupported manifest schema")
        for x in (self.manifest_id, self.writer_id, self.generation_id, self.scope_id,
                  self.origin_claim_id, self.attestation_ref):
            if x is not None:
                safe_token(x)
        require_utc(self.sealed_at_utc)
        if (self.capture_assessment.scope_id != self.scope_id or self.capture_assessment.generation_id != self.generation_id
                or any(e.scope_id != self.scope_id for e in self.capture_evidence)):
            raise ValueError("Manifest capture scope mismatch")
        if any(e.generation_id is not None and e.generation_id != self.generation_id
               for e in self.capture_evidence):
            raise ValueError("journal.generation_mismatch")
        if len(self.capture_evidence) > MAX_MANIFEST_SEGMENTS or len({e.invocation_id for e in self.capture_evidence}) != len(self.capture_evidence):
            raise ValueError("Invalid manifest capture evidence")
        if len(self.segments) > MAX_MANIFEST_SEGMENTS:
            raise ValueError("journal.manifest_segment_limit")
        if len({s.segment_id for s in self.segments}) != len(self.segments) or len({s.logical_locator for s in self.segments}) != len(self.segments):
            raise ValueError("Duplicate manifest segment")
        if self.seal_state == "sealed" and (self.capture_assessment.status != "complete" or
                not self.capture_evidence or any(e.evidence_quality != "collector_observed" or e.generation_id is None for e in self.capture_evidence) or
                any(s.write_state != "confirmed" for s in self.segments)):
            raise ValueError("Cannot seal an unconfirmed generation")
        if self.seal_state not in {"sealed", "incomplete"}:
            raise ValueError("Invalid generation seal state")
        if len(canonical_manifest_bytes(_data(self, include_id=True))) > MAX_MANIFEST_BYTES:
            raise ValueError("journal.manifest_too_large")
        expected = sha256(canonical_manifest_bytes(_data(self, include_id=False))).hexdigest()
        if self.manifest_id != expected:
            raise ValueError("Invalid manifest content identity")


def build_manifest(*, writer_id: str, generation_id: str, scope_id: str,
                   segments: tuple[SegmentDescriptor, ...],
                   records: tuple[JournalRecord, ...], sealed_at_utc: datetime,
                   origin_claim_id: str | None = None,
                   attestation_ref: str | None = None,
                   capture_evidence: tuple[CaptureCoverage, ...] = ()) -> JournalManifest:
    """Seal only the per-invocation corpus actually supplied, never a claimed summary."""
    assessment = assess_generation_coverage(records, capture_evidence, scope_id=scope_id,
                                            generation_id=generation_id)
    seal = "sealed" if assessment.status == "complete" and capture_evidence and all(
        e.evidence_quality == "collector_observed" and e.generation_id == generation_id
        for e in capture_evidence) and all(s.write_state == "confirmed" for s in segments) else "incomplete"
    provisional = object.__new__(JournalManifest)
    for name, value in {
        "schema_version": 2, "manifest_id": "placeholder", "writer_id": writer_id,
        "generation_id": generation_id, "scope_id": scope_id, "segments": segments,
        "capture_assessment": assessment, "sealed_at_utc": sealed_at_utc,
        "seal_state": seal, "origin_claim_id": origin_claim_id,
        "attestation_ref": attestation_ref, "capture_evidence": capture_evidence,
    }.items():
        object.__setattr__(provisional, name, value)
    digest = sha256(canonical_manifest_bytes(_data(provisional, include_id=False))).hexdigest()
    return JournalManifest(2, digest, writer_id, generation_id, scope_id,
                           segments, assessment, sealed_at_utc, seal, origin_claim_id,
                           attestation_ref, capture_evidence)


def encode_manifest(value: JournalManifest) -> bytes:
    return canonical_manifest_bytes(_data(value, include_id=True))


def decode_manifest(data: bytes) -> JournalManifest:
    if len(data) > MAX_MANIFEST_BYTES:
        raise ValueError("journal.manifest_too_large")
    try:
        obj = json.loads(data.decode("utf-8"))
        if not isinstance(obj, dict) or set(obj) != {
            "schema_version", "manifest_id", "writer_id", "generation_id", "scope_id",
            "segments", "capture_assessment", "sealed_at_utc", "seal_state",
            "origin_claim_id", "attestation_ref", "capture_evidence",
        }:
            raise ValueError("Invalid manifest envelope")
        s = obj["segments"]
        if not isinstance(s, list) or len(s) > MAX_MANIFEST_SEGMENTS:
            raise ValueError("Invalid manifest segment list")
        segments = tuple(SegmentDescriptor(x["segment_id"], x["logical_locator"],
                                           ByteIdentity(**x["identity"]), x["record_count"],
                                           x["record_ids_digest"], x["write_state"]) for x in s)
        if obj["schema_version"] != 2:
            raise ValueError("journal.unsupported_manifest_schema")
        c = obj["capture_assessment"]
        if not isinstance(c, dict):
            raise ValueError("Invalid manifest coverage")
        assessment = GenerationCaptureAssessment(
            c["scope_id"], c["generation_id"], c["status"], c["invocation_count"],
            c["complete_count"], c["incomplete_count"], c["indeterminate_count"],
            c["total_missing_events"], c["total_unknown_losses"],
            c["assessments_digest"], tuple(c["reasons"]))
        e = obj["capture_evidence"]
        if not isinstance(e, list) or len(e) > MAX_MANIFEST_SEGMENTS:
            raise ValueError("Invalid capture evidence list")
        def parse_coverage(value):
            def checked(name):
                parts = value[name]
                if not isinstance(parts, list) or len(parts) > MAX_RANGES:
                    raise ValueError("Invalid coverage intervals")
                return tuple(SequenceRange(*part) for part in parts)
            return CaptureCoverage(value["invocation_id"], value["scope_id"],
                                   value["producer_last_sequence"], checked("seen_ranges"),
                                   checked("policy_excluded_ranges"), checked("lost_ranges"),
                                   value["unknown_loss_count"], value["producer_dropped_count"],
                                   value["terminal_seen"], value["generation_id"],
                                   value["evidence_quality"], value["start_seen"])
        captured = tuple(parse_coverage(value) for value in e)
        return JournalManifest(obj["schema_version"], obj["manifest_id"],
                               obj["writer_id"], obj["generation_id"], obj["scope_id"],
                               segments, assessment, datetime.fromisoformat(obj["sealed_at_utc"]),
                               obj["seal_state"], obj["origin_claim_id"], obj["attestation_ref"], captured)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError, IndexError, RecursionError) as exc:
        if str(exc) == "journal.unsupported_manifest_schema":
            raise ValueError("journal.unsupported_manifest_schema") from None
        raise ValueError("journal.manifest_invalid") from None
