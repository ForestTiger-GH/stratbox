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
| `shared.identity` | Immutable digest/byte size and canonical manifest encoding. |
| `shared.evidence` | Source materials and acquisition, used-input, storage and publication receipts. |
| `shared.data` | Observation, dataset version, computation, representation, release comparison and table contracts. |
| `shared.reference` | Explicitly versioned packaged assets, bank and OKVED2 references and territorial name resolution. |
| `shared.time` | Date-only calendar period and anchor generation. |
| `domains.registry` | Discovers independent domain declarations and joins them with neutral operations. |
| `domains.<source>.<family>.<owner>` | Official source parameters, interpretation, period rules, calculations and output profiles. |
| Consumer | User interface, schedules, destinations, host authorization, publication and downstream effects. |

Local `_registration.py` manifests identify exact operation owners. The registry discovers
them recursively; the nearest registered ancestor owns a module, rather than an
entire publisher namespace. Child publication series may reuse their parent
family's dedicated `common` modules, while direct cross-owner dependencies
are allowed only for specifically identified source-schema reuse. A grouping
package never owns an operation without a local `_registration.py`. Publisher-neutral execution remains in core.

## Dependency contract

Shared semantic contracts depend on neither the executable core nor concrete
domains. `identity` is the minimal root; `evidence` depends on `identity`; `data`
does not import concrete `reference` modules. Reference assets verify exact bytes and
carry an explicit snapshot version. Infrastructure ports and neutral formats are independent of subject
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

[Shared owner boundaries](shared-ownership.md)

[Core API and evidence limits](../current-how/universal-business-core.md)

[Domain functional ownership and economic invariants](domain-functional-semantics.md)
