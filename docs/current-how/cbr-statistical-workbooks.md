# CBR statistical workbooks: source cells, qualified observations and retained views

The CBR statistical workbook route preserves an admitted XLSX original, extracts its physical cells, aligns reviewed table layouts into qualified observations, and prepares independently retainable views. Its default output describes published source measures. Canonical subject, geography and metric equivalence requires explicit mappings and a stated analytical perimeter.

The publication and operation catalogs define the available source scope. A successfully decoded workbook establishes the contents of that supplied original; it does not establish a complete publication history or make an unreviewed table interpretable. See the [CBR publication pipeline](cbr-data-pipeline.md) for discovery, acquisition, source revisions and destinations, and the [executable statistics example](../../examples/cbr_statistics_flow.py) for a local route through retained values.

## 1. Source families and table variants

The [source table registry](../../src/stratbox/domains/cbr/tables/statistics/profiles.py) binds 44 logical XLSX profiles to family-owned table declarations. A profile contains a series identity, version, edition, worksheet patterns, period basis, quantity kind, retained dimensions and explicit interpretation qualifications. Its variants identify published table meanings rather than output worksheet styling.

| Family | Logical profiles | Distinctions retained during interpretation |
| --- | ---: | --- |
| Corporate lending | 15 | Issuance and debt; activity and geography; denomination; SME perimeter; borrower counts; interest-rate structure; district layouts |
| Household lending | 6 | Mortgage issuance, debt, acquired claims, overdue balances, construction purpose, counts, duration and rates |
| Funding | 9 | Depositor and client perimeter, geography, denomination, escrow inclusion and budget funds |
| Household finance | 2 | Balances and transactions, asset and liability sections, financial instrument and seasonal adjustment |
| Monetary statistics | 6 | Central bank, credit institutions and consolidated banking system; stocks, transactions and published growth |
| Banking sector structure | 1 | Assets, liabilities, capital, denomination and maturity groups |
| Securities | 1 | Nominal and market valuation; monthly and quarterly publication tables |
| External debt | 3 | Instrument, sector, denomination, maturity and overlapping historical worksheet editions |
| Exchange rates | 1 | Nominal quotes, period averages, published growth indices, reference periods and trade weights |

The generic matrix interpreter handles the reviewed rolling time-series layouts. The two dated federal-district corporate workbooks also have physical workbook profiles, while their district, activity and single-release period semantics belong to the [corporate source-observation parser](../../src/stratbox/domains/cbr/tables/corporate_lending/observations.py). That source-specific route is exposed as `cbr.corporate_lending.extract_observations@1`. A worksheet name matching a generic profile does not replace its specialized dimensional interpretation. Regional industry tables, reporting forms, project finance and service-network publications have their own functional routes described in the domain pipeline.

`cbr.describe_source@1` exposes the selected source, supported and original-only formats, table variants, exact operation keys, ports, profile editions, qualifications and applicable storage handoffs. `cbr.describe_family@1` reports source-level gaps and separately scoped analytical methods. A family capability never grants coverage to every source or every historical layout in that family.

## 2. Independent operations and retained values

All operations in this table have contract version 1. Their declarations are owned by the [statistics operation catalog](../../src/stratbox/domains/cbr/operations/statistics/definitions.py).

| Operation | Input and resulting responsibility |
| --- | --- |
| `cbr.tables.extract` | An identified XLSX original becomes a `WorkbookFlake` with all admitted worksheets and physical cells. |
| `cbr.tables.validate` | A flake produces structural, recognized-layout, formula-cache and source-cell diagnostics. |
| `cbr.tables.compare` | Two flakes of the same series and logical asset produce source-cell and byte-revision differences. |
| `cbr.tables.readable` | A flake produces source-readable JSONL independently of semantic integration. |
| `cbr.tables.flake_snapshot` / `read_flake_snapshot` | Encode and restore the source-local workbook value. |
| `cbr.statistics.align` | An explicitly assembled collection of flakes becomes a `StatisticsDataset`, optionally using row and period bindings. |
| `cbr.statistics.calculate_change` | Calculate a selected absolute change or percentage growth from compatible observations. |
| `cbr.statistics.calculate_share` | Calculate an explicitly selected numerator/denominator relationship. |
| `cbr.statistics.dataset_snapshot` / `read_dataset_snapshot` | Encode and restore the integrated or calculated dataset. |
| `cbr.statistics.build_view` | Select an integrated or calculated dataset into a prepared presentation value. |
| `cbr.statistics.view_snapshot` / `read_view_snapshot` | Retain and restore that prepared view. |
| `cbr.statistics.render_view` | Render the prepared view alone as CSV or XLSX. |

