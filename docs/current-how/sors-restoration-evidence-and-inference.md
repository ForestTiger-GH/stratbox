# SORS evidence, mathematical order and inference limits

SORS reconstructs `CORPORATE_TOTAL × region × OKVED2 class × metric` from official
corporate, SME and individual entrepreneur publications. The current action
bindings live in `domains/cbr/calculations/sors/catalog.py`; the standard
operation owns every loop. [Inputs and replay](cbr-sors-snapshots.md) describes
the supported SDK route and retained values.

## Published values and latent quantities

With a publication step of one million rubles, a reported 6 means a latent amount
in `[5.5, 6.5)`. It identifies a published bucket, while an exact latent point
requires a separate proof. A publication zero similarly differs from exact zero.
Source intervals retain lower/upper attainment, and the solver uses adjacent
floating point bounds to respect open endpoints.

The hard model distinguishes `SME_IE ≤ SME ≤ CORPORATE_TOTAL`, performing and
overdue amounts, rubles and foreign currency, regional/district/national sums,
and source category membership. Equal numbers in two portfolio scopes remain
different source facts. The shared latent inequalities can constrain both.

## Evidence strength

| Assumption tier | Meaning |
| --- | --- |
| 0 | Strict official publication and latent constraints |
| 1 | Source-preserving direct published-value inheritance |
| 2 | Identification on the globally rounding-optimal face |
| 3 | Explicitly qualified rounding preference |
| 4 | Jointly checked controlled selection |

A higher assumption tier means a weaker premise. Ledger evidence strength is a
separate ordering that chooses the preferred representative for the same
published value. Closure and inheritance preserve the weakest supporting tier.
A fact derived after an optimized or selected assumption keeps that assumption;
it cannot acquire official-source status through an additional propagation step.

The append-only ledger retains historical facts, current representatives,
conflicts, source/relation/partition support, proof identifiers, optimization
phase and global feasibility confirmation. An integer value alone conveys none
of these qualifications.

## Command boundaries and fixed points

| Command | Consumes | Produces and guarantees |
| --- | --- | --- |
| `command.model.inputs` | Full interpreted role vector or exact source bundle | Validated date, units, source content and coupled portfolio inputs |
| `command.constraints.build` | Model inputs | Latent graph, publication partitions and initial inference state |
| `command.bounds.propagate` | Graph and state | New interval state and explicit derivations |
| `command.facts.inherit` | Graph and state | Source-preserving candidates tied to the exact input state |
| `command.facts.reconcile` | State and candidates or optimization proposal | A new state, proof ledger and convergence assessment |
| `command.model.compile` | Deterministically closed state | Data-only sparse problem with exact state basis |
| `command.model.feasibility` | Compiled problem | Global feasibility for that exact problem and state |
| `command.bounds.optimize` | Matching feasible problem | One qualified strict, rounding or selection phase proposal |
| `command.values.certify` | Completed state and current feasibility | Qualified full scientific result |
| `command.observations.assemble` | Certified values | Derived dataset retaining the full scientific result |

The inner loop alternates interval propagation, direct inheritance and
reconciliation until closure. A pass limit yields an explicit failure. Each
command clones mutable numerical helpers before applying changes; public table
accessors return copies, and no state retains a live solver handle.

Strict min/max, minimum rounding distortion and controlled selection run as
separate phases. After a newly admitted fact, the standard outer loop reruns
closure and global feasibility before the next phase. Certification rejects
stale candidate, problem or feasibility fingerprints. Fingerprints include exact
content and settings; observational pass numbering does not manufacture
scientific progress.

Global feasibility precedes accepted facts. A missing solver or an incompatible
source system cannot yield a successfully certified result. Source rounding
intervals remain hard under every phase. A permitted global objective degradation
is a qualified selection policy, rather than a change to an original interval.

## Conditional crosswalk

The separate `cbr.sors.crosswalk` calculation retains explicit legacy atoms,
source-node membership, allowed OKVED2 flow edges and configured mapping
scenarios. Its constraint closure, model feasibility and optional target extrema
are separate commands. Certification constructs an envelope across every
configured resolved scenario. Proven infeasible scenarios remain visible in the
assessment. Unknown, interrupted or unavailable scenarios keep the envelope
incomplete.

Crosswalk facts enter a conditional evidence layer. They preserve the mapping
content fingerprint, scenarios, relations and feasibility status. An unresolved
or multi-bucket interval carries bounds and status with an empty accepted value.
A benchmark or selected representative remains qualified separately from an
identified publication bucket.

## Interpreting outputs

The native result includes original sources and validation, primary regional
observations, latent components, restored facts, ledger history, interval
proofs, publication partitions, inherited tokens, optimization waves, solver
records, conflicts and objective profiles. Selected products can expose this
audit information alongside indicator pivots.

Before asserting identification, inspect the fact's evidence method,
`assumption_tier`, `feasibility_confirmed`, `value_precision` and bound/selection
proof flags. A jointly selected bucket can have a valid joint feasibility proof
without two independently certified min/max extrema. A deterministic bucket can
be accepted after global feasibility without claiming LP identification.

## Executable evidence and limits

The synthetic suite checks the published six and half-open interval, rejects
rounded-integer subtraction as a false inheritance proof, preserves distinct
portfolio scopes and weaker assumption tiers, executes real HiGHS phases,
checks joint selection, rejects stale continuation state, replays exact sparse
problems, and reproduces crosswalk/pivots/workbooks after process exit.

The opt-in July witness asserts 18,266 source rows, 89,760 atomic quantities and
the Udmurtia class 47 overdue-FX publication bucket 6. The June/July integration
fixtures assert full 85-region and 88-class coverage. These historical assertions
are conditional on supplying their exact external fixtures. A run that skips
them establishes synthetic numerical conformance only. It provides no evidence
of live source availability, current source-layout coverage or full-model runtime.
