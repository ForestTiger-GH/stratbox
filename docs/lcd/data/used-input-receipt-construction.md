# LCD candidate — exact used-input byte receipt in the analytical core

**Grade:** LCD_CANDIDATE for one bounded Python analytical-consumer pilot; LCD_BLOCKED for global compulsory provenance capture, retained raw replay and cross-host ingestion. Prepared 2026-10-12. **No production code was changed.** This packet proposes typed Python constructions only; not an adopted API, executed test or independent verification.

**Evidence:** directly read core at stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580 (base/net/http.py, macrobanks/cbr_file_collector/contracts.py, downloader.py and operations.py); [Current HOW](../../current-how/source-download-receipts-registry-choice-and-coverage-limits.md), [used-source LDD](../../ldd/data/used-source-receipt-boundary.md), [source-vintage Science](../../science/data-and-knowledge/source-observation-vintages-and-replay.md). Analytical results belong to independent stratbox and remain callable from Python without Windows, GUI, AppDock or host runtime. No environment-specific extension internals are described.

## 1. Narrow evidence boundary

The current generic DownloadResult has transport success, status, bytes, final locator and headers, but no universal timestamp/hash. Collector downloaded objects contain original byte content, source identity and chosen filename; the public operation selects a registry, downloads and disambiguates names before saving ZIP or separate files. In that operation, downloaded and saved raw **source collection** is the result; acquisition of bytes alone does not prove that a later banking calculation *consumed* those same bytes.

Only an analytic decoder actually handed byte sequence B may author a receipt saying B was **used** by a corresponding result. The downloader can truthfully report **acquired bytes**; saving may truthfully report **stored bytes** after actual backend evidence. Both are prerequisites or neighboring evidence, not automatically result lineage. A digest answers byte equality, not source authenticity, reporting-period correctness, economic comparability or durable replay.

**Pilot boundaries:** one call site that holds original source bytes and then parses exactly those bytes; in-memory receipt and Result linkage; optional user-requested export. The first scope need not create a global Source Catalog, permanent raw data lake, installed host or transaction database. Another implementation owner may independently choose a richer profile later.

## 2. Proposed source layout — CANDIDATE_DESIGN

~~~text
Potential neutral core construction, paths to be chosen under implementation commission:
src/stratbox/base/source_evidence/
    contracts.py       acquired bytes / used-input / attempt types
    capture.py         timestamp, digest and frozen payload handoff
    validation.py      evidence qualifiers, not economic schema assertion
src/stratbox/macrobanks/<chosen_domain>/
    used_input_bridge.py    domain-specific consumed-input qualification
tests/unit/base/source_evidence/
    test_exact_bytes_and_timing.py
    test_attempt_and_coverage.py
    test_capture_failures.py
tests/unit/macrobanks/
    test_used_input_bridge.py

Avoid adding base/source_evidence until a real chosen domain consumer exists.
~~~

## 3. Typed identity and result models — CANDIDATE_DESIGN

~~~python
# source_evidence/contracts.py -- documentation-only
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Protocol
from datetime import datetime

class AcquisitionKind(str, Enum):
    RECEIVED = "received"
    FAILED = "failed"
    UNATTEMPTED = "unattempted"
    UNKNOWN = "unknown"

class ValidationKind(str, Enum):
    NOT_CHECKED = "not_checked"
    FORMAT_VALID = "format_valid"
    DOMAIN_VALID = "domain_valid"
    INVALID = "invalid"
    INDETERMINATE = "indeterminate"

@dataclass(frozen=True, slots=True)
class OriginalByteIdentity:
    sha256: str
    byte_count: int

@dataclass(frozen=True, slots=True)
class SourceAcquisition:
    source_id: str
    attempt_ref: str
    requested_url_safe: str
    observed_at_utc: datetime
    kind: AcquisitionKind
    http_status: int | None
    actual_bytes: OriginalByteIdentity | None
    safe_error_code: str | None = None
    final_url_safe: str | None = None

@dataclass(frozen=True, slots=True)
class UsedInputReceipt:
    source_id: str
    acquisition_ref: str
    byte_identity: OriginalByteIdentity
    consumed_at_utc: datetime
    domain_scope: str
    format_validation: ValidationKind
    domain_validation: ValidationKind
    registry_revision: str | None
    parser_revision: str | None

@dataclass(frozen=True, slots=True)
class DomainInputEvidence:
    used: tuple[UsedInputReceipt, ...]
    selected_source_ids: tuple[str, ...]
    attempted_source_ids: tuple[str, ...]
    unattempted_source_ids: tuple[str, ...]
    failures: tuple[SourceAcquisition, ...]

