# Machine capability, portable domain reuse, and product execution — bounded cross-theme Research synthesis

**Mode:** bounded cross-theme corpus synthesis for currently extracted machine-capability and execution material. **Baseline:** `stratbox@6051c890a9479a22774993b697d1bba81b57a3cd`; original Research pinned at `8459dc58922b7e8df853cf1d9e8131fa9e132580`; direct implementation contrast `stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`. **Status:** provisional Research reconciliation, **not** maintained Scientific Knowledge, approved Target WHAT/HOW or an independent verification of original extraction.

## Exact dependency set

This synthesis intersects two newly read original Research sources with five previously reconciled execution sources. It adds no new documents to the frozen census:

| Research input | Pinned original SHA | Extracted material units | Primary role |
| --- | --- | ---: | --- |
| `SB-SRC-0022` | `d7dbd145be84faf31eae88262ff19a3a9dbbe019` | 49 | Machine-readable capability, scheme and versioned planning proposals |
| `SB-SRC-0023` | `176f9d644f401ad499de80a573318159393a4983` | 43 | Domain portability, direct Python consumption, source fidelity and reusable modules |
| `SB-SRC-0024` | `201ca931a09f5bf7bba15e364da50726fdca291f` | 32 | Command/Scenario/Cascade and planner/reuse proposals |
| `SB-SRC-0026` | `0cf37ddf3b0b44495a30ec1d31117fc9dfc70671` | 37 | User launch, parameter profiles and cancellation |
| `SB-SRC-0018` | `5ed80eeb3065b60f89d0706bfa49bbfd272fc066` | 21 | Background jobs, automation and chat lifetime |
| `SB-SRC-0030` | `c4ec86841e2a92299adbefeb6a6a387b7106f587` | 38 | Error, logs, observability, external problem adapter |
| `SB-SRC-0036` | `fb8ffe1b13f5c8718b171e6c7ad3d8a0f06948df` | 36 | Shared node, user/session identity and collaboration authority |
| **Declared intersection** | seven source identities | **256** | Provisional source units, not independent seven-study confirmation |

Full original reading is recorded in `sources/CENSUS.csv`. Individual semantic roles and exact spans are in `units/BASE-STUDY-0022.jsonl`, `0023.jsonl`, `0024.jsonl`, `0026.jsonl`, `0018.jsonl`, `0030.jsonl`, `0036.jsonl`. An earlier independent-value bounded execution synthesis exists at `reconciliation/EXECUTION-CROSS-THEME.md`; it is not a second source census or separate vote.

## Minimal common mechanism, without premature unification

The common principle across the texts is one domain implementation consumed in distinct contexts. An analytical **mechanism** (HTTP/DBF/FileStore), reusable **technical function**, **domain service** and user-meaningful **operation** need not be represented by one universal registry object. A desktop, notebook or permitted machine consumer can call a suitable public subject API; a user-facing **Scenario** may orchestrate several operations; a managed execution authority would provide **Job/Attempt/Case/Event** truth only if actually implemented and authorized.

The following concept layers are *useful for reasoning*, but do not require one-to-one source modules or new repositories:

```text
Subject data identity and semantics (source / reference snapshot)
        ↓
Reusable domain capability (typed public operation when justified)
        ↓
Optional inspectable composition (scenario / scheme / larger goal)
        ↓
Resolved invocation and execution plan
        ↓
Actual execution authority, outcomes and effects
        ↓
Evidence, artifacts and audience-scoped client projections
```

No single document establishes that every link in this candidate pipeline exists as operational code today. The current core offers heterogeneous staged domain functions and rich specialized outputs; Windows offers static operation specs, limited composed scenario and Qt execution, plus local JSON history/background scaffolds.

## Unresolved definition and ownership conflicts

| Tension | Source-unit lineage | Alternatives that survive | Resolution status |
| --- | --- | --- | --- |
| Is a product **Scenario** the same as a reusable **Scheme**? | `0022:004,027,045`, `0024:004,007,008`, `0026:004` | A Scheme may be toolkit-neutral process data below the user product; a Scenario may be its contextual user projection. Conversely a simple product can use one Scenario definition with embedded steps. | **OPEN — no accepted product ontology.** |
| Does **Cascade** require an independent definition? | `0024:008–010`, `0022:045` | Independent Cascade has its own reuse, naming, audience and owner; generic nested Scheme can express same composition technically, with the user label projected separately. | **OPEN**. Distinct user identity does not force a separate DAG engine. |
| Operation versus technical Command | `0023:003,035`, `0022:004,007`, `0024:001,006` | Core Operation denotes subject-level use case; technical command may be separate planner primitive when independent effect/retry/resource control is needed. | **CONDITIONAL**. Helper functions must not automatically enter a machine catalog. |
| Where does a semantic planner live? | `0022:030`, `0024:011,016`, `0036:013` | Reusable pure plan/type checking may belong with core semantic contracts; authoritative scheduling/queues must align with actual node/application execution and grants. | **OPEN physical allocation**, logical distinction retained. |
| Rich Python Result versus serializable Result | `0023:030`, `0022:009,036`, `0030:010` | Keep DataFrames and mathematical evidence in native Python; provide a separate serializable projection/ref when transport, persistence or machine discovery needs it. | **Compatible**, no premature universal domain result. |
| Public reusable blocks versus machine tool explosion | `0023:026,027`, `0022:028` | Small public functions remain direct imports; only curated operations receive durable semantic ID and effect/availability contract. | **Reconciled conditional rule**, not adopted registry interface. |
| Operation definition versus run state | `0022:003,039`, `0018:002,010`, `0036:013` | Immutable definition and invocation/plan identity can be portable; scheduler, actor, receipts and job state need actual execution authority. | **Reconciled meaning**; runtime readiness unproven. |

