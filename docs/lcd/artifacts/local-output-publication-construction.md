# LCD candidate — local output verification and Artifact publication construction

**Status:** LCD_CANDIDATE / safety-oriented local pilot; LCD_BLOCKED for any universal atomicity or hosted remote publication guarantee. All code fragments are CANDIDATE_DESIGN, not source implementation. Prepared 2026-10-12. **Science:** [identity, publication, availability](../../science/artifacts/output-identity-publication-and-availability.md). **Mechanism:** [staged publication LDD](../../ldd/artifacts/staged-publication.md), [used-source receipt LDD](../../ldd/data/used-source-receipt-boundary.md), [Target HOW](../../how/execution/execution-and-effects.md), [Current HOW](../../current-how/windows-application.md).

**Bounded consumer:** one authorized analytical operation creates one local file result under a permitted workspace and records a checkable Artifact link. Publication policy for a remote/shared host, mutable user file revisions, automatic retention, general registry and full source replay remain Product Decisions. Local file examples are deliberately narrower than a universal FileStore/SMB/cloud contract.

## 1. Current correspondence and required semantic correction

At the pinned core and Windows source revisions, independent stratbox FileStore supports file I/O and path operations but has no general atomic publication protocol. The Windows OperationResult outputs are path strings; its Scenario runner turns every returned path into a new ArtifactRecord, including technical log paths on failed steps. This is not proof that bytes are complete, valid, or accessible later. A file's current existence is also different from the historical fact that a generated version was published successfully.

**Candidate local boundary:**
1. Operation computes or exports staging bytes; domain validation remains with the domain.
2. Application output adapter controls the allowed destination path and staging lifecycle.
3. Adapter closes output, checks completed bytes, and requests format/domain validation.
4. Publisher performs a backend-supported finalization with an effect receipt; uncertainty stays explicit.
5. Application emits an Artifact publication receipt only after a confirmed final target and a recorded catalog entry; technical logs remain diagnostics.
6. At future click/open time, availability is checked separately; user deletion or editing does not retroactively erase the historical publication event.

**Definite negative scope:** no automatic whole-disk scan after user rename, no mandatory immutable copy of each working Excel workbook, no claim that a digest proves economic validity, and no assertion that every backend supports atomic rename or power-loss durability.

## 2. Bounded Python module design (no production files created)

~~~text
Potential application or core-adjacent local adapter:
  artifact_publication/
    contracts.py       typed intent, scoped locator, verification and receipts
    paths.py           confined destination resolver
    staging.py         unique staging lifecycle, cleanup and fault classification
    verifier.py        byte count / actual hash / domain predicate
    publisher.py       reconcile-aware finalize and catalog gate
    availability.py    read-time independent observation
tests/
    test_publish_interruptions.py
    test_publish_digest_conflict.py
    test_publish_permissions.py
    test_publish_availability.py
~~~

Ownership placement **not fixed:** a neutral byte writer can remain in stratbox FileStore helpers, while application-level Artifact identity, actor scope, publication permissions and Run linkage belong to application authority. Never move UI-facing Artifact state into the analytical core merely to reuse a file writer.

## 3. Concrete types and ports — CANDIDATE_DESIGN

~~~python
# artifact_publication/contracts.py -- DOCUMENTATION ONLY
from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, Callable, Protocol

class PublicationPhase(str, Enum):
    DRAFT = "draft"
    STAGING = "staging"
    STAGED_BYTES = "staged_bytes"
    VERIFIED_BYTES = "verified_bytes"
    PUBLISH_PENDING = "publish_pending"
    COMMITTED = "committed"
    ABORTED = "aborted"
    FAILED = "failed"
    OUTCOME_UNKNOWN = "outcome_unknown"
    QUARANTINED = "quarantined"

class Availability(str, Enum):
    UNCHECKED = "unchecked"
    AVAILABLE = "available"
    MISSING = "missing"
    CHANGED = "changed"
    DENIED = "denied"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class ScopedLocator:
    storage_scope: str          # e.g. authorized workspace; not absolute client path
    relative_path: str         # canonical relative path after confinement checks

@dataclass(frozen=True, slots=True)
class PublicationIntent:
    artifact_id: str
    generation: str
    run_ref: str
    step_ref: str
    actor_ref: str
    target: ScopedLocator
    expected_format: str

@dataclass(frozen=True, slots=True)
class ByteReceipt:
    byte_count: int
    sha256: str
    verified_at_utc: str
    domain_validation_ref: str | None

@dataclass(frozen=True, slots=True)
class PublicationReceipt:
    phase: PublicationPhase
    intent: PublicationIntent
    byte_receipt: ByteReceipt | None
    final_locator: ScopedLocator | None
    failure_code: str | None
    reconciliation_ref: str | None

@dataclass(frozen=True, slots=True)
class AvailabilityObservation:
    artifact_id: str
    checked_at_utc: str
    status: Availability
    current_digest: str | None = None