class ClockPort(Protocol):
    def now_utc(self) -> datetime: ...

class ByteDecoder(Protocol):
    def parse(self, payload: bytes) -> object: ...

class DomainInputValidator(Protocol):
    def qualify(self, parsed: object, source_id: str
                ) -> tuple[ValidationKind, str]: ...

@dataclass(frozen=True, slots=True)
class CapturedPayload:
    acquisition: SourceAcquisition
    content: bytes  # kept ONLY while the selected consumer needs the bytes
~~~

Only public-safe URL provenance should enter a shared receipt; credential-bearing locators and request headers require restricted handling. An observed clock is not necessarily authoritative publisher time; record timezone and clock uncertainty if a required claim depends on it. A content digest does not prove stored availability. Fields named source_id and domain_scope are caller-qualified and must never be asserted as publisher-approved without the required semantic validator.

## 4. Byte acquisition and consumed-byte bridge — CANDIDATE_DESIGN

~~~python
# source_evidence/capture.py -- CANDIDATE_DESIGN
from hashlib import sha256
from uuid import uuid4
from datetime import timezone

def capture_downloaded_payload(source_id: str, request_url_safe: str,
                               downloader: Callable[[], object],
                               clock: ClockPort) -> CapturedPayload | SourceAcquisition:
    attempt_ref = uuid4().hex
    try:
        result = downloader()
    except Exception:
        return SourceAcquisition(
            source_id, attempt_ref, request_url_safe,
            clock.now_utc(), AcquisitionKind.FAILED,
            None, None, "TRANSPORT_EXCEPTION")
    observed = clock.now_utc()
    if not result.ok or result.content is None:
        return SourceAcquisition(
            source_id, attempt_ref, request_url_safe, observed,
            AcquisitionKind.FAILED, result.status_code, None,
            "TRANSPORT_REJECTED", safe_url(result.final_url))
    # Existing generic HTTP success is only a TRANSPORT observation.
    payload: bytes = result.content
    identity = OriginalByteIdentity(sha256(payload).hexdigest(), len(payload))
    receipt = SourceAcquisition(
        source_id, attempt_ref, request_url_safe, observed,
        AcquisitionKind.RECEIVED, result.status_code, identity,
        None, safe_url(result.final_url))
    return CapturedPayload(receipt, payload)

# Chosen domain's used_input_bridge.py -- CANDIDATE_DESIGN
def decode_with_used_receipt(captured: CapturedPayload, decoder: ByteDecoder,
                             validator: DomainInputValidator,
                             domain_scope: str, clock: ClockPort,
                             registry_revision: str | None = None,
                             parser_revision: str | None = None
                             ) -> tuple[object, UsedInputReceipt]:
    # Do not re-fetch, recopy from disk, or hash an unrelated second read.
    same_bytes = captured.content
    parsed = decoder.parse(same_bytes)
    validation, validation_ref = validator.qualify(
        parsed, captured.acquisition.source_id)
    if validation is not ValidationKind.DOMAIN_VALID:
        raise DomainValidationIncomplete(validation_ref)
    used = UsedInputReceipt(
        source_id=captured.acquisition.source_id,
        acquisition_ref=captured.acquisition.attempt_ref,
        byte_identity=captured.acquisition.actual_bytes,
        consumed_at_utc=clock.now_utc(),
        domain_scope=domain_scope,
        format_validation=ValidationKind.FORMAT_VALID,
        domain_validation=validation,
        registry_revision=registry_revision,
        parser_revision=parser_revision)
    return parsed, used
~~~

The placeholders safe_url and DomainValidationIncomplete require real implementations *before use*. Domain-dependent format and economic validation remain with the domain; the generic helper must not elevate bare HTTP 200 or ZIP container parsing to a correct banking figure. A production implementation must validate that captured.acquisition.actual_bytes is present and bind the same immutable bytes into the parser; the type model may be refined to a separate ReceivedAcquisition variant so that a nullable digest cannot reach this function. Memory and streaming policy are deliberately open because the current DownloadResult materializes bytes. For large datasets use a constrained stream/chunk capture with immutable open-handle identity; do not change domain semantics just for a universal abstraction.

**Failure policy:** a successful acquisition followed by parser failure stays an acquisition success plus validation failure. Storage error after valid parsing cannot erase analytical evidence. A successful collector ZIP save does not imply the dataset was used by a banking computation. Form runner periods that were never reached after a fail-fast error must be classified as UNATTEMPTED, not ABSENT_FROM_SOURCE.

## 5. Source use, compatibility and safe technical choices

