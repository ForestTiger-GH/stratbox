# Core operation boundaries

Stratbox separates reusable technical operations from domain-specific methods.
The installed package has three independent semantic owners: `stratbox.core`,
`stratbox.shared`, and `stratbox.domains`. Applications compose capabilities,
operation calls and scheduling outside the library.

| Owner | Responsibility |
| --- | --- |
| `core.runtime` | Provider selection, capability requirements, secrets and optional dependencies. |
| `core.storage` | File-store ports, local implementation, byte identities and bounded staged writes. |
| `core.network` | Typed requests, response/peer qualification and transport. |
| `core.formats` | Independent file format parsers, workbook codecs and archive handlers. |
| `core.rendering` | Presentation-oriented projections and Excel styling. |
| `core.execution` | Invocation context, runner, cancellation, outcomes, event stream and immutable operation catalog. |
| `core.operations` | Domain-neutral acquisition, original-byte storage, comparison, validation and table operations. |
| `core.observability` | Event records, evidence assessment, capture, immutable journals and analysis. |
| `core.notifications` | Topic/subscription definitions, authorized intents, transaction state and qualified handoff. |
| `core.registry` | Catalog of built-in neutral operations. |
| `shared.data` | Byte/material identities, observation contracts, representations, evidence and computation manifests. |
| `domains.registry` | Discovers independent domain declarations and joins them with neutral operations. |
| `domains.<name>` | Official source parameters, interpretation, period rules, calculations and output profiles. |
| Consumer | User interface, schedules, destinations, host authorization, publication and downstream effects. |

## Dependency contract

Shared semantic contracts depend on neither the executable core nor concrete
domains. Infrastructure ports and neutral formats are independent of subject
matter. The generic executor does not depend on concrete operations. Neutral
operations compose the executor and infrastructure; observability consumes
execution records and storage contracts; notifications consume evidence and
use explicit state and handoff provider ports. No foundational component
imports a concrete domain. The public library has no historical
`stratbox.system` compatibility package.

## Operation identity and effects

Built-in HTTP transport evidence identifies the adapter family with stable\nsemantic tokens (`http.requests.v1`, `http.routed.v1` and\n`http.peer_bound.v1`). A caller-supplied custom transport should use an\nexplicit capability provider ID when requests participate in persistent\nevidence; an unbound custom class name is only a local fallback. This\nidentity contract replaces class-location-dependent built-in fingerprints.\nArchival receipts retain their original meaning and are never rewritten.\n\nA Python module path identifies a program implementation. It is not a logical
operation ID. The ID, contract version, request and result types and effect
rules are validated by `OperationRegistration` and `OperationCatalog`.
Physical refactoring does not change source material identities or downgrade
`confirmed`, `failed`, and `unknown` qualifications.

| Identifier | Owner |
| --- | --- |
| Package version | Installed distribution |
| Contract version | Public request and result schema |
| Method version | Domain calculation or representation method |
| Invocation ID | One executor call |
| Run, step, attempt | Caller orchestration |
| Release version | Input bytes, method and result manifest |
| Effect key | One authorized destination state transition |

A neutral source operation can archive an original independently of parsing,
parse later, or request only a literal representation. Other domains share
the same infrastructure and choose their own source-specific interpretations.

[Core API and evidence limits](../current-how/universal-business-core.md)