**Strongest cross-theme challenge:** a universal machine Scheme does not automatically make a user Scenario or Case obsolete. The user work item, authorization, audit timeline, review/assignment and ongoing execution may have lifetimes and ownership unrelated to the stability of a reusable algorithm. Conversely the existence of separate Scenario and Cascade labels in today's UI does not prove they deserve two independent graph runtimes. Keep the conceptual tension explicit.

## Reconciled data and effect constraints

1. **Source fidelity is distinct from analytical decoding.** `SB-SRC-0023` describes a source-preserving DBF conversion requiring preservation of selected lexical and record properties, whereas the pinned `base/ioapi/dbf.py` currently provides DataFrame conversion. The richer notebook is a secondary research carrier and has not been executed here. No release claim about a faithful transcoder is permitted.
2. **Actual source snapshot differs from acquisition definition.** Canonical registry/source IDs, bytes, reporting period and transformation versions cannot be replaced by a filename, URI or filesystem mtime. This aligns with the separately published bounded scientific source-identity topic.
3. **Effect-safe dedup is narrower than code reuse.** A pure calculation may serve several consumers. Distinct file writes and approvals remain distinct effects. A cache of prior outputs is not within-plan reuse, nor does either prove idempotent remote write.
4. **Modelled effect or visibility is not authority.** Declaring `destructive`, `AI-visible`, `requires_capability` or `cancellable` in a spec does not create enforcement or working cancellation. A managed executor and a validated grant decision must exist at the effect boundary.
5. **Conditional handling of UNKNOWN.** After a lost acknowledgement or worker termination, externally visible effects may have happened despite a failure observation. An unqualified generic `FAILED` boolean is scientifically inadequate if the effect state is unobserved.
6. **Offline notebooks and mobile clients do not share all affordances.** Domain Python APIs can be useful directly in a notebook; mobile status/action surfaces need neutral serialized projections. Qt widgets and platform-specific filesystem paths are not portable data contracts.
7. **Pipeline granularity is consumer-driven.** A typed DAG can make independent reuse/provenance visible, but a simple domain operation need not be split into dozens of registered commands to make it machine-readable.

## Evidence independence, counterexamples and negative space

The seven Research documents share the same current core/Windows baselines, design themes, and frequently quote or rely on one another. Their convergence is **one dependent research family**, not seven independent observations. Static source checks support narrow current claims: `base/ioapi/dbf.py` implements DataFrame read/write paths, `escrow/operations.py` exposes separated stages, `frg/cleanup.py` performs per-row effects, `application/scenarios/runner.py` sequentially executes steps, and `application/background/store.py` supplies local state rather than an installed scheduler.

The strongest negative arguments against immediate product admission are: an extra abstraction without a concrete client may create catalog/ABI maintenance cost; a universal dataset or result erases domain-specific evidence; generated Python or arbitrary DSL evaluation defeats static effects inspection; a local shared directory does not create transactional node history; and a status button is not actual cancel/approval authority. The research does not include independent runtime throughput measurements, actual multiuser installed tests, completed capability conformance runs, verified source-data revisions, or formally accepted product requirements.

An original portability research document includes access-bounded environment material. That content is **excluded from this public cross-theme synthesis**; the safe general boundary is external implementation behind neutral public contracts and separate qualification. No restricted identifiers, package names, paths or implementation behavior are reproduced.

## What this corpus cannot decide

It cannot decide **which** named public model types ship, whether a new `Scheme` or `Cascade` package is justified, semantic-version/retention guarantees, publication/fidelity rules for DBF, whether a durable node executor is required in the next release, placement of an optional remote service, actual permitted machine actions, or client/mobile scope. These are scoped Product, Science, external-platform and release authorities respectively.

**Synthesis verdict:** bounded Research relation model established for 256 provisional material units with explicit common lineage and unresolved consumer-level terminology. **NOT** independent full material conservation of seven files, **NOT** global Scientific corpus reconciliation, **NOT** Product adoption, **NOT** runtime acceptance.

**Reopen:** any underlying source baseline, new independent user/operational evidence, actual declared product use cases, tests of alternative composition models, or new admitted original research. Next Work: verify the two new ledgers and census statuses; then continue remaining base studies and 00–09 research before global source-to-final-owner challenge.
