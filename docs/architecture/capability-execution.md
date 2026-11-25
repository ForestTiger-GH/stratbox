# Capability definitions and execution

The canonical capability path separates authored definitions, prepared command
work and accepted results. Four kinds share one catalog and one execution
session: command, operation, scenario and cascade. This architecture covers
the core foundation and vertical pilot. The existing domain operation corpus
remains an explicit migration contribution until its domain migration stages.

## Ownership and dependencies

| Owner | Responsibility | Allowed dependencies |
| --- | --- | --- |
| `capabilities/model` | Pure contracts, authoring graph, acceptance and reuse identity | Shared contracts |
| `capabilities/catalog` | Immutable snapshots, resolution, profiles, methods and typed views | Pure models and shared contracts |
| `capabilities/commands`, `operations`, `scenarios`, `cascades` | Authored definitions and implementation references | Pure models and catalog descriptor types |
| `composition` | Closure, lowering, scopes, physical plan and explanation | Definitions, shared contracts and neutral execution handoff |
| `core` | Providers, resources, execution, owned values and effects | Pure contracts and technical implementations |
| `domains` | Source-specific interpretation and analytical meaning | Shared contracts and technical core |
| `sdk` | Bootstrap, embedding and direct calls | Catalog, compiler and execution service |

Definitions contain implementation references rather than imported handlers.
Discovery imports no numerical or workbook backend. The bootstrap binds only
selected command implementations for execution. A catalog snapshot fixes the
definition, method, profile and reference identities for a prepared plan.

## Authoring and preparation

An operation body contains command calls. A scenario contains operations or
reusable scenarios. A cascade coordinates scenarios and preserves their
individual acceptance scopes. Structural nodes organize work; they do not
replace analytical operations.

Exact preparation resolves the selected method and profile, then builds the
dependency closure from requested outputs, required checks and required effects.
Supplied accepted values cut their upstream prerequisites. Concrete input and
provider admission applies to the selected closure. Unused branches impose no
runtime requirement. A required save remains required when its receipt has no
downstream reader.

The authoring graph lives under `capabilities/model`; the physical execution
plan lives under `composition`. The plan preserves logical occurrences and
their mapping to physical commands. Equivalent command work may serve multiple
operations while retaining independent consumer acceptance and scope outcomes.

## Execution and ownership

The session coordinates initial tasks and admitted dynamic work with the same
provider checks, resource ledger and upper quotas. Waiting followers consume
no worker. Cancellation of one consumer preserves a shared producer needed by
another consumer. Retry delay belongs to the coordinator.

Candidate values become accepted only after validation. Mutable inputs receive
isolated reads. Demand pins, reader leases and retained result ownership control
cleanup. Completing a run releases its active-run slot; live returned results
remain charged until their owner releases them. Process-private spill remains
local temporary storage.

All task, attempt, scope, map and collection projections address the same
managed result placement. Moving a result to temporary storage clears its
resident payload through that owner. Reads reserve materialization capacity;
mutable worker copies hold their own reservations until consumption finishes.

Every capability owns its named output promises. A scenario predicate can
reject its exported output while the successful nested operation remains
available separately. Named predicates can release independent outputs early.
Predicates over multiple outputs wait for their full input group to settle.
Inherited activation conditions compose as a conjunction throughout the graph.

In-flight sharing and completed reuse have separate permissions. The shared
work identity includes the selected semantic basis and actual input evidence.
Content equality alone cannot transfer another consumer's source ancestry.

Effects have their own authority, expected revision and confirmation state.
Computation success, committed storage and notification delivery are separate
facts. A lost effect reply remains unknown until reconciliation. Observability
projects authoritative execution facts; optional capture failures preserve the
business result. Durable recovery is supplied by an external host through the
declared state, artifact and effect ports.

Promised publication capacity is reserved before work is admitted. Immutable
fact obligations enter the bounded outbox before journal publication; a full
journal delays their transfer while preserving their identities. Variable-size
effect producers reserve additional receipt capacity before each mutation.
Impossible claims fail admission; temporary pressure suspends dynamic expansion.

The [effect and stage-event guide](../current-how/effect-recovery-and-stage-events.md)
describes reconciliation, retained facts and notification boundaries.

## Adding capabilities

Add a pure typed definition, an implementation reference for each command and
an explicit profile or method binding for source-specific interpretation.
Use a local snapshot overlay for temporary notebook definitions. Keep source
selection in registered groups and recipes. The generic compiler contains no
publisher-specific dispatch.

The import checker enforces pure capability metadata ownership and shared
dependency direction. Deterministic vertical fixtures distinguish synthetic
execution evidence from publisher-layout evidence. Complete domain migration
and machine facade migration have their own later acceptance gates.
