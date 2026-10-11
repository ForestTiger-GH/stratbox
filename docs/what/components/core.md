# Analytical core — bounded component Target WHAT

**Implementation owner:** `ForestTiger-GH/stratbox`. **Admission:** independent/headless banking-macro domain boundary `BOUNDARY_ACCEPTED`; further normalization and new operations `CANDIDATE`.

**Role:** provide a Python library for acquiring, parsing, validating, transforming and interpreting external banking and macroeconomic statistical sources, producing typed calculations and structured analytical outputs and exports. Existing core domains include selected source collectors, regulatory bank reporting forms, industry series, escrow statistics and a specialized statistical-restoration method.

**Separation of concerns:** core does not own the GUI, desktop process lifecycle, shared multiuser session, external platform installation or a universal remote application host. Additional physical environments should connect through neutral public infrastructure and execution contracts, rather than incorporating external implementation details into banking algorithms.

**Candidate improvements:** stable subject-level operation requests/results, scoped effects and errors, realistic completeness/provenance qualification of used data, scheme and registry version checks, and discoverability for authorized notebook or machine consumers. Exact operation IDs, public schema fields, accepted series set, solver semantics and economic admission thresholds await evidence and proper Product review.

**Acceptance boundary:** direct import and execution as a Python dependency must work independently of Qt/desktop application imports. This statement **does not** promise support for every possible bank report, dataset, document or source revision. Current implementation guarantees are established only by [pinned code witnesses](../../current-how/README.md).
