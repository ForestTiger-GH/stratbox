# CBR functional architecture and independently resumable data routes

Scope: the implemented CBR publication and processing contracts. The domain uses the same
functional organization as Minfin and Frank RG: source declarations, source
tables, semantic integration, calculations, products and operations have separate
owners. One CBR registration exposes the exact callable contracts. Family and
source descriptions qualify their actual coverage.

## 1. Physical owners and registries

| Owner | Responsibility |
| --- | --- |
| `stratbox/registry/cbr/{sources,profiles}` | Atomic logical series, shared family attributes, issue models, format variants, processing profiles and allowed route transitions. |
| `stratbox/registry/cbr/operations` | Complete versioned contracts, named ports, execution policy and implementation references. |
| `domains.cbr.publications/` | Official routes, discovery and selection, release/date conventions, original admission, update assessment and collection manifests. |
| `domains.cbr.tables/<family>/` | Physical layouts, source cells or records, table editions, extraction and flake codecs. |
| `domains.cbr.integration/<family>/` | Versioned subject/metric/period mappings, comparable observations and integrated histories. |
| `domains.cbr.analytics/<family>/` | Calculations, financial models and complete inputs specific to an analytical method. |
| `domains.cbr.products/<family>/` | Prepared tables, display policies, view codecs and file renderers. |
| `domains.cbr.operations/<family>/` | Typed request/result classes, metadata projections, handlers and explicit multi-stage compositions. |
| `domains.cbr.operations/bindings.py` | Source-scoped bindings to the operation catalog: formats, tables, editions, handoffs and missing capabilities. |
| `core.registry` | Shared resource loading, validation, indexes and catalog assembly. |
| `core.execution` | Named value adapters, source binding and independent invocation. |

Dependency direction follows these boundaries. Publication access does not import
parsers; tables do not import models or products; integration does not import
analytics. Products consume lower-layer values. Operation compositions connect
these owners explicitly. The import checker enforces this direction. Source families and functional
implementation packages retain one declared CBR operation owner.

Logical publication identity is `(series_id, issue_id, asset_id)`. It is separate
from URL, filename, storage location and exact byte identity. A release may
contain many observation periods. Rolling workbooks require explicit capture or
issue context when acquired. Acquisition time does not establish an official
reporting date.

Source-table profiles, semantic mappings, calculation models and product styles
have separate versions. Changing workbook colours does not change a source
flake. A changed semantic mapping can require processing unchanged originals.

## 2. Twelve families and 57 logical series

The universal workbook route covers 44 XLSX series. Thirteen series have
specialized extractors: eight reporting forms, two regional industry tables,
regional escrow and two office-network publications.

| Family | Series | Implemented route and distinctions |
| --- | ---: | --- |
| `cbr.reporting_forms` | 8 | All-member DBF flakes; reviewed projections, alignment and models for 101, 102, 123, 135, 802 and 805. Forms 134 and 803 retain the supported source route. |
| `cbr.corporate_lending` | 17 | Fifteen workbook profiles plus separate 0105a debt and 0104a issuance routes. Source observations also feed the explicitly assembled SORS method. Stocks, monthly flows and borrower counts stay distinct. |
| `cbr.household_lending` | 6 | Mortgage balances, flows and individual-housing tables with declared sheet variants, source units and period bases. |
| `cbr.funding` | 9 | Client funds, organization and household deposits, entrepreneurs, budgets and escrow-account balances. Account balances remain separate from project-finance statistics. |
| `cbr.project_finance` | 1 | Regional escrow cells, integrated history, prepared views and formatted workbooks. Historical HTML has original-only scope. |
| `cbr.service_network` | 2 | Bank/territory office counts and territorial workbooks, histories, aligned observations, count changes and prepared views. |
| `cbr.household_finance` | 2 | Household balance and operations tables; stocks, transactions and published changes have separate bases. |
| `cbr.monetary_statistics` | 6 | Monetary aggregates and sectoral surveys/balances with distinct variants, units, institutional perimeters and published growth measures. |
| `cbr.banking_sector_structure` | 1 | Sector structure with source-local institutional categories and declared period axes. |
| `cbr.securities` | 1 | Debt-securities holdings with instrument, holder and source-perimeter qualifications. |
| `cbr.external_debt` | 3 | Debt stocks and maturity/currency breakdowns; source variants and conflicting unit evidence remain visible. |
| `cbr.exchange_rates` | 1 | Daily, monthly and annual rate/index tables; trade weights have independent unit qualifications. |

