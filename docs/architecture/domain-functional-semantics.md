# Source-domain functional semantics

Publisher domains own the economic meaning of their source publications and the
operations that interpret them. Functional packages separate acquisition,
source tables, semantic alignment, calculations and presentation. General
execution, byte formats and storage adapters belong to `stratbox.core`;
cross-source data contracts and shared reference semantics belong to
`stratbox.shared`.

The registered operation owner and a publication-family identifier are different
identities. CBR has one root operation owner, `cbr`, with independently maintained
functional segments. A source card describes applicability to one publication,
format and table edition. An aggregate domain capability never establishes that
every publication supports the same analytical route.

## 1. Registered owners and economic boundaries

| Registered owner | Original and economic object | Important semantic boundary |
| --- | --- | --- |
| `rosstat.publications` | Rosstat indexes, releases, assets and exact native files | Publisher issue labels are distinct from observation periods; original byte identity precedes statistical interpretation |
| `cbr` | Bank of Russia reporting forms, banking and monetary statistics, lending, funding, office networks and other declared publication families | One root registration; separate source, integration, calculation and product owners with source-specific coverage |
| `minfin` | Ministry of Finance publications, document structures, source flakes and explicitly qualified fiscal facts | Source evidence and readable material remain independent of later semantic integration; acquisition, comparison, flakes and calculations have separate operations |
| `frank_rg` | Logical report sources, deliveries, source file assessment, naming, archive selection and cleanup | Supplier reporting dates, delivery metadata and exact byte revisions remain distinct; workbook interpretation and calculations are explicit gaps |
| `fns.legal_entities_1yur` | Legal entities by status, legal form and published geographic unit | Dated snapshots and historically changing columns require explicit epoch mappings |
| `fns.sme_register` | Regional SME-register statistics | Dated regional/monthly observations retain published identities and measures |

The exact operation inventory comes from `domain_registration_inventory()`.
A `_registration.py` declares an actual registration boundary; ordinary package
nesting does not create one. Each logical operation ID has one registered owner
across its versions. Handler and definition modules can live in functional
subpackages without introducing additional registered owners.

For CBR, operation namespaces such as `cbr.forms`, `cbr.industries.0105a`,
`cbr.escrow` and `cbr.service_network` are callable groupings under `cbr`.
Publication families such as `cbr.reporting_forms` and `cbr.project_finance`
classify logical sources. Neither set replaces the root ownership identity.

## 2. CBR functional owners

The CBR domain root holds `REGISTRY_*.yaml` declarations for logical publication
families and one `_registration.py`. Registry declarations identify sources and
reviewed profile references. Source routes, physical layouts, mappings, models
and output profiles have distinct implementation owners.

| Functional owner under `stratbox.domains.cbr` | Responsibility | Boundary kept explicit |
| --- | --- | --- |
| `publications` | Logical source catalog, acquisition profiles, official routes, issue/asset selection and acquisition evidence | A constructed URL is a route, while an evidenced publication link is source discovery |
| `tables` | Workbook cells, DBF members, source-specific parsers, physical schemas, literal representations, source projections and selected source histories | Source-local structure and source dates remain available before semantic mapping |
| `integration` | Period, metric, subject and geography alignment; integrated observation datasets and version vectors | Shared identity requires an admitted mapping, and missing interpretation remains qualified |
| `analytics` | Financial-model input admission, formulas, count changes, shares, APK and SORS methods | Calculation scope and required inputs are independent of presentation selection |
| `products` | Prepared views, presentation profiles, ordered tables and file renderers | Rendering can start from a retained prepared view without reacquiring or recalculating data |
| `operations` | Typed definitions, execution handlers, explicit compositions, registrations and source/family catalog bindings | Executable registration remains the sole operation registry; profile bindings qualify existing operations |

These boundaries follow the same separation between root declarations,
functional implementation and callable operations used by Minfin and Frank RG.
They do not imply that those publishers have identical extraction or analytical
coverage.

The `operations/<segment>/registration.py` modules contribute references to the
single CBR root registration. They are assembly modules for functional segments,
not independent domain registrations. Definitions remain inspectable without
loading their executable handlers or optional analytical engines.

## 3. Publication groups preserve their own meaning

| CBR source scope | Implemented route | Material qualification |
| --- | --- | --- |
| The 44 series with `cbr.workbook.flake.v1` | Complete worksheet-cell extraction, readable source JSONL, validation/comparison, flake replay, qualified statistical alignment, change/share calculations, prepared views and CSV/XLSX rendering | Source table variants retain period, quantity, dimensions and unit policy; ambiguous periods, units or identities require explicit bindings or diagnostics |
| Reporting forms `101`, `102`, `123`, `135`, `802`, `805` | All-member DBF flakes, reviewed source projections, semantic observations, prepared financial-model inputs, calculation, prepared views and workbook products | Model admission checks source namespaces, complete measure channels, exact unit/scale, layout edition, periods and formula axes |
| Reporting forms `134`, `803` | All-member extraction, source reading/comparison, typed flake replay and CSV collections | Source preservation is implemented; reviewed projection, semantic alignment and financial models remain unavailable |
| Industry debt `debt_0105a` | Reviewed source flakes, integrated streams, APK calculations, pivots, snapshots and rendering | Stock at the reported date; six reviewed physical sheets |
| Industry issuance `issuance_0104a` | Independent source flakes, integrated streams, APK calculations, pivots, snapshots and rendering | Monthly flow with a distinct report date and observation interval; three reviewed physical sheets |
| Escrow/project-finance statistics | Reviewed regional workbook extraction, metric alignment, integrated data, prepared views and separate workbook rendering | Average and weighted rates retain different identities; historical HTML has an original-preservation scope until a parser is reviewed |
| Bank/region office counts | HTML capture, source release/history, explicit identity alignment, comparable count changes and prepared CSV/XLSX products | Capture date and known official state date remain distinct; capture change alone cannot establish a new official issue |
| Territorial office counts | Dated XLSX blocks, explicit candidate selection, source history, count alignment/calculation and products | Published territory labels, missing formula caches, selected fragments and unresolved fields remain qualified |

