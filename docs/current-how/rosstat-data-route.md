# Rosstat: independent data processing routes

Rosstat has one registered owner, `rosstat`, and four publication families.
Canonical source, operation and profile records live under
`stratbox/registry/rosstat`; functional Python packages separate publisher
materials, source tables, integration, calculations and products. Source cards
bind applicable operations and admission requirements to each series. Metadata
discovery imports no optional spreadsheet or document engine.

## Family routes and admission

| Publication family | Original and physical evidence | Selected source flake | Integration |
| --- | --- | --- | --- |
| `rosstat.socioeconomic_russia` | Publisher PDF; all decoded page blocks, including qualified text-extraction errors | A reviewed layout pinned to the exact PDF digest supplies line/column table regions; reviewed cell bindings then supply statistical meanings | Explicit metric, unit, scale, frequency, actual interval, geography and perimeter |
| `rosstat.socioeconomic_regions` | ZIP/RAR inventory, explicitly selected member, member digest and container lineage; workbook cells or document blocks | An exact-member reviewed coordinate profile; document text first requires reviewed structure | Explicit regional subjects, periods, units and statistical perimeters |
| `rosstat.short_term_indicators` | Unchanged XLSX; full admitted worksheet cells, exact sheet names, merges, formats, source tokens and cached formula evidence | Built-in reviewed KEP2 profile for the supplied eleven-indicator notebook; other selections use reviewed coordinate profiles | Published indices keep their percentage-of-baseline meaning; all source frequencies survive |
| `rosstat.population_municipalities` | Unchanged XLSX and full physical cell extraction | Exact-original reviewed cell profile with a stock date and geographic code edition | OKTMO/OKATO codes resolve against a supplied dated `TerritoryEdition`; statistical perimeter must match the reviewed territory |

“Reviewed profile” is an actual input contract: `ReviewedTableProfile` binds a
profile ID/version, source digest, review evidence and complete coordinate
bindings. It supplies meanings explicitly. The code does not guess a population
column from its position or turn arbitrary PDF page text into a table. A
`ReviewedDocumentLayout` retains the original text blocks and appends only
specified source regions, split using literal separators or fixed character
boundaries. Region width and bounds are validated against the exact text.

The built-in KEP2 profile was exercised against the unchanged August 2026
publication. That validation does not certify other Rosstat workbook families or
all future layouts. A changed period header, ambiguous sheet alias or ambiguous
section/marker is rejected; unresolved values and missing selected blocks produce
qualified partial source flakes that cannot pass integration.

## Material identities and storage boundaries

The route keeps these values distinct:

1. **Original**: exact `SourcePayload` bytes, identified independently from the
   publisher's series, issue and asset. `source.save_original` preserves them;
   `source.read_original` restores confirmed bytes.
2. **Physical extract**: a neutral `WorkbookExtract` or `DocumentExtract`. The
   workbook contains every admitted source cell, including hidden-column values;
   formula expressions/caches and native numeric tokens remain source evidence.
   Original bytes retain workbook features outside this structured cell contract.
3. **Selected source flake**: `RosstatSourceFlake`, with selected values, actual
   periods, source units, raw tokens, coordinates, notes and row-selection evidence.
   Its identity references the complete physical extract and original digest.
4. **Integrated dataset**: `RosstatDataset`, containing typed observations and the
   source selection context. No network, source decoder or presentation engine is
   needed to restore it.
5. **Prepared view**: a portable `ObservationView`, with selected observations and
   their evidence. It can be stored before any particular rendering is chosen.
6. **Rendered product**: CSV, JSON, JSONL or the KEP2 monthly XLSX. A
   `MaterialArtifact` retains the representation's contract, exact bytes, source
   identity and lineage alongside the file.

Workbook/document, source-flake, integrated and prepared-view snapshots are
complete `DatasetSnapshot` values. The neutral `dataset.write_snapshot` and
`dataset.read_snapshot` operations support their persistence through the selected
adapter. A partial component read is insufficient for a full domain replay.
Encoding a snapshot is a technical `encode` function; it is separate from the
storage effect. Replay operations are technical `replay` functions.

A network share, local directory or another compatible store is selected by the
caller. The same rendered bytes can be retained with `material.save_artifact` and
copied with the neutral artifact-transfer operation. Tabularium destinations and
Git publication policies are caller-owned; the parser has no hidden upload,
download, filesystem path, Colab dependency or publication side effect.

## KEP2 notebook implementation

The contents sheet has two independently read panels, A:B and E:F. Contents
labels determine source sheets. Exact worksheet names remain in provenance;
trimmed lookup is accepted only when it resolves to exactly one sheet. Section
selection uses complete reviewed titles and explicit aliases. It does not use
fuzzy worksheet matching or the notebook's ambiguous first-30-character search.

The reviewed indicator order is:

| ID | Presentation label |
| --- | --- |
| `investment` | Инвестиции в основной капитал |
| `wages` | Заработная плата |
| `construction` | Строительство |
| `freight_turnover` | Грузооборот |
| `retail` | Розничная торговля |
| `retail_food` | Продовольственная розничная торговля |
| `retail_nonfood` | Непродовольственная розничная торговля |
| `catering` | Оборот общественного питания |
| `wholesale` | Оптовая торговля |
| `paid_services` | Платные услуги |
| `agriculture` | Сельское хозяйство |

Wages resolve to the nominal accrued-wages subsection when that reviewed title
exists. Food, nonfood and catering sections can share the retail worksheet.
Freight turnover stops before cargo transportation: the presence of another
index marker farther down the sheet cannot supply a missing target block.

Three measure kinds remain separate: absolute values, the published index versus
the same period of the preceding year, and the published index versus the
preceding period. The actual August 2026 agriculture section publishes only the
year-on-year index. Its absolute and preceding-period presentation rows remain
empty, as in the notebook's full row order; no missing series is invented.