The former collector categories `borrowings`, `household_assets` and
`other_statistics` are replaced by these semantic families. The 41-workbook
collection is a named convenience selection in `publications/selection.py`,
independent of the family registry.

These counts describe implemented profiles, not reviewed historical completeness.
Known table variants are explicit. Unknown sheets remain in complete workbook
flakes and receive diagnostics before semantic interpretation.

## 3. Discover a source's actual route

```python
from stratbox.domains.cbr.operations.catalog import (
    DescribeFamilyRequest, DescribeSourceRequest, describe_family, describe_source,
)

card = describe_source(DescribeSourceRequest("cbr.monetary_statistics.monetary_agg"))
assert card.outcome == "succeeded", card.diagnostics
for operation in card.value.operations:
    print(operation.key, operation.stages, operation.composition)

family = describe_family(DescribeFamilyRequest("cbr.reporting_forms"))
assert family.outcome == "succeeded", family.diagnostics
```

A source card includes exact operation/schema versions, table/variant IDs,
edition admission, semantic/model/product profiles, qualifications and handoffs.
Collection inputs require explicit assembly: one extracted workbook does not
silently become a multi-source bundle. Direct schema compatibility still
requires runtime admission and any declared parameters or additional inputs.

Family coverage lists supported, conditional, missing and delegated sources for
each stage. Publisher-wide `operation_catalog().coverage("cbr")` provides
navigation; source cards answer whether a particular format/table can continue.
Form 134 does not inherit form 101's financial model, and historical escrow HTML
does not inherit the XLSX parser.

SORS appears as a separate multi-source method on the corporate-lending card,
with ten required sources and one optional source. It is not an implied model
for every corporate-lending table.

## 4. Processing and restart boundaries

| Boundary | Responsibility | Retain and resume |
| --- | --- | --- |
| Inventory | Discover candidates and select an exact issue, asset and route. | Preserve index evidence and alternatives; availability/history remain qualified. |
| Original | Acquire or admit supplied bytes with explicit source context. | Save exact bytes and acquisition/material evidence through the chosen provider. |
| Readable material | Produce source-readable JSONL/CSV/text where provided. | Save as a representation with an identity separate from the original. |
| Flake | Decode sheets, cells, DBF records or office tables under a physical profile. | Write a complete snapshot and reconstruct the same source value later. |
| Integrated data | Apply mappings, periods, units, subjects and revision rules. | Retain typed data and exact input versions. |
| Calculation | Consume admitted integrated/model inputs under an explicit method. | Preserve results, method version and dependency vector. |
| Prepared view | Select rows/periods, arrange tables and declare display policy. | Retain tables and metadata; render without parsing or recalculating. |
| Rendered product | Format a prepared view as XLSX/CSV. | Save, transfer or archive through a caller-selected destination. |

Persistence is optional at each boundary. The next operation accepts the same
logical value whether just produced in memory or reopened from storage. No
physical database is required between every pair of operations. Encoding a
snapshot is distinct from a confirmed durable write.

`MemoryDatasetStore` and `FileDatasetStore` implement the same immutable logical
contract. Component schemas, exact values, input identities and manifests survive
reopening in a new process. Partial component reads support inspection; complete
domain replay requires every mandatory component. Paths and provider IDs stay
outside logical data identity.

### Workbook statistics

The route is `cbr.tables.extract` → `cbr.statistics.align` → optional
`calculate_change`/`calculate_share` → `build_view` → `render_view`, with independent
flake, dataset and view snapshot/read operations. Numeric lexemes, formulas,
cached values, structural cell metadata and merged ranges survive flake replay.
Missing formula caches remain unresolved; no spreadsheet engine runs implicitly.

Source-derived identities stay scoped to series/table unless explicit versioned
mappings establish wider equivalence. Published growth, transactions and adjusted
rates keep their source basis. A change calculated from two levels is a separate
computed indicator. See [statistical workbooks](cbr-statistical-workbooks.md).

### Reporting forms

Archives are extracted member by member before model selection. Supported DBF
records retain fields, raw tokens, deletion flags and member identity. Reviewed
projections feed `cbr.forms.align`; retained aligned observations continue through
`prepare_model_inputs` → `calculate` → `build_views` → `render_workbook`. The source
convenience composition calls the same independent stages. REGN and REGN_GKO
remain different namespaces. Form 102 needs explicit flow intervals. Default
model selection includes every admitted subject; a legacy subset is an explicit
profile. See [reporting forms](cbr-reporting-forms.md) and the offline
[DBF retention example](../../examples/cbr_reporting_form_flow.py).