class ScopedWriterPort(Protocol):
    def create_unique_staging(self, intent: PublicationIntent) -> tuple[str, BinaryIO]: ...
    def read_closed_staging(self, staging_ref: str) -> BinaryIO: ...
    def finalize(self, intent: PublicationIntent, staging_ref: str,
                 verified: ByteReceipt) -> str: ...
    def inspect_final(self, intent: PublicationIntent) -> ByteReceipt | None: ...

class ArtifactCatalogPort(Protocol):
    def record_pending(self, intent: PublicationIntent,
                       verified: ByteReceipt) -> None: ...
    def record_committed(self, intent: PublicationIntent,
                         verified: ByteReceipt, final_ref: str) -> None: ...
    def read_receipt(self, artifact_id: str, generation: str
                     ) -> PublicationReceipt | None: ...

class AuthorizationPort(Protocol):
    def may_write(self, actor_ref: str, locator: ScopedLocator) -> bool: ...
    def may_read(self, actor_ref: str, locator: ScopedLocator) -> bool: ...

class DomainFileValidator(Protocol):
    def validate(self, file_stream: BinaryIO, expected_format: str
                 ) -> str | None: ...  # accepted validation ref or None
~~~

These are application-facing types; the neutral writer may be implemented using an admitted local FileStore capability. A path-like staging_ref is a restricted internal handle, not an externally shareable URL. A format validator does not have blanket authority to declare banking data economically accurate.

## 4. Algorithm and error boundary — CANDIDATE_DESIGN

~~~python
# artifact_publication/publisher.py -- CANDIDATE_DESIGN
import hashlib

class LocalOutputPublisher:
    def __init__(self, writer: ScopedWriterPort, catalog: ArtifactCatalogPort,
                 auth: AuthorizationPort, domain: DomainFileValidator):
        self.writer, self.catalog, self.auth, self.domain = (
            writer, catalog, auth, domain)

    def publish(self, intent: PublicationIntent,
                produce: Callable[[BinaryIO], None]) -> PublicationReceipt:
        if not self.auth.may_write(intent.actor_ref, intent.target):
            return PublicationReceipt(PublicationPhase.FAILED, intent, None,
                                      None, "WRITE_DENIED", None)
        # Validate confinement of storage_scope + relative_path independently:
        # no '..', absolute injection, symlink/junction traversal or racing open.
        staging_ref, stream = self.writer.create_unique_staging(intent)
        completed = False
        try:
            try:
                produce(stream)              # may raise after partial bytes
                stream.flush()               # storage-specific sync tier is open
                completed = True
            finally:
                stream.close()               # must not COMMIT the final target
            if not completed:
                raise RuntimeError("INCOMPLETE_STAGING")
            # Hash the very bytes subsequently validated/finalized, after
            # closing writer. Detect replacement/races by storage generation
            # or a verified re-read before commit, not stat-before-read only.
            with self.writer.read_closed_staging(staging_ref) as src:
                digest = hashlib.sha256()
                count = 0
                for chunk in iter(lambda: src.read(1024 * 1024), b""):
                    count += len(chunk)
                    digest.update(chunk)
            with self.writer.read_closed_staging(staging_ref) as src:
                domain_ref = self.domain.validate(src, intent.expected_format)
            if domain_ref is None:
                return PublicationReceipt(PublicationPhase.QUARANTINED,
                                          intent, None, None,
                                          "VALIDATION_FAILED", staging_ref)
            receipt = ByteReceipt(count, digest.hexdigest(),
                                  "UTC_CLOCK_FROM_INJECTED_SOURCE", domain_ref)
            self.catalog.record_pending(intent, receipt)
            # Recheck authorization immediately before external finalization.
            if not self.auth.may_write(intent.actor_ref, intent.target):
                return PublicationReceipt(PublicationPhase.FAILED, intent,
                                          receipt, None, "PERMISSION_CHANGED",
                                          staging_ref)
            try:
                final_ref = self.writer.finalize(intent, staging_ref, receipt)
            except Exception:
                # The external finalize MAY already have happened.
                return PublicationReceipt(PublicationPhase.OUTCOME_UNKNOWN,
                                          intent, receipt, None,
                                          "FINALIZE_AMBIGUOUS", staging_ref)
            observed = self.writer.inspect_final(intent)
            if observed is None or observed.sha256 != receipt.sha256:
                return PublicationReceipt(PublicationPhase.OUTCOME_UNKNOWN,
                                          intent, receipt, None,
                                          "FINAL_VERIFICATION_MISSING",
                                          staging_ref)
            self.catalog.record_committed(intent, receipt, final_ref)
            return PublicationReceipt(PublicationPhase.COMMITTED,
                                      intent, receipt, intent.target, None, None)
        except Exception:
            # Preserve restricted technical trace elsewhere. A failure AFTER
            # unknown side effects requires reconciliation, not blind delete.
            return PublicationReceipt(PublicationPhase.FAILED, intent, None,
                                      None, "STAGING_OR_METADATA_FAILED",
                                      staging_ref)
~~~