The fixed A:R layout is admitted only after checking the source annual, quarter
and twelve month headers:

| Source columns | Flake frequency | Actual interval | Notebook display anchor |
| --- | --- | --- | --- |
| B | `annual` | January 1 through December 31 | January 1 of the following year |
| C:F | `quarterly` | First through last day of the source quarter | First day of the next quarter |
| G:R | `monthly` | First through last day of the source month | First day of the next month |

The display anchor is an additional field, not a substitute observation date.
Both frequency and real interval survive source-flake and integrated replay. The
monthly product filters the integrated dataset; quarterly and annual values stay
available for other views.

Year continuation rows use the notebook's explicit `last_source_row` policy.
`duplicate_year_policy="reject"` is available when that reviewed policy is
inappropriate. Every candidate row retains its year, exact coordinates, selected
flag, reason and canonical A:R source-cell evidence **inside the source flake**,
including discarded rows. Thus an annual or quarterly value on an earlier row
remains recoverable even when the notebook's selected continuation has a blank.
The parser never averages duplicates, and dataset integration rejects duplicate
semantic observation keys even when the numerical values agree.

Missing source states remain distinct: blank, dash, ellipsis/missing,
not-applicable and unparsed. Zero remains a reported zero. Numeric and year-cell
footnotes are retained separately from numerical values. Source headers,
methodological notes, unit literals, scales, number formats, formula evidence and
raw tokens remain traceable. Decimal values preserve the source's numeric token;
the XLSX display format is a separate presentation choice. A formula lacking a
cached result is unparsed, rather than silently treated as blank or evaluated.

A published index of 105.1 remains **105.1 percent of its baseline** in the
source and integrated layers. `rosstat.analytics.derive_index_growth` explicitly
creates a separate derived 5.1 percent change, with a derived status and a named
method. This derivation does not assert equivalence to changes in nominal
absolute values or bridge methodological breaks.

## Independent operations

The operation catalog exposes 36 Rosstat operations. Significant groups are:

| Concern | Operations |
| --- | --- |
| Publication | `publications.discover`, `select`, `review_index`, `plan_updates`, `acquire`, `acquire_to_store` |
| Regional materials | `publications.inspect_archive`, `extract_members` |
| Physical workbooks | `tables.extract_workbook`, `workbook_snapshot`, `read_workbook`, `readable_workbook`, `compare_workbooks` |
| Physical documents | `tables.extract_document`, `structure_document`, `document_snapshot`, `read_document`, `readable_document` |
| Source selections | `tables.extract_kep2`, `map_reviewed_cells`, `validate_flake`, `compare_flakes`, `flake_snapshot`, `read_flake`, `readable_flake` |
| Integration and analysis | `integration.integrate`, `dataset_snapshot`, `read_dataset`; `analytics.compare_datasets`, `derive_index_growth` |
| Products | `products.prepare_view`, `prepare_kep2_monthly`, `view_snapshot`, `read_view`, `render_view`, `render_kep2_xlsx` |

Each name has the `rosstat.` prefix and contract version 1. The typed request
classes live in `operations/contracts.py`; KEP2 selection has its own
`tables/contracts.py:Kep2Request`. Operation boundaries expose qualified outcomes,
input receipts, cancellation checks and shared resource limits. Source cards mark
conditional profile requirements rather than advertising every generic decoder
as a fully reviewed statistical parser.

## Offline run and replay

Install the package with its spreadsheet extra and run the complete example:

```sh
python examples/rosstat_kep2_offline.py \
  --source /caller/source/2026-08.xlsx \
  --issue 2026-08 \
  --output-root /caller/output/rosstat
```

The example preserves the original separately, writes and rereads each of the
four snapshot types, and saves the monthly product plus its semantic descriptor.
It accepts only successful, fully admitted KEP2 source selections; partial
results require review of their diagnostics before integration. Its storage
adapter can be replaced independently of all domain parsing and calculation.

The monthly workbook contains the requested three blocks in the eleven-indicator
order, the correct “Ежемесячные показатели” title, frozen C5 panes and one-decimal
presentation. Its `Evidence` sheet retains exact numerical text, source tokens,
actual intervals, display dates, unit/scale, footnotes and source coordinates.
`Metadata` states the index and date conventions and references source identities.
Formula-looking source strings are written as literal text.

## Verification evidence and limits

The unchanged reference workbook came from the public Tabularium route
`originals/russia/authorities/rosstat/short-term-economic-indicators/2026-08.xlsx`.
Its SHA-256 is
`999b960af08ce82afc93820887979da7cb07084caea95f05e7ff7cf66270fe55`
and its size is 1,740,993 bytes. Local verification decoded 43 worksheets and
359,235 physical cells, then selected 14,637 source cells: 861 annual, 3,444
quarterly and 10,332 monthly, across eleven indicators and 31 published measure
blocks. The selected scope was complete with zero unresolved diagnostics. One
rejected candidate year row remained in the flake's row evidence; 320 selected
cells carried numeric or year-level footnotes.

The original, physical, source-flake, integrated and view identities were checked
through independent replay; the monthly XLSX was rendered from the restored view.
Synthetic regression fixtures also cover a shifted period layout, ambiguous
sheet aliases, missing markers, unknown numeric tokens, last-row decisions,
duplicate observations, explicit PDF table structure, archive membership and
lineage, dated municipal codes and changed territorial perimeters.

This is validation of that source issue and those explicit admission contracts.
Publisher-page completeness remains a separate discovery property, and reviewed
profiles for other publication layouts must supply their actual coordinates,
statistical meanings and source evidence. No full historical archive, universal
PDF table extraction or automatic geographic boundary bridge is asserted.
