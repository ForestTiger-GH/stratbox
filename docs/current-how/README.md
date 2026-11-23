# Current HOW — observed Strategy Box mechanisms

[Stratbox core operations](universal-business-core.md)

[Universal material flow and typed operation handoff](universal-data-flow.md)

[Logical dataset snapshots and storage adapters](logical-dataset-snapshots.md)

[CBR publication registry and independent processing routes](cbr-data-pipeline.md)

[CBR statistical workbooks: source cells, qualified observations and retained views](cbr-statistical-workbooks.md)

[CBR reporting forms: complete DBF flakes, CSV collections and calculation replay](cbr-reporting-forms.md)

[CBR corporate debt and issuance: retained flakes, histories, calculations and views](cbr-corporate-lending.md)

[CBR escrow: source cells, integrated history and prepared-view replay](cbr-escrow.md)

[CBR service network: qualified releases and explicit-date replay](cbr-service-network.md)

[CBR SORS: source dependencies and calculation snapshots](cbr-sors-snapshots.md)

[Current shared semantic contracts](shared-semantic-contracts.md)

[Versioned reference snapshots and update procedure](reference-snapshots-and-update.md)

[Territory names and reviewed identity resolution](geography-name-resolution.md)

[Automatic domain registration and operation discovery](domain-operation-registry.md)

[Core operation construction](core-operation-construction.md)

[Processing roles, qualified connections and bounded operation discovery](processing-operation-catalog.md)

**Status:** maintained current shared contracts and CBR processing routes, plus
the nine bounded historical implementation slices below. The current route
guides describe executable local operations and regression coverage. Full
Current HOW reconstruction, deployed-state verification and independent
assurance remain open.

## Historical implementation slices

- [Public AppDock Recorder and exact ProblemQuery](appdock-public-problem-contracts.md) — existing neutral contracts for recorded occurrences, unconfirmed references and five lookup outcomes; installed app-client integration unverified.
- [Public AppDock activation versus host attachment](appdock-activation-host-attachment-boundary.md) — actual process launch, explicit delegated-backend unavailability and remaining remote host evidence gap.
- [Analytical core runtime and network transport](core-runtime-network.md) — provider composition and typed HTTP download outcomes.
- [Windows application lifecycle, scenarios and local history](windows-application.md) — activation, case execution, JSON history and background status scaffold.
- [FRG cleanup plan and destructive effect handling](frg-cleanup-effects.md) — plan/apply separation, per-row results and explicit failure/partial-effect limits.
- [SORS reconstruction, evidence and publication rounding](sors-restoration-evidence-and-inference.md) — direct implementation of multi-scope source constraints, exact/publication distinction, tiered inference, feasibility gates, fixed-point and optimizer failures.
- [CBR forms semantics and skipped publication dates](cbr-forms-semantic-model-and-missing-periods.md) — source/indicator/Excel separation, form 802 hierarchy and the observed dropped-download period failure mode.
- [Download source receipts, packaged registry selection and observed coverage limits](source-download-receipts-registry-choice-and-coverage-limits.md) — direct code/test inspection of transport outcomes, collector partial failures, duplicate filenames, local mtime selection, absent universal byte-vintage receipts and the date-skipping gap.
- [Local FileStore missingness, path boundaries and publication limits](local-filestore-missingness-and-publication-limits.md) — three pinned code witnesses, absence versus empty listing, direct write truncation and scope-limited path authorization assumptions.

**Exact direct-source baselines:** `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580` and `stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`. The external managed platform is a separate contract owner and its potential future features are not evidence of present runtime behavior.

These modules have local static evidence, but no GUI, tests, filesystem mutation, fault injection or installed application was executed. They do not prove currentness of all other domains, complete coverage of the 566 registered file source identities, or end-to-end reliability.

Uncovered mechanisms remain owned by their direct implementation and test source files. The scientific and target documents do not override their observed control flows.

- [Rosstat original publication acquisition and version evidence](rosstat-publications.md)
