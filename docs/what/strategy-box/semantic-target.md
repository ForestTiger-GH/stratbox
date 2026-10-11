# Strategy Box semantic target — concepts versus admitted product elements

**Baseline:** `TW-SB-2026-10-09-CANDIDATE-1`, mixed admission. The vocabulary below intentionally distinguishes **possible semantic entities** from **existing, verified or explicitly promised capabilities**. A Research noun is not a mandate to add a table, class or network service.

## Data and analytical meaning

Candidate domain concepts:

- `Source`: a publisher/publication family or addressable source rule. `SourceSnapshot`: a particular observed byte revision with acquisition metadata.
- `Registry`: a versioned interpretation of entity identifiers, accounting perimeters and official statistical classifications.
- `Dataset/Observation`: canonical observations with period, unit, missingness, scope and evidence qualification. `DerivedResult`: computed or inferred values with their method and inference strength.
- `Artifact`: a user-consumable output such as an XLSX/CSV/document/report, whose identity and availability are separate from the underlying economic result.

**Current code witness:** the core contains distinct domain families `cbr_forms`, `cbr_industries`, `escrow`, `cbr_file_collector`, `frg` and specialized SORS restoration. Some produce structured results and files, but a single universal source registry, domain-wide provenance receipt, and complete managed Artifact identity have **not been verified as a shipped cross-domain product**. Source catalog, registry release identity and raw snapshot retention are **candidate mechanisms**, with proportional maintenance cost. Actual acquisition time for **used inputs**, rather than a compulsory global indicator catalog, is the source-supported near-term direction.

## Capabilities, work and execution

- `Capability`: a subject-matter ability in an explicitly authorized actor/data/environment context, not a blanket user privilege.
- `Operation`: an independently meaningful typed analytical or effect-bearing task.
- `Scenario`: a human-facing use or composition of operations. `Scheme`: a reusable conceptual/machine projection of subject capabilities, with any distinct Scheme API **CANDIDATE**.
- `Work`: a persistent commissioned task/goal; `Run`: one logical invocation/episode; `Job`: a schedulable execution unit; `Attempt`: one actual backend try. This distinct identity model is **CANDIDATE** until an authoritative implementation contract is admitted.
- `Result`, `Event`, `Log`, `Problem` and `Effect` convey different evidence. Run completion, accepted analytical claim, artifact publication and observed external mutation are not interchangeable. Physical lifetime and storage owner of each remain candidate choices.

**Current consumer:** at the pinned Windows baseline the UI presents scenarios/cases and locally stored history; it exposes a bounded fixed operation catalog and one sequential case coordinator. Exact behavior and limitations belong to [Windows Current HOW](../../current-how/windows-application.md). A full Work/Job authority, hosted scheduler and universal machine API are future proposals, **not** verified deployed features.

**Independent Python requirement:** the domain core should be callable from Python/notebook use without importing a desktop GUI; future clients and machine projections must not rewrite core business algorithms as UI-specific code. Which operations deserve stable machine-capability identities remains a separate admission question.

## Actors, authority and presentation surfaces

`Actor` is the executing requester/automation, `Principal` supplies authorization, `Participant` joins collaboration, while `Node` and `Session` describe external platform lifecycle. These can be related but must not be treated as one implied grant. The exact principal-role vocabulary and policy enforcement for remote Web/host remain open.

Future Windows/Web/Android clients may share **semantic presentation and status concepts** while retaining platform-native layout and interaction mechanics. A client's claim of support depends on actual installed capabilities, authorized host connectivity and tested execution owner, not the existence of a planned schema.

## Candidate observable invariants requiring Product admission

| Candidate | Possible independently testable property | Status |
| --- | --- | --- |
| `TW-C01` | A missing/unavailable/unknown observation is never silently substituted by numeric zero. | CANDIDATE |
| `TW-C02` | Execution outcome is distinct from domain correctness, accepted Work and strength of evidence. | CANDIDATE |
| `TW-C03` | Requesting cancellation is distinct from proving that an external effect was cancelled. | CANDIDATE |
| `TW-C04` | Repeated commands cannot duplicate unsafe effects without verified idempotency/preconditions. | CANDIDATE |
| `TW-C05` | Shared-node or remote clients cannot read another principal's unauthorized Work, events or artifacts. | CANDIDATE; conditional shared/remote profile |
| `TW-C06` | Incomplete file bytes cannot be presented as a committed published Artifact. | CANDIDATE |
| `TW-C07` | Common scenario meaning can reach more than one UI surface without requiring a Qt runtime in the core. | CANDIDATE |

These IDs label **draft product properties**, not implemented runtime APIs, accepted normative requirements or release guarantees.
