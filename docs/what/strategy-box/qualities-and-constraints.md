# Target WHAT — qualities, constraints and open commitments

**Admission:** mixed. Established purpose and independent ownership boundaries may be `BOUNDARY_ACCEPTED`; quality properties of an unbuilt or untested runtime remain `CANDIDATE`. Each potential release promise requires an applicable profile, accountable owner and observable acceptance evidence.

## Established directions and constraints

1. **Headless analytical core:** banking and macroeconomic subject algorithms must remain usable from Python without requiring the Windows UI.
2. **Separate responsibility owners:** Windows and other application layers should consume core domain semantics without duplicating or secretly changing the computations. An external platform's versioned contract is not core source code.
3. **Portable application meaning:** reuse application contracts and semantic UI elements across future surfaces, including Android, while keeping Qt/browser/native rendering platform-specific.
4. **Public-source protection:** publicly published knowledge and neutral extension interfaces must avoid environment-specific protected implementation information.
5. **No legacy API compatibility requirement:** breaking API changes are permitted where authorized. Safe handling of **existing user data, valuable artifacts and persisted state** is a distinct policy, not an accidental waiver of data integrity.

## Candidate measurable quality and failure cases

| Concern | Possible property / falsifying case | Gate |
| --- | --- | --- |
| Data trust | Source/registry revision and evidence limitations are available for material claims; absent data is never silently converted to zero. | PRODUCT DECISION |
| Execution | Job/Run status and cancel/retry outcomes are truthful; UI failure must not be reported as confirmed worker outcome. | PRODUCT DECISION / deployed profile |
| Durable state | Corrupt authoritative Work data produces an explicit diagnosable condition rather than silent data loss or an empty history. | OWNER / deployment profile |
| Effects | Dangerous operations require authority, scope-specific confirmation and verifiable receipts; incomplete/ambiguous mutation is not declared fully successful. | RISK POLICY |
| Collaboration | A remote/shared client receives only records and events authorized for the relevant principal and audience. | CONDITIONAL multiuser profile |
| Artifacts | Writing and content verification finish before the externally visible terminal publication state; a manually deleted file can still become a simple unavailable link. | ARTIFACT POLICY |
| Observability | Concise user-safe conditions are separate from restricted raw technical logs; relevant incident routing is scoped. | PRIVACY AND PLATFORM CONTRACT |
| Performance | Workload, source size, latency, memory and responsiveness limits are measured against actual target devices and execution profiles. | MEASUREMENT |
| Accessibility | Keyboard operation, focus, text scaling, contrast and state interpretation remain usable without color or motion alone. | TESTED TARGET PROFILE |
| Operations and recovery | Recovery of connected state+files, truthful RPO/RTO and controlled upgrades are exercised, not merely declared. | DEPLOYMENT POLICY |

**Numeric thresholds are deliberately not invented.** The right performance or durability guarantee depends on actual user hardware, source sizes, criticality, workload, host installation and independently demonstrated failure/recovery behavior.

## Scope and admission

The present baseline offers an independently readable list of purpose, risks and **candidate** qualities but is not a complete Product Commitment Census covering every historical user decision and every new operating profile. It is suitable for reviewing WHAT choices; it does not itself establish a released product specification.

Before a candidate becomes binding, record the authorized product decision, applicable deployment and data profile, exact observable acceptance tests, known limitations, versioned external contracts and implementation owner. Only then may Target HOW select physical stores, schedulers, API protocols and client rendering choices without silently promoting Research into policy.