### Corporate lending and SORS

0105a debt and 0104a issuance have distinct source, stream, calculation and view
contracts. They share reviewed physical helpers without making issuance part of
a debt owner. SORS source projection consumes retained workbook flakes; model
preparation consumes retained source observations and a parsed 0105a flake.

`cbr.sors.prepare_inputs` produces the complete validated model bundle.
`prepare_from_flakes` and `prepare_from_originals` are explicit compositions;
`restore` consumes the prepared bundle. `build_views` prepares every selected
sheet; `render_views` formats the pack independently of extraction and the solver.
Output region selection leaves the complete restoration constraints intact.
See [corporate lending](cbr-corporate-lending.md) and
[SORS snapshots](cbr-sors-snapshots.md).

### Escrow and service network

Escrow metrics and header recognition are separate from product styles.
`integrate_flakes` and the original-file `build_history` composition return the
same dataset type. `build_views` consumes that dataset. A prepared view retains
exact source versions and can be rendered independently. See
[escrow](cbr-escrow.md).

The service-network route includes histories, alignment, count changes, views
and rendering. Capture time, official reference date and observation period stay
distinct. An aggregate count decline does not identify individual closed offices.
See [service network](cbr-service-network.md).

## 5. Collections and independent destinations

`cbr.file_collector.collect_materials` accepts a heterogeneous explicit selection.
Each member chooses supplied bytes, a pinned material reference, an explicit URL
or an admitted default route. Named providers allow independent input stores in
one batch. An unavailable explicit retained input remains an error; the collector
does not replace it with an Internet download.

Every selected item has an observed disposition: completed, failed, unsupported,
not attempted or unknown. The shared `CollectionManifest` records exact members,
hashes, sizes, semantic roles, source assets, input evidence and coverage.
Selection completeness remains separate from publisher-history completeness.

Collectors expose typed `archive_members` and `manifest` outputs, including
partial results. They bind to `material.archive`, which verifies exact membership
and retains the complete selection ledger. A ZIP of successful files can thus
still describe failed and unattempted inputs. The file-only archive convenience
operation can describe only the files supplied to it.

Downloaded workbooks remain original artifacts. A generated escrow workbook is
a product artifact. Both can be saved, transferred or packaged through neutral
material operations. A mounted share or checked-out Tabularium corpus may supply
a file destination; further repository publication follows the receiver's own
policy and acknowledgement. Parsers, models and renderers contain no
destination-specific branches.

## 6. Observed updates and reprocessing

`cbr.publications.assess_updates` compares an admitted original, a processing
checkpoint and observed destination identities. It makes separate decisions for
source state, processing and each destination, without executing effects.

- Different bytes under the same issue are a source revision.
- A new official dated issue changes interpretation even if bytes happen to agree.
- A new capture label with unchanged rolling bytes does not itself change observations.
- A changed processing signature or missing result requires processing.
- An original may already be stored while a derived product awaits processing.
- Each destination is confirmed only against its own observed identity.

The caller forms the processing signature from selected table, mapping, model and
view versions/parameters. A pending plan does not claim completed calculation or
successful storage.

## 7. Admission limits and verification

The DBF codec supports reviewed classic text-oriented dBASE III layouts and
retains unsupported members with explicit partial diagnostics. Forms 134 and 803
have no reviewed financial model. Historical escrow HTML has no reviewed semantic
parser. Additional source editions require reviewed profiles; current source
success does not establish historical completeness.

Ambiguous units, periods, geography, blocks and revisions remain qualified.
Strict alignment rejects unresolved semantics where required; the complete flake
remains available for inspection. Partition large histories by release or a
bounded period set.

Local verification covers complete snapshot replay, exact numeric values,
source/model/product separation, typed material handoffs, independent adapters,
model admission and cold-process rendering. The ordinary suite requires no live
downloads. Real SORS and performance fixtures retain explicit opt-in flags.

```sh
PYTHONPATH=src python -B -m pytest -q
python -B scripts/check_internal_imports.py
python -B scripts/check_release_integrity.py
python -B scripts/check_readme_links.py
PYTHONPATH=src python -B examples/cbr_statistics_flow.py
```