**Important deliberate incompleteness:** this skeleton still has a possible ambiguous window between physical finalization and catalog commit. The actual accepted backend must prove a durable publish intent, stable generation/reconciliation, permissions at final open, and its particular atomic visibility/durability tier. Hashing and validating in two reads introduces a TOCTOU risk unless the staging object is sealed or immutable by generation; a production plan must tie both reads and finalization to the *same byte generation*. The injected UTC clock and verification must supply actual observations, not the literal placeholder shown. Callback, writer cleanup, quarantine retention and catalog conflict handling also require tested concrete implementations. This is a construction *prompt to eliminate ambiguity*, not deployable code.

**Backend-specific stop condition:** if rename/finalize lacks a trustworthy commit-barrier, do not return COMMITTED based on a successful method call alone. Publish a weaker explicit outcome tier, reject the requested guarantee or select a proven backend. Cleanup cannot destroy the only recoverable staging bytes while effect outcome remains unknown.

## 5. Operation/Scenario integration and external evidence

The application operation adapter classifies:
- domain result/evidence returned by the independent analytic operation;
- ordinary output candidate paths;
- technical logs and restricted diagnostics;
- receipts with actual verified publication status;
- possible downstream availability checks.

A failed operation may have earlier successfully published an Artifact; a successful computation may have a failed exporter. The aggregate Scenario result therefore must not infer Artifact readiness from step success or file extension. The corresponding [local Scenario LCD](../application/local-scenario-execution-construction.md) consumes typed output evidence rather than relabeling a log path.

Used-source byte receipts, where Product Authority admits their capture, belong at the **actual consumed-byte** boundary inside the analytical core. A digest identifies observed bytes, not authenticity or economic correctness. This publication design links only actual used-input/method IDs known to the result, not every discovered or downloaded URL. No universal Source Catalog is implied.

## 6. Proposed conformance stubs — UNEXECUTED

~~~python
def test_producer_failure_leaves_no_published_artifact(fake_writer, publisher, intent):
    result = publisher.publish(intent, produce=lambda stream: raise_after_partial_write(stream))
    assert result.phase is not PublicationPhase.COMMITTED

def test_same_generation_different_digest_rejected(fake_catalog, intent):
    fake_catalog.record_pending(intent, byte_receipt_A)
    with raises(GenerationConflict):
        fake_catalog.record_pending(intent, byte_receipt_B)

def test_lost_finalize_ack_requires_reconciliation(inject_lost_ack, publisher, intent):
    result = publisher.publish(intent, produce=write_valid_xlsx)
    assert result.phase is PublicationPhase.OUTCOME_UNKNOWN

def test_permission_revoked_between_verify_and_finalize(revoke_after_verify, publisher, intent):
    result = publisher.publish(intent, produce=write_valid_xlsx)
    assert result.phase is not PublicationPhase.COMMITTED

def test_external_user_delete_does_not_erase_old_publication_receipt(catalog, availability, artifact_id):
    assert catalog.get(artifact_id).publication_phase is PublicationPhase.COMMITTED
    assert availability.check(artifact_id).status is Availability.MISSING

def test_validation_and_digest_bind_to_same_staging_generation(fake_storage):
    assert fake_storage.rejects_staging_mutation_between_read_and_finalize()
~~~

These fixtures are *not implemented*. Link the actual target suite to [staged publication LDD](../../ldd/artifacts/staged-publication.md), [input provenance LDD](../../ldd/data/used-source-receipt-boundary.md), and host HC artifact/security vectors where applicable. Static Python parse checks alone validate no storage semantics. Native filesystem fault injection and independent implementation review are required before an implementation-ready declaration.

## 7. Decision register / implementation sufficiency

| Material choice | Status | Owner |
| --- | --- | --- |
| No Artifact COMMITTED solely from output path or log | FIXED evidence invariant | Target Science/HOW; implementation signoff pending |
| Actual byte identity and domain validator boundary | BOUNDED for local pilot | Core owner + domain specialist |
| Finalization, visibility, fsync, crash durability and backend capabilities | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Storage/operations + chosen backend tests |
| Scoped locator, path confinement, symlink/junction and race policy | BLOCKED pending actual storage boundary | Security + application owner |
| Physical file layout of local staging helpers | DELEGATED_NONMATERIAL once guarantees proven | Implementer |
| Catalog transaction, generation conflict, recovery and retention | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Product + storage owner |
| Raw source retention and replay promise | BLOCKED/NOT_APPLICABLE to basic output pilot without capture | Product + analytic source owner |
| Remote-host fetch, multiuser ACL and content streaming | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Host/security/operations |
| Verification against real Excel/ZIP and interrupted writes | PROPOSED / UNEXECUTED | Independent test owner |

**Cold handoff:** an implementer can construct fake writer, catalog, validator and fault suite from these interfaces; cannot yet promise atomic publish or write the production finalizer without owner choices and storage evidence. Local narrow scope: LCD_CANDIDATE. Universal publication capability: LCD_BLOCKED. The independent Research Amputation and source-completeness status remain unchanged.
