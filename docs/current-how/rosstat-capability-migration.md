# Rosstat capability routes

Rosstat contributes commands, exact operations and reusable source scenarios to
the common catalog and executor. Each route keeps publisher acquisition,
physical evidence, reviewed interpretation, integration and products as separate
values with independent acceptance and retained replay.

Verified publisher layouts cover the eleven-indicator KEP2 selection, municipal
population bulletins for 2022/2023/2024 and the three-sheet regional industrial
index workbooks in the June/August 2026 regional archives. Other regional tables
and Russia report tables use an explicit reviewed profile tied to their exact
original. The automated verification corpus contains publisher-cell excerpts
with pinned original identities and separately identified deterministic cases.

## 1. Source interpretation and supported editions

| Source | Supplied-material route | Interpretation scope |
| --- | --- | --- |
| Short-term indicators | `rosstat.scenario.kep2_extract` / `rosstat.scenario.kep2_product` | Eleven named indicators, source annual/quarterly/monthly periods, literal tokens, units, notes and explicit row decisions. |
| Municipal population | `rosstat.scenario.population_extract` / `rosstat.scenario.population_product` |2022/2023 names-only table layouts;2024 TERSON-MO codes; total, urban and rural population at 1 January. |
| Regional socioeconomic archives | `rosstat.scenario.regional_industrial_extract` / `rosstat.scenario.regional_industrial_product` | Explicit industrial-index member, three reviewed index bases, June/August 2026 archive editions. |
| Other reviewed regional members | `rosstat.scenario.regional_workbook_extract` / `rosstat.scenario.regional_document_extract` and corresponding product scenarios | Explicit member name plus an exact-original reviewed cell profile; document members also receive a reviewed text-region layout. |
| Russia socioeconomic report | `rosstat.scenario.document_extract` / `rosstat.scenario.document_product` | Ordered physical PDF evidence followed by explicitly reviewed table regions and cell semantics. Real publisher PDF geometry remains outside the certified built-in layout scope. |

The source recipes `source.extract` and `source.product` select these routes
through source/representation metadata. The regional industrial recipe also
requires `table_id="industrial_production"`. Archive routes require an explicit
member name. `source.original` acquires a selected asset; `source.capture` adds an
explicit preservation obligation.

## 2. Population geography and source periods

The population parser reads the stock date from both the bulletin title and the
municipal table heading. The annual issue must match that date. Total, urban and
rural population remain separate count measures.

The 2022/2023 source tables supply names and row membership. Their source-native
geography identifies an annual source row. The 2024 table supplies TERSON-MO
codes, including repeated or annotated codes in the actual source. The flake
retains each code, literal name, source row and dated publisher territorial
edition. Independent perimeters retain repeated source codes as separate facts.
Canonical municipal codes and comparisons across territorial editions require
an explicit reviewed crosswalk. Aggregating parent and descendant source rows
requires a separately declared selection and overlap policy.

Regional industrial indices retain monthly year-on-year, year-to-date
year-on-year and previous-month comparison bases. January-to-February has a
January 1 start; a February monthly observation has a February 1 start. Published
indices remain reported values. `rosstat.analytics.derive_index_growth` creates
separate derived observations by subtracting 100 from the published percent
index. Source footnotes, including the change of industrial weights to the 2023
base, stay attached to the interpreted observations.

## 3. Command graphs and independent replay

`rosstat.publications.discover` consumes an explicitly supplied publisher page.
`rosstat.scenario.discover` separately acquires that page and then qualifies the
issue/asset inventory. Asset acquisition exposes admission, transfer and envelope
verification as separate commands. Preservation uses a bounded verified transfer
with its own storage receipt and effect state.

Archive inspection, member extraction, member selection and physical decoding
are separate commands. The selected physical value carries the original
container identity and exact member name. Workbook/document mapping has exact
physical contracts and an explicit interpretation boundary.

Workbook, document, source-flake, integrated-dataset and view snapshots preserve
their semantic roles, periods, source uses, statuses, notes and qualifications.
Their corresponding `read_*` operations replay retained values independently of
network access or the original decoder. `rosstat.integration.ingest_dataset`
encodes the integrated dataset and invokes the selected dataset writer through
an explicit effectful command.

`rosstat.scenario.kep2_monthly` accepts a retained integrated dataset and prepares
its monthly view and XLSX product. Annual and quarterly source values stay in
the source flake and integrated dataset. A supplied accepted source flake or
view cuts earlier work from the selected output closure.

## 4. Direct calls and source goals

```python
from stratbox.sdk import StrategyBox
from stratbox.shared.evidence import SourcePayload

with StrategyBox() as box:
    plan = box.prepare_goal(
        "source.extract",
        selection={
            "source_id": "rosstat.short_term_indicators",
            "representation": "xlsx",
        },
        inputs={"payload": SourcePayload(workbook_bytes)},
        parameters={"issue_id": "2026-08", "asset_id": "main_workbook"},
    )
    result = box.run(plan)
    source_flake = result.output("flake")
```

For bounded population extraction from a retained physical workbook, call
`rosstat.tables.extract_population` with `selected_rows`. For regional industrial
indices, call `rosstat.tables.extract_regional_industrial_indices` with explicit
`selected_rows` and `selected_years`. An empty selection requests the full
reviewed table scope. Each selected scope has its own coverage description;
complete processing of a selected table remains a different claim from complete
publisher history.

The saved/rendered data keep source absence and unresolved tokens visible.
Unsupported editions, changed period headers, an unreviewed code system and
inconsistent source dates produce addressed diagnostics at the interpretation
boundary. Exact-original reviewed profiles remain the extension route for
additional publisher layouts.