The generic workbook route preserves all physical source cells before choosing
statistical rows or model inputs. Successful extraction does not establish that
all cells have an admitted economic meaning. Alignment retains exact source
versions and diagnostics; later calculation requires compatible observations.
Published totals remain available even when a separate calculation derives a
sum or ratio.

Forms retain `REGN` and `REGN_GKO` as credit-institution and banking-group
namespaces. Form `102` requires an explicitly supplied interval. Financial
calculations can start from retained aligned observations using
`cbr.forms.prepare_model_inputs` and `cbr.forms.calculate`; the source-projection
`build_data` operation explicitly composes alignment, preparation and the same
calculator. Default subject selection includes all admitted registrations.

Source history packs explicitly selected issues or captures. It does not infer
publisher-wide historical completeness or silently select a competing revision.
Integrated datasets separately carry semantic definitions and the exact input
version vector. A prepared view is another independent value with its own
selection and evidence.

## 4. Industry models and SORS have separate responsibilities

`tables/corporate_lending/industry` owns shared physical industry/geographic
layout rules and source-flake contracts. Debt and issuance retain their own
reviewed parsing and report-period rules. `integration/corporate_lending` owns
aligned industry streams; `analytics/corporate_lending/industry` owns APK
requirements and arithmetic; `products/corporate_lending` owns selected pivots
and file representations.

Sharing a reviewed industry or geography profile does not make stock and flow
interchangeable. A publication revision with different codes, geography or
measurement definitions requires a reviewed profile and explicit admission.
Source selection controls materialization while full required-input validation
remains independent.

SORS is an analytical method under `analytics/corporate_lending/sors`. Its
versioned dependency contract names required publications, an optional
validation history and the compatible reporting step. Preparation creates a
complete model bundle; restoration consumes that bundle, and view rendering
consumes prepared products. A narrow output request does not narrow the
constraint inputs. Restored values remain derived estimates with explicit
feasibility, rounding and evidence semantics.

The `cbr.describe_family` operation, called with
`DescribeFamilyRequest("cbr.corporate_lending")`, exposes method dependencies
separately from ordinary single-publication source routes.

## 5. Source-scoped coverage and portable continuation

Use `cbr.describe_source` for a selected `series_id`, optional format, table ID
and edition. A source description exposes table variants, schemas, profile and
method editions, exact operation keys, parameters, qualifications, stage
coverage, neutral delegated operations and handoffs. `cbr.describe_family`
returns per-source descriptions and stage membership sets instead of reducing a
heterogeneous family to a single success flag.

Owner-level `operation_catalog().coverage("cbr")` answers whether the domain
contains implementations or delegated operations for a stage. It does not prove
that every CBR source supports that stage. Source cards therefore continue to
report forms `134` and `803` as missing semantic/model operations while the
same root owner implements those stages for other forms.

Direct handoffs identify compatible port shapes. Collection handoffs require an
explicit tuple of selected admitted values. Both still require correct period,
unit, identity, coverage and runtime conditions. A scoped source card does not
execute a handler or authorize a side effect.

Original preservation, typed dataset ingestion and artifact saving use neutral
storage operations. The destination belongs to the caller. A source archive,
a flake, integrated observations and a presentation workbook keep different
roles even if they are stored on the same network drive. A retained dataset
reference permits a later process to restore the appropriate semantic boundary
without reconstructing a live Python execution environment.

## 6. Functional invariants and acceptance

1. Originals, source extracts, integrated observations, derived calculations and
   presentation products retain distinct identities and methods.
2. Published totals and published adjusted-growth series remain source values;
   calculated sums or changes have independent method identities.
3. Reporting dates, capture dates, official state dates and observation intervals
   retain their economic meanings through persistence and replay.
4. Source geography and subject labels survive explicit canonical mappings;
   unresolved identities remain qualified.
5. Full required-input validation precedes selective output materialization.
6. Source file, member, sheet, cell or record evidence remains available at each
   admitted transformation boundary.
7. Missing inputs, unreviewed layouts, partial decoding and ambiguous selection
   produce explicit diagnostics, partial values or rejected admission.
8. Execution effects require the declared operation and selected infrastructure;
   catalog inspection and route planning are separate from those effects.

Acceptance uses the actual executable registry and relevant source, semantic,
replay and presentation tests. Import-direction checks protect the functional
boundaries; release-integrity checks verify that packaged resources and exact
registrations remain resolvable. The local release check additionally validates
wheel/sdist contents and isolated resolution when its dependencies are present.
No fixed owner count or operation count is an architectural ceiling.

Related maintained interfaces are described in [processing operation discovery](../current-how/processing-operation-catalog.md),
[CBR processing routes](../current-how/cbr-data-pipeline.md),
[reporting forms](../current-how/cbr-reporting-forms.md) and
[office-network publications](../current-how/cbr-service-network.md).
