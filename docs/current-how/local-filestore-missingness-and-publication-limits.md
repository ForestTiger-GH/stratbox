# Local storage and publication guarantees

`LocalFileStore(root)` confines explicit paths to its configured root. Create-only writes establish immutable objects, while compare-and-set writes require the expected current content token. The effect coordinator admits direct results, retry lookups and explicit reconciliation through one typed evidence boundary.

A missing disk input is a missing input; acquisition occurs only in an explicitly prepared acquisition route. Immutable member references are verified before a release manifest is published. Compare-and-set of a pointer alone cannot preserve mutable member bytes.

## 1. Evidence identifies the exact intended occurrence

Every supplied `effect_id`/`intent_id` and `effect_kind`/`kind` alias must agree with the durable intended occurrence. Provider scope, intent, returned payload and supplied preconditions must also agree. A matching primary alias cannot conceal a conflicting secondary alias. Notification acknowledgements retain their actual acceptance level; a provider accepting a message establishes that acknowledgement, while recipient delivery requires delivery evidence.

Typed evidence and receipt wrappers preserve that same rule: every supplied wrapper outcome and nested payload status or confirmation must agree. A positive wrapper cannot promote an unknown or rejected payload. Publication and dataset intents also seal the provider identity; an explicit returned provider identity must match it.

Immutable content references bind exact bytes, provider scope and storage location. Named-copy evidence verifies the required current bytes. Conditional replacements, moves and deletions require evidence of the conditional transition; observing matching destination bytes or an absent source alone leaves an uncertain transition unresolved. Local transition records are written after the physical transition. A process can fail between these writes, so the two writes do not form one atomic transaction.

`FileEffectState` claims an occurrence before handing it to the provider. Receipt revisions and claim tokens reject stale local settlements and changed intent. Unknown effects retain their identity and cannot be automatically reclaimed for another attempt. A claim token fences the local receipt ledger; physical provider fencing requires a provider that implements that capability.

## 2. Historical confirmation and current availability have separate lifetimes

`command.artifact.reconcile` observes current evidence and returns an assessment. It performs no repair. A historical confirmed receipt remains confirmed after its destination disappears, while the current availability assessment becomes indeterminate. Reusing a confirmed retention through `command.artifact.commit` also verifies current bytes before returning the reference.

To repair missing immutable content, supply independently available exact bytes to `command.artifact.commit` with a stable, explicit `repair_id`:

```python
repaired = box.invoke(
    "command.artifact.commit",
    inputs={"material": exact_material, "destination": "objects"},
    parameters={"repair_id": "restore-2026-11-27-001"},
)
```

The original retention must already have a confirmed receipt. The repair receives a new effect identity and preserves the original receipt. Reusing the same repair ID observes that repair occurrence. Named destinations use `command.artifact.materialize` with a new `delivery_id` and a readable source or surviving retained ancestor. `create_only` protects an intervening different destination from replacement.

Mutable release pointers use an optional explicit `publication_id` for a new publication occurrence. This permits a later A-to-B transition after the pointer returns to A while preserving the earlier A-to-B receipt. Each new occurrence still requires the actual expected current token. Reusing an earlier occurrence verifies current availability and does not silently republish an old transition.

Both HTTP response bodies and qualified retained 304 representations pass through the same destination fulfillment. Reusing an original in directory A while requesting directory B verifies and retains the bytes in B, with B's own storage receipt.

## 3. Local ownership survives process death

Directory guards hold an operating-system lock over a stable anchor file. Release closes the held lock and preserves the anchor; process death also releases ownership. A busy guard fails promptly. Participating provider operations protect the anchor from deletion and directory renaming. The guarantee covers cooperating writers on the qualified local filesystem. It does not impose conditional-write semantics on arbitrary outside writers or a remote filesystem.

Private staging directories use the same held-lock primitive. Their cleanup additionally requires an exact private ownership marker and an unlocked abandoned session. Caller directories and active staged results remain outside reclamation.

## 4. Receipt capacity and checkpoint restoration

Each unknown receipt reserves its complete configured `max_receipt_bytes` within `max_hot_bytes` before the external action. Intent enrichment and settlement consume that reservation. `usage()` reports actual, reserved and effective hot bytes; capacity pressure stops new claims while permitting settlement that reduces existing pressure. Unknown receipts remain hot. Terminal bodies can move to immutable cold storage while exact identity rows remain authoritative.

`FileEffectState.export_checkpoint(directory)` writes one SQLite backup plus the immutable cold bodies referenced by that cut and a streaming dependency index. `restore_checkpoint(checkpoint, destination)` verifies those dependencies and preserves receipt identity. It closes the restored action namespace because newer external occurrences may have happened after the backup. Existing exact-ID evidence can still be reconciled; fresh and rejected-action claims remain fenced until a separately qualified recovery establishes sufficient authority. This effect checkpoint does not by itself establish a consistent cut of a journal, notification queue, content store or derived source state.

Checkpoint export accepts explicit `max_bytes`, `max_files` and `max_file_bytes` limits. It checks the SQLite physical size and cold dependencies while copying and publishes the final checkpoint directory only after validation. A failed limit check leaves the live receipt authority usable and removes the partial checkpoint.
