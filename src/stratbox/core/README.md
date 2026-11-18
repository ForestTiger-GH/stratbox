# Stratbox core

The `stratbox.core` package owns reusable execution, capability-based runtime composition,
storage, network transport, format-specific encoding and decoding, presentation,
generic source and table operations, observability, and notification handoff.

`stratbox.shared` owns immutable byte identities, used-input and effect receipts,
statistical data contracts, reference edition assets and calendar semantics. `stratbox.domains` owns
individual banking and economic methods. A domain can call core services; core services
never import a concrete domain.

## Package owners

- `runtime/`: provider composition, secret ports, optional dependencies and capabilities.
- `storage/`: file-store ports, local adapters, bounded byte IO and staged writes.
- `network/`: HTTP and peer-qualified transport.
- `formats/`: format decoders and encoders; `spreadsheets/` and `archives/` are specialized groups.
- `rendering/`: presentation-oriented Excel styles and readable projections.
- `execution/`: invocation, typed results, events and operation catalog.
- `operations/`: neutral source and table operations implemented through execution.
- `observability/`: records, evidence assessment, capture, journals and projections.
- `notifications/`: subscription intent, state, qualified handoff and reconciliation.

Operation identities are logical contract IDs, not Python module paths. Journal
write outcomes, effect receipts and source identities must retain their existing
semantics across the package relocation.

See [core boundaries](../../../docs/architecture/core-operation-boundaries.md) and
[shared owners](../../../docs/architecture/shared-ownership.md).
