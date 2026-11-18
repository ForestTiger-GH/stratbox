# 01_04_A_New_loans_corp

This adapter owns the monthly corporate loan **issuance** source identity,
reference-month validation, three-sheet parsing and typed operations.
Industry/geography dimensions, derived APK and region-by-date pivoting are
implemented through shared family helpers and explicitly reused official
01_05_A reference profiles in the sibling `debt_0105a` owner.

See [issuance-series semantics](../../../../../../../docs/current-how/cbr-industries-issuance.md) for the operation flow.

Structural result types come from `../common/contracts.py`. Source-specific
release dates, reference months, three-sheet flow profile and input requests
remain owned here. A future divergence of the physical industry/geography
profile must be reviewed and modeled explicitly rather than inherited silently.
