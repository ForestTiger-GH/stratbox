# Candidate LDD — FRG plan trust, replacement bytes and destructive file effects

**Status:** `CANDIDATE / CONDITIONAL / NOT IMPLEMENTED`. **Based on observed current code:** [pinned FRG Current HOW](../../current-how/frg-cleanup-effects.md), including **five passing offline fault-injection characterization cases** in [CI 38188245744](https://github.com/ForestTiger-GH/stratbox/actions/runs/38188245744). These tests expose current behavior; none establishes this LDD's desired safeguards. **Related design:** [staged Artifact publication](../artifacts/staged-publication.md) and [execution-effect truth Science](../../science/trust-and-assurance/computation-reuse-and-external-effects.md).

## Specific trusted and untrusted boundaries

The existing Python core intentionally exposes a lower-level `apply_frg_cleanup_plan(plan_df)` which accepts a supplied plan and performs FileStore changes. The ordinary `run_frg_cleanup()` path constructs a catalog-derived plan and excludes unrecognized files from its **generated** delete rows. Those are different reliance envelopes:

- A developer calling low-level apply directly from a trusted notebook assumes responsibility for its inputs and writable FileStore scope.
- A future Strategy Box host invoking the same core on behalf of a Web/Windows/Android user must apply its **own effect authority** before reaching that lower-level primitive; ordinary mutable DataFrame rows are not an authenticated grant to delete arbitrary files.
- An AI tool, background trigger or remote client must never gain implicit authority to submit a raw `delete_source` plan just because a neutral Python API exports it. It may request a known restricted capability with an approved source/root/plan scope instead.
- A read-only `build_frg_cleanup_plan` preview must not be reported as executed cleanup; a prepared plan can also become stale before application.

Proposed *logical* effect-intent predicates (no mandatory physical schema): authenticated principal or service actor, approved workspace/file-root scope, target source member identity, expected file content/version when relevant, plan identity/revision, dry-run summary and destructive-effect authorization. The exact approval and persistence grade are Product/Operations decisions, especially when local notebook use remains independent of any application host.

## Failure windows and proposed guard semantics

| Boundary | Observed current possible outcome | Required candidate approach |
| --- | --- | --- |
| Existing target → copy replacement | Old target removed, copy fails, old bytes unavailable | Stage new bytes under different locator; verify; publish by backend-qualified swap; preserve/reconcile old until commit |
| Existing target → rename replacement | Old destination removed, rename fails | Same verified staging/rollback/unknown-state discipline; do not promise atomic rename on unsupported FileStore |
| Existing archive → new ZIP | Existing ZIP removed before writer fails | Stage and verify new archive before changing visible old version |
| Planned latest source → existing standardized target | Copy may skip, archive member prefers old target bytes | Bind archive members to **accepted chosen source or a verified matching target digest**, not path presence |
| Prepared plan → user edits/moves files | Actions target changed physical state | Recheck version, membership/scope and effect preconditions immediately before each destructive operation |
| Direct apply input from another actor | Low-level code accepts arbitrary action rows | Reject unapproved plan/paths at application capability gateway; defend against confused deputy |
| Partial execution → later delete/archive actions | Individual row exceptions logged; subsequent row continues | Explicit partial/unknown outcome; guard irreversible dependent steps on verified prerequisites; no fabricated full success |
| Parent process or worker dies mid-effect | No authoritative receipt in returned DataFrame after crash | Reconcile actual file bytes and effect intent before retry; preserve ambiguity rather than infer failure/no write |

This is a **design space**, not a requirement to wrap all direct Python-core operations in a central server. An in-memory dry run + user confirmation may suffice in a single-user local profile, but destructive multiuser hosted effects need attributable authority and durable/reconcilable evidence appropriate to their impact. Staging bytes imposes storage/IO costs; preserving every old file forever has unbounded retention cost. The minimal chosen guarantee depends on data criticality and backend capabilities.

## Future negative and acceptance vectors — all UNEXECUTED

| ID | Injection | Evidence expected under an admitted policy |
| --- | --- | --- |
| FR-01 | Existing destination and injected copy failure | Old verified destination remains available, or an explicitly weaker approved replacement policy is disclosed |
| FR-02 | Existing destination and injected rename failure | No silent loss of old version; qualified recovery/unknown evidence |
| FR-03 | Existing ZIP and archive writer fails | Previous committed ZIP preserved under chosen publication guarantee |
| FR-04 | Existing standardized target contains older bytes than latest chosen source | Archive binds to current verified source identity and cannot silently package stale target |
| FR-05 | User submits arbitrary delete row outside selected workspace | Host/app effect authority rejects it before core FileStore mutation |
| FR-06 | Plan built with recognized file, filename/path swapped before apply | Preconditions detect stale identity and require replan/approval |
| FR-07 | Source is symlink or path escapes assigned FileStore root | Filesystem/scope policy verified at point of effect; no traversal or foreign deletion |
| FR-08 | First operation fails; later dependent delete would remove last known good source | Dependent action blocked, independently safe actions may continue if explicitly allowed |
| FR-09 | Crash after actual file commit, before in-memory execution row returned | Reconcile actual bytes/receipt; neither blind retry nor false loss claim |
| FR-10 | Two authorized actors plan replacement of the same destination | Resource/version concurrency resolves one accepted generation; no silent overwrite |
| FR-11 | User denies destructive approval after seeing preview | No mutations; preview does not count as committed plan |
| FR-12 | After successful operation, live file is deleted by someone else | Historical execution remains; Artifact/file availability reflects current truth separately |

Five current-behavior tests `test_frg_cleanup_observed_faults.py` are **executed**, while **all twelve FR-01..12 target tests remain unexecuted**. A passing GitHub knowledge evidence workflow does not certify native Windows, deployed AppDock, encrypted storage, backend atomicity or actual backup recovery.

**Blocking decisions:** who may perform destructive cleanup, which roots/objects are eligible, when approval and audit are mandatory, how lost old versions are handled, retention and output storage guarantees for both host deployments, and the appropriate independent release/fault-verification scope. They remain outside the presently accepted host-existence Product Decision.