Discovery and acquisition belong to publication operations. Storage belongs to neutral operations such as `source.save_original`, `dataset.write_snapshot` and `material.save_artifact`. Source cards also describe the typed collector-member and manifest handoff to `material.archive`. These contracts allow a caller to select an external storage provider without introducing storage policy into a parser, mapping or renderer.

## 3. Source evidence and exact values

The [physical workbook reader](../../src/stratbox/core/formats/spreadsheets/cells.py) retains worksheet names, dimensions, merged ranges, coordinates, source cell types, numeric lexemes, formulas, cached results, number formats and indentation. Finite source numeric values remain integers or `Decimal` values. The original XLSX bytes remain the authority for workbook features outside this cell representation.

Formula expressions are retained as source evidence and are never evaluated during extraction. A missing cached result remains missing. Unknown worksheet variants stay in the flake and source-readable output, even when alignment excludes them with a diagnostic. Workbook comparison distinguishes identical bytes, byte revisions and changes in retained source-cell evidence; a caller-supplied issue identifier remains separate from those comparisons.

During alignment, a blank, dash, unavailable marker, withheld marker and reported zero remain distinct. Recognized decimal text, including comma decimal separators, preserves its complete raw token. Annotated numeric tokens such as `28,5**` retain both the exact numeric value and the original annotation. The observation carries an annotation qualification; the source flake retains the corresponding footnotes and surrounding cells. A number beside a note or update-date label is diagnosed rather than promoted to an economic measure.

## 4. Period axes and embedded source sections

The [alignment owner](../../src/stratbox/domains/cbr/integration/statistics/alignment.py) resolves physical column axes before interpreting values. Its admitted period rules include:

- Full source dates become `as_of` periods, with trailing source annotation markers retained.
- Russian month/year labels, including `Январь 2019`, `Январь2019` and `Янв-2019`, become calendar-month intervals.
- A year header paired with month or quarter labels resolves every qualified column. Year propagation follows an explicit merged range; an empty, unmerged year cell supplies no year evidence.
- Explicit cumulative labels such as `Янв - Фев`, first-half-year and nine-month labels retain their cumulative interval.
- For a source-interval profile, an actual spreadsheet date displayed exclusively as month/year supplies a monthly interval. A full-date display preserves the point date.
- A short year label such as `дек.25**` is accepted only when the other qualified dates in the same physical axis establish one matching year. Its source label remains attached to the observation.

Repeated blocks within a worksheet have independent axes and source sections. This matters for SME borrower statistics: counts of borrowers with outstanding debt use reference dates, while counts receiving a loan during the month use intervals. Exchange-rate worksheets likewise retain separate level, average, growth and cumulative-growth sections.

An explicit monthly row label under a first-of-month reporting date can identify the preceding calendar month. A flow with only an unresolved point date retains `period_qualification=reported_date_interval_unresolved`; it does not acquire an invented interval. Dates, column positions and source periods remain separately inspectable in the retained evidence.

A `ColumnPeriodBinding` addresses a source series, worksheet and physical column. Competing adjacent axes require sufficient bindings to resolve every conflict. A column-only binding is rejected when it would overwrite different meanings in repeated blocks; that input shape cannot express a block-specific override. Missing or unrecognized period columns produce diagnostics and their unqualified values remain available in the source flake.

## 5. Measurement units, scales and source conflicts

A value keeps its published scale. For example, `120` with unit `RUB` and scale `1000000` remains the published number 120; alignment does not silently multiply it or relabel it as 120 unscaled rubles.

Unit resolution uses an explicit row unit, a qualified parent-row unit, a source section unit, or an unambiguous table unit. Currency denomination phrases such as “in rubles” do not override a published million- or billion-ruble measurement scale. A label discussing interest rates or accrued interest does not by itself declare a percentage unit. Counts, months, percentages and currency amounts retain separate units. Nominal exchange-rate quotes retain their source quote-unit meaning; published growth indices retain their percentage unit and distinct index identity.

