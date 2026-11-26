# SORS inputs, independent commands and retained values

SORS is the coupled calculation `cbr.sors` in `domains/cbr/calculations/sors`.
The source-neutral operation `operation.constraints.restore` supplies its graph.
Domain records bind each standard command to one scientific method and immutable
settings. There is one repository release identity; source bytes, reference
material, settings and actual scientific states have content fingerprints.

## Source preparation

Each source is interpreted using its own `SeriesTarget` and
`operation.series.extract_workbook`. The regional 0105a source retains its full
six-sheet native stream. The other sources retain independent corporate source
observations with exact values, missing-cell status, original receipts and all
available periods. Source interpretation precedes mathematical model admission.

The `cbr.sors.inputs` declaration records these roles:

| Role | Publication | Required | Mathematical purpose |
| --- | --- | --- | --- |
| `regional_traditional` | 01_05_A | Yes | Regional corporate totals and legacy activity evidence |
| `national_traditional` | 01_02_A | Yes | National corporate totals and legacy activity evidence |
| `national_okved2` | 01_02_C | Yes | National corporate OKVED2 constraints |
| `federal_district_okved2` | 01_03_C | Yes | District corporate OKVED2 constraints |
| `sme_national_totals` | 01_11 | Yes | National SME portfolio constraints |
| `sme_national_okved2` | 01_11_F | Yes | National SME OKVED2 constraints |
| `sme_ie_national_okved2` | 01_11_I | Yes | National SME individual entrepreneur constraints |
| `sme_federal_district_okved2` | 01_12_A | Yes | District SME OKVED2 constraints |
| `sme_regional_totals` | 01_13_F | Yes | Regional SME totals |
| `sme_ie_regional_totals` | 01_13_I | Yes | Regional SME individual entrepreneur totals |
| `regional_totals_history` | 01_05_D | No | Validation and historical context |

`command.model.inputs` accepts a mapping from these roles to their interpreted
`SourceDataset` values, or a retained `SorsSourceBundle`. It checks one reporting
date, publication step, full portfolio scope, source structure and exact original
receipts. The native scientific schema must be available. Raw file bytes belong
to upstream decoding commands. URLs and source layouts stay in the source records.

A narrow result or optimization target keeps the full coupled input vector.
Selecting one region or indicator narrows the requested output or extrema; it
preserves every source and auxiliary constraint needed to justify the answer.

## Standard calculation route

```python
from stratbox.sdk import StrategyBox
from stratbox.capabilities.model.targets import CalculationTarget
from stratbox.domains.cbr.calculations.sors.contracts import SorsRunConfig

with StrategyBox() as box:
    outcome = box.invoke(
        'operation.constraints.restore',
        target=CalculationTarget('cbr.sors'),
        inputs={'datasets': interpreted_by_role},
        parameters={'config': SorsRunConfig('2026-07-01')},
    )
    if outcome.outcome != 'succeeded':
        raise RuntimeError(outcome.diagnostics)
    dataset = outcome.output('dataset')
```

The graph explicitly executes input admission, constraint construction, an
inner propagation/inheritance/reconciliation fixed point, compilation, global
feasibility, one optimization phase and reconciliation. An outer loop sends new
qualified optimization facts through deterministic closure and fresh global
feasibility. Final certification requires the current state and its matching
feasibility evidence. Each action is independently callable through its standard
command ID; a domain method never schedules another command.

`cbr.sors.crosswalk` is a separate coupled calculation over the retained strict
result. It binds the same standard model route to conditional scenario graphs,
closure, feasibility, extrema and robust-envelope certification. The mapping
resource fingerprint pins the actual four resource files. Proven infeasible
scenarios are reported; incomplete scenario coverage prevents full certification.

## Retention and replay

The target bindings for `command.value.encode` and `command.value.decode` retain
bundles, strict/crosswalk results, certified values, prepared views and resumable
numerical states. The bounded JSON codec has a static vocabulary of scientific
types. It preserves every DataFrame axis, dtype and scalar, open interval
endpoint, CSR array, ledger fact, setting, source receipt and qualification.
Decoded data cannot select an import path or create a solver session. Live
workbooks, Python pickles and solver handles are outside this representation.

```python
encoded = box.invoke('command.value.encode', target=CalculationTarget('cbr.sors'),
                     inputs={'value': dataset}).output('representation')
# The application can retain encoded.data in its artifact provider.
replayed = box.invoke('command.value.decode', target=CalculationTarget('cbr.sors'),
                     inputs={'representation': encoded}).output('value')
```

The generic artifact-commit and dataset-ingest commands own persistence effects.
Encoding a value does not save it or claim that its original publication exists
at a particular provider. Retained source receipts distinguish exact content
from availability. Content evidence rejects a changed retained source table.
Admission also rejects missing dependency roles and mismatched original hashes.

## Products and observability

`ProductTarget('cbr.sors.workbook')` binds `command.view.prepare` and
`command.product.render`. Preparation selects tables and pivots and produces
`View(SorsViewPack)`. Rendering consumes those exact sheets and returns an
`EncodedProduct`; it runs no mathematical model. A retained prepared view can be
rendered in another process with the original publications and solver absent.
The full source vector follows a selected-region pivot and retained view.

The common execution service journals every scientific command, scope,
iteration, resource claim and failure. Mapping and source receipts are attached
as actual command evidence. Scientific ledger rows remain part of the data;
invocation events and notification delivery belong to the common runtime.

The executable [example](../../examples/cbr_sors_restoration.py) accepts an
explicit JSON mapping of role names to local original paths, or a retained input
value. It uses the standard SDK path for source interpretation, calculation,
retention, optional crosswalk and workbook rendering.

## Validation perimeter

Synthetic regressions exercise the real HiGHS solver, all strict optimization
phases, exact compiled-state replay, conditional crosswalk, source provenance,
prepared-view rendering in a fresh process, and evidence qualification. Real
June/July source cases remain opt-in through `STRATBOX_SORS_REAL_DATA_DIR` or
`STRATBOX_SORS_REAL_20260701_DIR`; performance cases additionally require
`STRATBOX_SORS_RUN_PERFORMANCE=1`. Skipped real-data cases provide no certification
of the current publisher vintage or large-model performance.