- **Stable source catalog:** selected source_id and catalog revision must reflect the actual chosen registry items. A filename or local mtime is insufficient evidence of latest official release.
- **Content versus method:** identical SHA-256 under different parser/registry versions can produce different interpreted results; preserve both identities.
- **Consumption boundary:** a producer must mark which selected original bytes actually fed each computation; unused downloads remain acquisition diagnostics.
- **Partial periods:** requested, attempted, received, consumed, failed and unattempted are independent counts; an empty selected registry may return an application-level no-work outcome, not a certificate of publication completeness.
- **Overwrite:** a later save may replace workspace files. A historic digest alone cannot guarantee replay if earlier raw bytes were not retained.
- **Security:** sanitize shared URL and exception fields, limit raw evidence retention by actual approved policy, and preserve permissions when publishing a receipt through a host.
- **External policy:** the generic HTTP implementation may fall back after URL preparation errors; mandatory network policy must have a separately accepted fail-closed boundary. No specific external implementation is inferred.
- **No automatic SORS evidence promotion:** a trustworthy source digest cannot strengthen weaker rounding/assumption tiers into official facts.

## 6. Concrete proposed tests — UNEXECUTED

~~~python
def test_same_url_changed_bytes_makes_two_receipts(fake_download, clock):
    a = capture_downloaded_payload("s", "safe-url", fake_download(b"A"), clock)
    b = capture_downloaded_payload("s", "safe-url", fake_download(b"B"), clock)
    assert a.acquisition.actual_bytes.sha256 != b.acquisition.actual_bytes.sha256

def test_valid_download_not_used_until_decoder_consumes(fake_download, clock):
    captured = capture_downloaded_payload("s", "safe-url", fake_download(b"X"), clock)
    assert isinstance(captured, CapturedPayload)
    assert no_domain_used_receipt_created_yet()

def test_parser_receives_identical_original_bytes(captured, spy_parser, validator, clock):
    parsed, used = decode_with_used_receipt(
        captured, spy_parser, validator, "scope", clock)
    assert spy_parser.seen_input is captured.content
    assert used.byte_identity == captured.acquisition.actual_bytes

def test_html_payload_does_not_become_domain_valid(fake_html, parser):
    with raises(DomainValidationIncomplete):
        parser.consume(fake_html)

def test_unattempted_dates_are_not_mislabeled_missing_by_publisher(fake_period_runner):
    evidence = fake_period_runner.stop_early_after_failure()
    assert evidence.unattempted_source_ids
    assert not evidence.claims_official_absence()

def test_same_digest_different_method_revision_stays_distinct(two_evaluations):
    assert two_evaluations.byte_identity == two_evaluations.repeated.byte_identity
    assert two_evaluations.parser_revision != two_evaluations.repeated.parser_revision

def test_raw_retention_loss_preserves_historic_receipt(replay_store):
    replay_store.delete_raw_keep_receipt()
    assert replay_store.receipt_exists()
    assert not replay_store.replay_available()
~~~

The test stubs above need fixtures, chosen consumer and deterministic UTC clock. They refer to actual source concerns PR-01..28 in the [LDD](../../ldd/data/used-source-receipt-boundary.md), but are not a claim that those tests exist in production. Core Python fakes can establish input-byte identity and mapping; official source authenticity, economic data validity, declared replay SLA and retained-raw fault tests require separate evidence.

## 7. Decision closure and implementer freedom

| Decision | Classification | Owner/stop |
| --- | --- | --- |
| Independent analytic core; capture exact consumed bytes rather than unrelated later stat/read | FIXED evidence boundary | Core/domain owner |
| Receipt type and per-consumer opt-in on one real pilot | LCD_CANDIDATE; BOUNDED | Core implementation owner; pilot selection needed |
| Parser revision and source selection identity | BOUNDED after a real domain consumer is picked | Domain and registry owners |
| Whether every domain must record receipts; policy on absent capture | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Product/analysis |
| Raw-byte retention, replay and storage guarantee | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Product + storage/operations |
| URL confidentiality, personal source sharing and export scope | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Security + application owner |
| Pure helper file layout and hash chunk size for bounded inputs | DELEGATED_NONMATERIAL when correctness holds | Core implementer |
| Independent reading, property/fault tests and actual data verification | NOT EXECUTED | Separate reviewer/test owner |

**Readiness:** a competent implementer can start a controlled fake source downloader/decoder receipt prototype without inferring storage architecture. A production core API patch needs consumer-specific validation and authority; full cross-domain `LCD_READY_FOR_IMPLEMENTATION` is not established. This packet does not adjust the frozen source-unit count, independently review the Science corpus or prove a deployed host.
