# Host LCD qualifier truth and proposed-test interface consistency

**Work:** same Strategy Box Knowledge Work Program, producer program-construction challenge, no product code edited. Original exact `main@39101bfc3d2017246e5de1f927bd37fc1ef9f8e2` with prior [CI 38248390557](https://github.com/ForestTiger-GH/stratbox/actions/runs/38248390557) SUCCESS.

## Diagnosed implementation-near candidate defects

1. `HostAdmission.submit` caught **every** exception raised by `CanonicalSubmissionPort.seal` and returned `AdmissionKind.REJECTED`, although unavailable schema/source/policy evidence is not a deterministic request validation failure. This conflates proven bad input and an unavailable qualification boundary. Neither case demonstrates a Run was committed; the client must not invent definitive knowledge about a prior Run with the same intention.
2. A draft conformance test `test_digest_change_under_same_key_is_rejected` changed only caller-supplied `payload_digest`. The candidate source correctly specifies host recomputation and should therefore **replay the same semantic request**, not reject it. Changing validated parameters with the same intention key is a different conflict.
3. A proposed missing-bytes fixture referenced non-existing `ArtifactAvailability.UNAVAILABLE`, and the revoked-feed test passed integer keyword `after=5` instead of declared opaque `after_cursor: str|None`. These stubs are not executed host API tests.
4. A proposed disconnect fixture coupled the independent host snapshot to a client-specific `actor` attribute not part of the formal attached-client contract; revised to pass the actual authenticated actor separately as a test fixture.

## Bounded corrections

- Added `SubmissionRejected` to documentation-only Host LCD and distinct catches: proven validation failure yields `REJECTED / REQUEST_VALIDATION_REJECTED`, generic qualifier failure yields `OUTCOME_UNKNOWN / REQUEST_QUALIFIER_UNAVAILABLE` with no Run ref.
- Literal Markdown-extracted Work-only tests compile this new class; synthetic qualifier raises typed rejection or infrastructure exception; distinguish outcomes and assert no ledger mutation.
- Synthetic host test now changes only untrusted request digest and confirms `REPLAY` with unchanged real Run; existing changed-period negative test proves `REJECTED` for changed semantics under same key.
- Proposed code-shaped test stubs now refer to existing candidate status names and signatures. The absence of a real fixture/endpoint is retained explicitly; no runnable-host acceptance claim.
- The qualifier error type is a **candidate seam**, not an accepted cross-language wire error, secure principal, storage transaction or production interface.

## Blockers and next step

All results are **producer/documentation-only**. Native Windows/Web host, server-recomputed canonicalization, actual policy outage, signed actor, durable transaction, independent cold reading, source-to-Science lossless and complete implementation handoff remain `UNEXECUTED/BLOCKED`. Census rows and all 566 independent material statuses remain unchanged. After new commit, inspect exact Actions verdict before crediting synthetic tests; when Product authority selects host profile, test the real service and reconcile source/implementation semantics before any `LCD_READY_FOR_IMPLEMENTATION` claim.
