# LCD candidate — FRG cleanup plan trust and file-effect construction

**Status:** \`LCD_CANDIDATE\` for a bounded, single-workspace local design; \`LCD_BLOCKED\` for transactional replacement, hosted destructive actions and backend-agnostic guarantees. **Prepared:** 2026-10-12. This is \`CANDIDATE_DESIGN\` within the maintained Knowledge Product, never a patch to the FRG implementation.

**Direct source:** \`stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580\`, \`src/stratbox/macrobanks/frg/cleanup.py\` blob \`a51e1a905ddc9290dc1593e6d887564714b0bce4\`. [Current HOW](../../current-how/frg-cleanup-effects.md) records five actually executed synthetic faults at [CI 38188245744](https://github.com/ForestTiger-GH/stratbox/actions/runs/38188245744). [FRG effect LDD](../../ldd/application/frg-cleanup-effect-guards.md), [Artifact publication LCD](../artifacts/local-output-publication-construction.md) and [host effect-authorization LCD](../security/host-effect-authorization-construction.md) are the adjacent design owners. Those five current-state tests are **not** implementation tests of this LCD.

## 1. Exact reason a specialized LCD is warranted

The existing \`run_frg_cleanup\` path builds a catalog-based DataFrame plan, then optionally calls \`apply_frg_cleanup_plan\`. That lower-level apply function accepts the supplied plan as trusted, iterates rows, can remove an existing target **before** a copy/rename or archive write succeeds, records row-level errors and continues. A new FileStore layer alone cannot determine whether a caller is authorized to delete a specific file or whether a selected latest source is semantically correct. A generic Artifact publisher alone cannot prove that an archive member corresponds to the accepted latest source version.

This LCD prepares a *narrow* seam: immutable normalized cleanup intentions, plan freeze/validation, source and target observations, guarded per-effect execution, verified replacement, evidence/partial states, and an independent application authority for hosted destructive use. It does not make every FRG file an immutable data lake, rewrite the statistical parser, mandate a database, or prevent a trusted notebook caller from using the existing direct Python core API.

## 2. Candidate logical location and phases

~~~text
src/stratbox/macrobanks/frg/
   cleanup.py                    # existing observed implementation, unmodified
   cleanup_plan_contracts.py     # candidate neutral typed value model
   cleanup_plan_validate.py      # candidate actual-family/source plan qualification
   cleanup_effects.py            # candidate per-file staging and receipts
application_authority/
   effect_admission.py           # host-only principal, resource, permission and approval
tests/frg/
   test_stale_plan_and_root_escape.py
   test_replace_failure_preserves_old_bytes.py
   test_archive_uses_verified_chosen_source.py
   test_partial_effect_and_ack_loss.py
~~~

Read-only planning can remain in the core. The host wraps any remotely requested write/delete operation in a trusted application effect gate; UI approval or an AI agent's suggested row is not a FileStore authorization grant.

**Proposed execution phases:** (1) select actual source family from recognized catalog; (2) freeze a normalized plan, input generation and intended effects; (3) request admission/approval under the actual application profile; (4) re-read source/target generation and authorization at effect time; (5) stage new bytes, verify source identity and resulting representation; (6) finalize with backend-specific replace/commit evidence; (7) persist or return a bounded effect receipt; (8) permit dependent archive/remove only if its prerequisites were verified. A failure after an effect may have begun becomes a partial or uncertain outcome, not an unconditional rollback.

## 3. Concrete typed plan and effect state — CANDIDATE_DESIGN

~~~python
# cleanup_plan_contracts.py -- DOCUMENTATION ONLY
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

class FileAction(str, Enum):
    COPY_LATEST = "copy_latest"
    RENAME_LATEST = "rename_latest"
    DELETE_SOURCE = "delete_source"
    CREATE_ARCHIVE = "create_archive"

class EffectTruth(str, Enum):
    NOT_STARTED = "not_started"
    VERIFIED = "verified"
    SKIPPED = "skipped"
    FAILED_NO_EFFECT = "failed_no_effect"
    PARTIAL = "partial"
    OUTCOME_UNKNOWN = "outcome_unknown"

@dataclass(frozen=True, slots=True)
class FileWitness:
    root_scope: str
    relative_path: str
    file_generation: str | None
    sha256: str | None
    observed_at_utc: str
    exists: bool

@dataclass(frozen=True, slots=True)
class FrozenAction:
    action_id: str
    action: FileAction
    source: FileWitness | None
    target: FileWitness | None
    recognized_family: str
    selected_period: str
    expected_target_digest: str | None
    destructive: bool

@dataclass(frozen=True, slots=True)
class FrozenCleanupPlan:
    plan_id: str
    revision: str
    scope_ref: str
    actions: tuple[FrozenAction, ...]
    sorted_target_set_digest: str
    selected_source_revision: str

@dataclass(frozen=True, slots=True)
class EffectReceipt:
    plan_id: str
    action_id: str
    truth: EffectTruth
    observed_target_digest: str | None
    reconciliation_ref: str | None
    safe_code: str

@dataclass(frozen=True, slots=True)
class DeleteEffectProof:
    root_scope: str
    relative_path: str
    deleted_generation: str | None
    deleted_sha256: str | None
    absence_confirmed: bool
    backend_receipt_ref: str

class PlanEvidencePort(Protocol):
    def observe(self, scope_ref: str, relative_path: str) -> FileWitness: ...
    def recognized_source(self, scope_ref: str, path: str
                          ) -> tuple[str, str] | None: ...
    def derive_plan_digest(self, actions: tuple[FrozenAction, ...],
                           scope_ref: str, revision: str,
                           selected_source_revision: str) -> str: ...

class FileEffectPort(Protocol):
    def prepare_copy_to_staging(self, source: FileWitness,
                                destination: FileWitness) -> str: ...
    def verify_staging(self, staging_ref: str,
                       expected_sha256: str) -> bool: ...
    def conditional_finalize(self, staging_ref: str, target: FileWitness,
                             intended_sha256: str) -> FileWitness: ...
    def conditional_delete(self, source: FileWitness) -> DeleteEffectProof: ...

class EffectAuthorizationPort(Protocol):
    def authorize(self, plan: FrozenCleanupPlan, action: FrozenAction,
                  approval_ref: str | None) -> str: ...

class CleanupReceiptPort(Protocol):
    def record_pending(self, plan: FrozenCleanupPlan,
                       action: FrozenAction, permit_ref: str) -> str: ...
    def record_result(self, pending_ref: str, receipt: EffectReceipt) -> None: ...
~~~

A \`FileWitness\` is a bounded observed fact, not a cryptographic resource capability. A content digest is evidence of byte identity but does not prove file ownership, recognized bank-source publication or a safe path. On storage without stable generations/conditional effects, the strong option is **BLOCKED**, not a hopeful \`os.rename\` claim.

## 4. Plan normalization and application guard — CANDIDATE_DESIGN

~~~python
# cleanup_plan_validate.py -- CANDIDATE_DESIGN
def freeze_cleanup_plan(catalog_rows: tuple[dict[str, object], ...],
                        root_scope: str,
                        evidence: PlanEvidencePort) -> FrozenCleanupPlan:
    # 1. Interpret recognized catalog policy and selected reporting period.
    # 2. Reject unknown action strings, duplicated action IDs, conflicting
    #    targets, out-of-root references and unrecognized delete subjects.
    # 3. Observe source/target bytes/generations where required.
    # 4. Sort canonical action tuples before digesting; do not hash Pandas
    #    object identity or serialize unstable DataFrame repr().
    # 5. Record source choice and prerequisites for every archive member.
    validated: list[FrozenAction] = normalize_and_validate(
        catalog_rows, root_scope, evidence)
    if not validated:
        raise ValueError("NO_ELIGIBLE_ACTIONS")
    actions = tuple(validated)
    revision = "candidate-v1"
    selected_revision = source_selection_revision(actions)
    digest = evidence.derive_plan_digest(
        actions, root_scope, revision, selected_revision)
    return FrozenCleanupPlan(
        plan_id=create_stable_plan_ref(), revision=revision,
        scope_ref=root_scope, actions=actions,
        sorted_target_set_digest=digest,
        selected_source_revision=selected_revision)

# cleanup_plan_fingerprint.py -- CANDIDATE_DESIGN, pure functions
from dataclasses import asdict
import hashlib
import json

def canonical_cleanup_digest(actions: tuple[FrozenAction, ...],
                             scope_ref: str, revision: str,
                             selected_source_revision: str) -> str:
    """Bind *content* and scope of an effect plan, not its display action IDs.

    Backend authorizer must independently bind a trusted principal, approval
    issuer, expiry and plan_id; this hash is not an approval signature.
    """
    ids = [action.action_id for action in actions]
    if not actions or not scope_ref or not revision or not selected_source_revision:
        raise ValueError("INCOMPLETE_PLAN_FINGERPRINT_INPUT")
    if len(ids) != len(set(ids)) or not all(ids):
        raise ValueError("DUPLICATE_OR_EMPTY_ACTION_ID")
    message = {
        "protocol": "frg-frozen-effects-v1",
        "scope": scope_ref,
        "revision": revision,
        "selected_source_revision": selected_source_revision,
        "actions": [asdict(action) for action in sorted(
            actions, key=lambda item: item.action_id)],
    }
    raw = json.dumps(message, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def source_witness_matches(actual: FileWitness, planned: FileWitness) -> bool:
    """Observation time is NOT a byte generation or a source identity."""
    if not actual.exists or not planned.exists:
        return False
    if (actual.root_scope != planned.root_scope
            or actual.relative_path != planned.relative_path):
        return False
    if not (planned.file_generation or planned.sha256):
        return False
    return (not planned.file_generation
            or actual.file_generation == planned.file_generation) and (
                not planned.sha256 or actual.sha256 == planned.sha256)

# cleanup_effects.py -- CANDIDATE_DESIGN
class CleanupExecutor:
    def __init__(self, effects: FileEffectPort, auth: EffectAuthorizationPort,
                 receipts: CleanupReceiptPort, evidence: PlanEvidencePort):
        self.effects, self.auth, self.receipts, self.evidence = (
            effects, auth, receipts, evidence)

    def apply_one(self, plan: FrozenCleanupPlan,
                  step: FrozenAction, approval_ref: str | None) -> EffectReceipt:
        # Do not accept an arbitrary action row merely because it has the
        # FrozenAction type. Require a unique exact member of the frozen plan.
        matches = tuple(a for a in plan.actions if a.action_id == step.action_id)
        if len(matches) != 1 or matches[0] != step:
            raise PermissionError("STEP_NOT_UNIQUE_MEMBER_OF_APPROVED_PLAN")
        if (not plan.sorted_target_set_digest
                or self.evidence.derive_plan_digest(
                    plan.actions, plan.scope_ref, plan.revision,
                    plan.selected_source_revision)
                    != plan.sorted_target_set_digest):
            raise PermissionError("PLAN_DIGEST_NOT_CURRENT")
        if (step.source is not None
                and step.source.root_scope != plan.scope_ref):
            raise PermissionError("SOURCE_OUTSIDE_PLAN_SCOPE")
        if (step.target is not None
                and step.target.root_scope != plan.scope_ref):
            raise PermissionError("TARGET_OUTSIDE_PLAN_SCOPE")
        if (step.action is FileAction.DELETE_SOURCE
                and (step.source is None
                     or not (step.source.file_generation or step.source.sha256))):
            raise PermissionError("DESTRUCTIVE_SOURCE_IDENTITY_REQUIRED")
        # Only COPY and guarded DELETE have a bounded implementation plan.
        # A rename is copy + separate approved delete; archive requires an
        # independently verified member plan and publishing port.
        if step.action not in (FileAction.COPY_LATEST, FileAction.DELETE_SOURCE):
            raise NotImplementedError("ACTION_HAS_NO_VERIFIED_EXECUTION_PLAN")
        permit = self.auth.authorize(plan, step, approval_ref)
        pending = self.receipts.record_pending(plan, step, permit)
        try:
            if step.action is FileAction.COPY_LATEST:
                assert step.source is not None and step.target is not None
                current = self.evidence.observe(
                    plan.scope_ref, step.source.relative_path)
                if not source_witness_matches(current, step.source):
                    raise StalePlanError("SOURCE_CHANGED")
                staging = self.effects.prepare_copy_to_staging(
                    step.source, step.target)
                expected = step.source.sha256
                if expected is None or not self.effects.verify_staging(staging, expected):
                    raise StalePlanError("STAGING_NOT_VERIFIED")
                final = self.effects.conditional_finalize(
                    staging, step.target, expected)
                # A returned object is not proof when it names a different
                # target or represents different bytes. After finalize starts,
                # invalid/missing proof means UNKNOWN, never FAILED_NO_EFFECT.
                if (not isinstance(final, FileWitness)
                        or not final.exists
                        or final.root_scope != step.target.root_scope
                        or final.relative_path != step.target.relative_path
                        or final.sha256 != expected
                        or not final.file_generation):
                    raise RuntimeError("FINALIZE_RECEIPT_UNVERIFIED")
                receipt = EffectReceipt(
                    plan.plan_id, step.action_id, EffectTruth.VERIFIED,
                    final.sha256, None, "REPLACEMENT_VERIFIED")
            elif step.action is FileAction.DELETE_SOURCE:
                assert step.source is not None
                # Do not delete unrecognized or changed source, or anything
                # that is still the only needed recovery copy.
                current = self.evidence.observe(
                    plan.scope_ref, step.source.relative_path)
                if not source_witness_matches(current, step.source):
                    raise StalePlanError("DELETE_SOURCE_CHANGED")
                recognized = self.evidence.recognized_source(
                    plan.scope_ref, step.source.relative_path)
                if recognized != (step.recognized_family, step.selected_period):
                    raise StalePlanError("DELETE_SOURCE_FAMILY_OR_PERIOD_CHANGED")
                # The real FileEffectPort must *also* prove compare-and-delete
                # on the same generation; a prior observe() is not a fence.
                confirmed = self.effects.conditional_delete(step.source)
                # Backend-issued absence proof must bind the exact target
                # and generation or source digest. A bare success string is
                # not a verified deletion receipt.
                if (not isinstance(confirmed, DeleteEffectProof)
                        or confirmed.root_scope != step.source.root_scope
                        or confirmed.relative_path != step.source.relative_path
                        or confirmed.deleted_generation != step.source.file_generation
                        or confirmed.deleted_sha256 != step.source.sha256
                        or confirmed.absence_confirmed is not True
                        or not confirmed.backend_receipt_ref):
                    raise RuntimeError("DELETE_RECEIPT_UNVERIFIED")
                receipt = EffectReceipt(
                    plan.plan_id, step.action_id, EffectTruth.VERIFIED,
                    None, confirmed.backend_receipt_ref, "DELETE_CONFIRMED")
            else:
                raise AssertionError("UNREACHABLE_ACTION_AFTER_ADMISSION")
        except StalePlanError:
            receipt = EffectReceipt(plan.plan_id, step.action_id,
                                    EffectTruth.FAILED_NO_EFFECT,
                                    None, None, "STALE_PLAN")
        except Exception:
            # After a pending effect, an exception alone cannot establish
            # whether the external backend committed bytes or deletion.
            receipt = EffectReceipt(plan.plan_id, step.action_id,
                                    EffectTruth.OUTCOME_UNKNOWN,
                                    None, pending, "EFFECT_UNCERTAIN")
        self.receipts.record_result(pending, receipt)
        return receipt
~~~

**Fingerprint equivalence qualification:** an earlier producer-only fake `derive_plan_digest()` hashed **action IDs alone**, even though the LCD claimed a digest over the complete frozen target set. That is an unsafe test double: changing a file path, planned source revision, selected period or scope while retaining action IDs would keep the same alleged fingerprint. The source-addressed cleanup/frozen-approval requirement demands a canonical digest of **complete action content and exact selected-scope/revision metadata**. The revised candidate supplies pure `canonical_cleanup_digest()` over all typed action/witness fields and plan scope/revision/selected-source revision (sorted actions with deterministic JSON encoding, SHA-256), and the synthetic evidence adapter must call this exact pure function. The real `PlanEvidencePort` is required to use a matching canonical serializer. This digest is **not cryptographic actor authorization** or an externally attested Plan signature: trustworthy approval must independently check principal, plan ID/revision, target digest, issuer, expiry and current grant. The candidate also adds an explicit `source_witness_matches()` that compares source scope/path, existence and the frozen generation/hash **without requiring an equal observation timestamp**. Two identical observed byte generations at different acquisition times should not spuriously appear stale; a changed byte digest or generation must fail. Real backend identity and conditional effects are still necessary.


**After-effect receipt truth correction (2026-10-12, candidate design only):** a prior `CleanupExecutor` accepted *any* FileWitness returned by `conditional_finalize` as `VERIFIED`, without checking that it described the approved target, verified source digest, live existence and a supported target generation. It likewise accepted any string from `conditional_delete` as a verified deletion. These are real gaps in the earlier **documentation-only LCD skeleton**, not demonstrated vulnerabilities in product code or released FileStore drivers. The revised candidate checks a typed `DeleteEffectProof` bound to the exact source scope/path/byte identity and an explicit absence claim; it checks a replacement result against the exact intended target and digest. Crucially, a missing/mismatched *post-effect* receipt now takes the general exception route to `OUTCOME_UNKNOWN`, **not** `FAILED_NO_EFFECT`, because the mutation could already have committed. The physical backend must still independently prove receipt authenticity, compare-and-delete under concurrency, atomic finalize and durable reconciliation; the typed fields alone cannot do that. These invariants are explicitly hypothetical until a selected backend and owner authority are admitted.

**Source-first destructive-plan correction:** the first candidate called `auth.authorize(plan, step, ...)` without first checking whether `step` was **the unique exact action in the frozen plan**, whether the plan digest was still derived from its actual ordered action set, whether source/target scopes matched the plan, or whether a requested delete had any byte/generation witness. The delete branch additionally checked only that `recognized_source()` returned *some* recognized family: it omitted a current source witness comparison and could accept another family/period occupying the same path. The code now refuses these mismatches **before creating an effect intent**, and treats changed source bytes before deletion as `FAILED_NO_EFFECT`. These are conditions **necessary** for a trustworthy host caller; `normalize_and_validate`, canonical digest computation, authenticated plan approval, backend-safe path resolution and a genuine compare-and-delete storage primitive remain independently unimplemented. A malicious Python caller with the same OS rights can still call core I/O directly, outside an application host's access policy. Never represent this LCD as deployed permission enforcement.

**Hard stops before production:** \`normalize_and_validate\`, \`create_stable_plan_ref\`, \`source_selection_revision\`, \`source_witness_matches\` and \`StalePlanError\` are deliberate design obligations, **not shipped definitions**. More importantly, \`record_result\` can fail after a confirmed physical effect; the actual implementation must preserve the pending receipt for reconciliation. Storage must guarantee a generation-checked finalize/delete or disclose a weaker, explicitly accepted local policy. A source may change after a precheck but before staging; staging must validate the bytes actually copied, and conditional finalization must be tied to the same immutable generation. An authorization check that happened before this code cannot replace an effect-time check.

**Unsupported-action semantic correction (2026-10-12, documentation-only):** the preceding candidate incorrectly marked `RENAME_LATEST` **VERIFIED** after copying bytes without deleting the old source. It also opened a pending effect for `CREATE_ARCHIVE` and then classified its own `NotImplementedError` as `OUTCOME_UNKNOWN`, despite never invoking the archive backend. Both actions now raise a bounded explicit unsupported-action diagnostic **before** authorization, pending record or effect call. These are corrections to the *design skeleton*, not evidence of product-code defects. A future application must safely project that exception without claiming a completed effect. The enum retains possible future actions as design vocabulary, not as admitted commands.

**Rename semantics:** a desired rename must not silently consume the only source copy until target commit is proven; if the source is to be removed, model it as a **separate guarded delete** with a confirmed prerequisite, not a magic atomic cross-backend move.

**Archive semantics:** construct each archive member from the *accepted selected source* or a verified target that has the same selected source digest. An old preexisting target path is **not** sufficient. Archive staging, integrity and publication use the generic Artifact LCD. The membership manifest must be frozen before a delete that could eliminate required input bytes.

## 5. Partial and unknown outcomes

A complete cleanup plan is not one Boolean. Maintain per-action \`NOT_STARTED\`, \`VERIFIED\`, \`SKIPPED\`, \`FAILED_NO_EFFECT\`, \`PARTIAL\`, \`OUTCOME_UNKNOWN\`; derive the plan outcome from required actions, outstanding prerequisites and actual effect certainty. One completed copy cannot justify archive or delete when another required action failed.

For each action, preserve a causal chain: normalized plan revision → approved principal/target set → current file generation → pending effect → physical receipt → verified final bytes or explicit unknown → actual source/data availability. The user-visible summary must never dump raw \`str(exc)\` or private absolute paths into a shared feed.

## 6. Proposed concrete negative tests — UNEXECUTED

~~~python
def test_same_action_id_cannot_hide_changed_target_or_source_selection(
        plan, canonical_cleanup_digest):
    altered = replace(plan, actions=(
        replace(plan.actions[0], target=other_file), *plan.actions[1:]))
    assert canonical_cleanup_digest(
        altered.actions, altered.scope_ref, altered.revision,
        altered.selected_source_revision) != plan.sorted_target_set_digest

def test_identical_bytes_reobserved_later_do_not_look_stale(source_witness_matches):
    observed = replace(planned_source, observed_at_utc="later-utc")
    assert source_witness_matches(observed, planned_source)
    assert not source_witness_matches(
        replace(observed, sha256="changed"), planned_source)

def test_injected_action_row_cannot_bypass_frozen_cleanup_plan(executor, plan):
    forged = replace(plan.actions[0], source=other_sensitive_source)
    with raises(PermissionError):
        executor.apply_one(plan, forged, approval_ref="approved")

def test_changed_delete_source_and_family_cannot_reach_conditional_delete(
        executor, changed_source, plan):
    with raises_or_failed_receipt("STALE_PLAN", "DELETE_SOURCE_CHANGED"):
        executor.apply_one(plan, plan.delete_step, approval_ref="approved")
    assert not changed_source.deleted

def test_existing_old_target_survives_failed_staging(effects, executor, plan):
    effects.raise_on_copy()
    result = executor.apply_one(plan, plan.replace_step, approval_ref="a")
    assert result.truth is not EffectTruth.VERIFIED
    assert effects.original_target_bytes_intact()

def test_changed_file_since_preview_rejected(executor, mutable_source, plan):
    mutable_source.replace_bytes_after_preview()
    r = executor.apply_one(plan, plan.copy_step, approval_ref="a")
    assert r.truth in (EffectTruth.FAILED_NO_EFFECT, EffectTruth.OUTCOME_UNKNOWN)

def test_reused_approval_with_new_target_set_fails(auth, plan):
    with raises(PermissionError):
        auth.authorize(plan.with_changed_actions(), plan.delete_step, "old")

def test_unrecognized_delete_row_cannot_reach_host_effect(executor, plan):
    r = executor.apply_one(plan, plan.unrecognized_delete_step, approval_ref="a")
    assert r.truth is not EffectTruth.VERIFIED

def test_archive_members_match_selected_source_digest(archive_builder, plan):
    manifest = archive_builder.prepare_members(plan)
    assert all(member.digest == plan.chosen_source_digest(member.family)
               for member in manifest)

def test_lost_finalize_ack_marks_unknown_and_preserves_pending(executor, effects, plan):
    effects.commit_then_lose_reply()
    r = executor.apply_one(plan, plan.copy_step, approval_ref="a")
    assert r.truth is EffectTruth.OUTCOME_UNKNOWN
    assert r.reconciliation_ref


def test_finalize_mismatched_or_missing_commit_receipt_is_unknown(executor, effects, plan):
    for fault in ("wrong_digest", "wrong_target", "not_present", "wrong_scope"):
        effects.final_receipt_mode = fault
        r = executor.apply_one(plan, plan.copy_step, approval_ref="a")
        assert r.truth is EffectTruth.OUTCOME_UNKNOWN
        assert r.reconciliation_ref

def test_delete_ack_binds_exact_generation_bytes_and_absence(executor, effects, plan):
    for fault in ("wrong_generation", "wrong_digest", "absence_unproved",
                  "wrong_scope", "blank_ref", "untyped_ack"):
        effects.delete_receipt_mode = fault
        r = executor.apply_one(plan, plan.delete_step, approval_ref="a")
        assert r.truth is EffectTruth.OUTCOME_UNKNOWN
        assert r.reconciliation_ref

def test_unimplemented_rename_and_archive_are_rejected_before_effect(executor, plan, effects, receipts):
    for kind in (FileAction.RENAME_LATEST, FileAction.CREATE_ARCHIVE):
        with raises(NotImplementedError):
            executor.apply_one(plan.with_action(kind), plan.action(kind), "a")
    assert not effects.calls
    assert not receipts.pending

def test_notebook_direct_core_still_imports_without_host_python_package(import_guard):
    import_guard.block_application_and_qt()
    import stratbox.macrobanks.frg.cleanup
~~~

These are **proposed future fake/native tests**. Their correct execution requires a real chosen FileStore backend, staged publication conformance, conditional resource mutations, approved host effect policy and a separate verifier. The five existing pinned synthetic tests expose the current *absence* of these safeguards; they do not pass the target contract.

**Real POSIX fault demonstration distinct from fake executor tests:** [CI 38221344760](https://github.com/ForestTiger-GH/stratbox/actions/runs/38221344760) exercised eight actual temporary-file operations on Linux and confirmed pathname-approval symlink swap, same-inode byte mutation and `os.replace()` overwriting a changed destination. A backend able only to perform `stat→remove`, `resolve→open` or `stat→replace` cannot satisfy this candidate's promised generation-fenced destructive effects merely through producer tests. A Linux create-only `os.link()` can refuse collision, but **deletion, replace-existing, multi-file archive, native Windows and remote mounts need their own chosen safe primitive**. Real source authenticity, authorized principal and durable effect reconciliation are still separate.

## 7. Decisions and implementer freedom

| Choice | Status / consumer |
| --- | --- |
| Preserve independently usable analytic core and current plan/apply identity | FIXED source and architecture boundary |
| Normalized immutable selected-source/effect plan for one local pilot | LCD_CANDIDATE; core domain + application owners |
| Actual backend atomic/conditional writes, durable pending effect and safe rollback/reconcile | LCD_BLOCKED; storage/operations owner with native fault tests |
| Host permission, destructive approval, machine delegation, lease/revocation | LCD_BLOCKED; Product/Security owner; [effect LCD](../security/host-effect-authorization-construction.md) |
| FRG family/period source policy and changed/unknown file recognition | Core domain owner; use existing recognized catalog source, do not invent publisher truth |
| Archive member manifest semantics | Candidate specialized FRG rule; actual compression backend and staging acceptance need proof |
| Choice of concrete Python module filenames and small helper functions | BOUNDED; developer after invariants satisfied |
| Exact consumer/safe migration and independent implementation handoff | NOT EXECUTED |

**Verdict:** scoped FRG cleanup is \`LCD_CANDIDATE\`; safe universal/hosted destructive operation remains \`LCD_BLOCKED\`. This model is sufficient for an implementation author to construct a fake-plan reference and find gaps, not to make real destructive source-code changes under the present documentation Commission. No Research completeness claim follows.