A table may declare a specific unit anchor in its profile. The three Balance ODC detail variants—loans, deposits included in broad money, and other deposits—use cell `A2`, where the publisher states their unit in the first data-row label. The anchor is visible in the source card. A missing anchor declaration in the supplied worksheet is diagnosed; the previous workbook's unit is never carried forward silently.

Multiple contradictory header units produce `source_unspecified` and a diagnostic unless an explicit row measurement resolves that row. A contradictory source row can produce `source_conflicting`. Examples include the construction-purpose mortgage row that declares counts under a monetary-volume parent, and the liabilities worksheet whose source header declares both RUB and USD. These observations retain the published value and source evidence. A caller must provide a reviewed interpretation before using them in qualified calculations.

An explicit `RowBinding` supplies a metric, subject, additional dimensions and optionally an analytical perimeter. When the source unit and scale are known, the binding must preserve them exactly. Unit or scale conversion requires a separately stated transformation; binding a different metric name does not perform conversion. `mapping_version` records the caller's mapping edition.

## 6. Source identity, integration scope and calculations

Default metric and subject identities are scoped by source series, logical asset, worksheet, section and row hierarchy. Identical text in two sources does not assert the same subject. Overlapping external-debt worksheets remain distinct source measures, including their shared calendar dates. Source coordinates, original-byte identity and the source-local hierarchy remain attached after mapping.

The integrated value retains the exact input-version vector: series, issue and asset, original identity, flake identity, and table-profile identity/version. Multiple releases remain available without an implicit “latest wins” policy. A calculated result retains the complete input vector, its method identity, parameters and parent integrated identity.

Published transaction and growth tables keep their own `measure_basis`. A library-computed change receives a different metric identity and computation basis. Published transactions may exclude valuation or other adjustments; subtracting two stocks therefore does not establish the same measure. Seasonal-adjustment status and source perimeter also remain explicit.

The [calculation owner](../../src/stratbox/domains/cbr/analytics/statistics/changes.py) requires compatible selected observations. Ambiguous revisions require an explicit release selection. Missing values, unresolved units, unresolved flow intervals and zero denominators do not become numeric answers. Share calculations additionally require matching subject, period, perimeter, unit, scale and an admitted additive quantity kind. Because default subjects identify individual source rows, numerator and denominator generally require explicit bindings to a common subject. Cross-source integration still needs a reviewed policy for the retained source axes; a matching label or canonical metric name alone supplies no join policy.

## 7. Qualified gaps and strict alignment

Alignment diagnostics distinguish unknown layouts, unresolved or conflicting period axes, missing unit anchors, missing or contradictory units, source notes containing values, and unsupported source-value tokens. Successfully aligned observations coexist with this evidence when `strict=False`. With `strict=True`, unresolved semantic diagnostics reject the alignment request.

A qualified fully blank physical metric row can retain blank observations. Section headings, merged label headings and explanatory footnotes remain structural evidence. Unknown geography and classifications stay in source identities until an explicit mapping is supplied. Successful source extraction and a diagnostic-free selected table remain different claims from complete historical coverage, canonical cross-source comparability or complete publication inventory.

## 8. Retained presentation and output destinations

`build_view` consumes an integrated or calculated `StatisticsDataset` and an explicit series, release or metric selection. Its prepared value contains presentation metadata, observation rows, the full input-version vector and diagnostics. It is a selected presentation with its own identity and parent dataset identity.

A restored view can be rendered without the original workbook, parser, alignment code or calculation step. XLSX rendering includes metadata, observations, inputs and diagnostics sheets. CSV rendering contains the observation table; retain the view snapshot when the complete presentation evidence is required. Numeric presentation lexemes remain text in generated spreadsheets to preserve exact digits; typed numeric values belong to the integrated snapshot.

Ratio calculations use a fixed 28-significant-digit, half-even decimal context;
absolute differences preserve every input digit within the admitted precision
bound. The host application's decimal context does not alter these results.
Source period/value annotations are evidence rather than pairing axes: computed
observations retain baseline or denominator annotations and both input evidence
references. The XLSX container uses fixed creation metadata so rendering a
retained view under the same implementation produces the same bytes.

The renderer returns a representation. Saving that representation, retaining the source-readable JSONL, ingesting a dataset snapshot, and publishing to a remote destination are separate caller-selected actions. A change to view selection, title or presentation formatting creates a presentation result while leaving the retained source flake and integrated dataset intact.
