# Source-domain functional semantics

This is the maintained functional-ownership map for `src/stratbox/domains`.
Package names describe *who publishes the original statistical data* and the
publication family, not its file format or the destination storage taxonomy.
Publisher-specific rules belong to owners. General technical primitives belong
to `stratbox.core`; cross-source semantic data contracts belong to
`stratbox.shared`. Multi-source analytical models may define an independent
subject boundary rather than pretending to belong to a single publisher.

## Owners and economic meaning

| Registered owner | Original and economic object | Time and quantity semantics |
| --- | --- | --- |
| `rosstat.publications` | Official Rosstat publication indexes, release/asset identity and exact native files; acquisition precedes any statistical interpretation | Publisher issue labels are not inferred observation periods; PDF/XLSX/ZIP/RAR bytes are versioned independently of extracted facts |
| `cbr.file_collection` | Official Bank of Russia original-file catalogs, acquisition and archival preparation | Original source identity; no implied statistical period |
| `cbr.reporting_forms` | Bank-reporting forms and their physical/formula models | Each published form owns its reporting periods and measurement definitions |
| `cbr.escrow` | Escrow account histories, tables and Excel workbooks | Periods and indicators as published in each source workbook |
| `cbr.service_network.bank_offices` | Bank-by-region daily office publication captured from HTML | Capture date distinct from publisher's stated observation context |
| `cbr.service_network.territorial_offices` | Bank-office regional aggregates from dated XLSX publications | Source as-of date; region/federal-district and mobile-office distinctions |
| `cbr.corporate_lending.industries.debt_0105a` | Corporate lending outstanding and overdue debt by industry/region/currency | **Stock** at the reported date; six physical sheets |
| `cbr.corporate_lending.industries.issuance_0104` | Newly issued corporate loans by industry/region/currency | **Flow** for the reference month; source report date is generally next month's first day; three sheets |
| `cbr.corporate_lending.sors_restoration` | Constraint-based restoration of regional economic activity observations | Derived estimates with explicit feasibility/evidence/rounding semantics; never relabel as original observations |
| `fns.legal_entities_1yur` | Legal entities by status, legal form and geographic unit | Dated snapshots; historically changing published columns require explicit epoch mappings |
| `fns.sme_register` | Regional SME register statistics | Dated regional/monthly snapshots; preserve published identity and measure |
| `frank_rg` | Logical report sources, runtime delivery, standard naming, cleanup plans and archive selection | Supplier snapshot dates and numbered weeks within a month; file metadata and exact byte revisions remain separate; workbook interpretation and calculations are explicit gaps |

A grouping package is not automatically an operation owner. It becomes an owner
only with an exact local `_registration.py`. One logical operation ID belongs
to one registered owner across all its versions, independently of Python
module locations. Owners publish domain contracts; the neutral executor does
not import concrete domain implementations.

## Functional invariants

1. **Originals and derived results differ.** A source acquisition preserves exact
   source bytes and identity; parsing creates typed observations; views and
   calculations have their own methods and evidence.
2. **Published totals remain published values.** A total is recomputed only when
   a method explicitly defines a derived total. Source totals are not silently
   replaced by sums of subcategories.
3. **Time has economic meaning.** Stock-at-date and monthly-flow-for-period
   are separate types of observation. A file's publication date is not
   automatically its economic reference month.
4. **Geography follows each publication.** Country, federal districts,
   constituent regions and special component/exclusion rows must keep their
   published roles. A source-specific geographical layout is not a universal
   region registry.
5. **Full-source validation precedes selective materialization.** Industry
   selection controls output size but cannot hide invalid source observations.
   APK calculations require all component industries, even for a narrow view.
6. **Independent source evidence survives normalization.** A representation
   may use canonical names while retaining original labels, source file,
   sheet and cell positions when available.
7. **Partial work is explicit.** Failed source acquisition, missing inputs,
   source-layout changes and incomplete calculations surface a diagnostic or
   partial outcome, never an apparent complete result.
8. **Side effects belong to declared operations.** Planning and reading
   are distinct from writing, deleting, scheduling, delivery and publication.

## CBR industry-family boundary

`industries/common` owns structural industry/geographic models, validation
issue shapes, pivot and APK result contracts, common text/stream formatting,
shared selection/Excel renderer and evidence helpers. It does **not** own the
two series' operations. Each series owns its source links, requests, workbook
sheet profile, report-date mapping, quantity type and result interpretation.

The issuance series currently references explicitly verified 01_05_A reference
profiles and the same calculation and pivot algorithms. This is a deliberate,
restricted reuse of *published source semantics*, not an assumption that
stock and flow are interchangeable. A future source revision with divergent
geography, industry codes or definitions requires its own reviewed profile.

SORS consumes specifically published source parsers/schema, but owns the
restoration and evidence semantics. The repository's import-direction check
restricts this one-way dependency.

## Quality and acceptance

The executable inventory comes from `domain_registration_inventory()`, not a
hard-coded 11/68 ceiling. To verify new and existing owners, use:

```bash
python -B scripts/check_internal_imports.py
python -B scripts/check_release_integrity.py
python -B scripts/check_readme_links.py
python -m pytest -q tests/unit/registry tests/unit/architecture tests/unit/macrobanks tests/integration/universal_core tests/cbr_sors_restoration
python -B scripts/local_release_check.py
```

The last check validates source/wheel/sdist manifests, data assets and isolated
operation resolution; it requires locally installed dependencies and is
independent of GitHub Actions. Keep synthetic tests of incomplete hierarchies,
cross-owner IDs, stock/flow periods and partial/invalid observations in place.

This document describes the current functional boundaries. It does not claim
that the experimental FRG report-parser stubs perform real data extraction.
