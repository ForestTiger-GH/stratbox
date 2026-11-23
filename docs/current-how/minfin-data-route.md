# Minfin source operations

Minfin owns logical statistical series, publisher recognition, source-cell
extraction, source-local flake cleaning, explicit integration, headline calculations
and prepared products. The core owns
execution, provider selection, storage, archive creation and data handoff.

## Source declarations and acquisition

Root `REGISTRY_*.yaml` files use `stratbox.minfin.registry.v3`. They contain
logical identities, frequency/basis and registered profile IDs. Physical URLs,
paths and filenames are outside these records. Typed acquisition profiles in
[publications/profiles.py](../../src/stratbox/domains/minfin/publications/profiles.py) hold convenient official
landing-page defaults. `DiscoverRequest.page_url` overrides the default;
`DiscoverRequest.index` supplies already acquired HTML. A supplied input is
used exclusively, including when its content is invalid.

`discover`, `acquire` and `capture` accept an HTTP `ProviderSelection` alongside
an `ExecutionContext`. Offline `extract` accepts the same `SourcePayload`
obtained through any admitted source adapter. Domain parsing and economic rules
are independent of whether the bytes came from HTTPS, a disk or a retained
material reference. Publication index coverage remains unknown.

## Complete flake replay and database snapshots

`build_source_flake` returns a typed `FlakeTable`. `serialize_source_flake` and
`read_source_flake` provide a complete versioned JSON interchange preserving
original byte identity, source coordinates, period headers, exact value strings,
nulls, economic basis, method version, per-row units/scales/bases and publication
context. Version 2 codecs preserve these fields as an inseparable domain value. `render_source_flake`
exports a readable CSV; the JSON codec restores the complete typed value.
Source-cell extracts have the separate `serialize_extract`/`read_representation`
pair. Representations can be retained through the core material operations in
any supported store.

`build_flake_snapshot` exposes the same flake as a logical dataset with typed
metadata, columns and rows. `read_flake_snapshot` validates all three components
and restores the original domain value. The generic dataset reader/writer can
use an application adapter or an immutable file-backed snapshot without changing
headline calculations. Selected components remain partial and cannot be decoded
as a complete flake. Exact nullable text values are preserved without automatic
numeric conversion.

The [table contracts](../../src/stratbox/domains/minfin/tables/contracts.py) and [operation definitions](../../src/stratbox/domains/minfin/operations/definitions.py)
are the public semantic owners. [Profile binding](../../src/stratbox/domains/minfin/operations/bindings.py) validates
registered series, publisher rules, economic basis and calculation methods.
Every table transformation records its actual canonical typed input, parameters
and output identity. Changed values or changed original evidence produce
separate computation keys even when a CSV export happens to be identical.

```python
from stratbox.domains.minfin import (
    ExtractRequest, BuildFlakeRequest, SerializeFlakeRequest, ReadFlakeRequest,
    SummaryRequest, extract, build_source_flake, serialize_source_flake,
    read_source_flake, calculate_headlines,
)

# payload is a SourcePayload supplied by the chosen acquisition operation.
raw = extract(ExtractRequest("minfin.fedbud", payload, "xlsx"))
assert raw.outcome == "succeeded", raw.diagnostics
flake = build_source_flake(BuildFlakeRequest(raw.value, payload.source_id))
assert flake.outcome == "succeeded", flake.diagnostics
encoded = serialize_source_flake(SerializeFlakeRequest(flake.value))
assert encoded.outcome == "succeeded", encoded.diagnostics
restored = read_source_flake(ReadFlakeRequest(encoded.value))
assert restored.outcome == "succeeded", restored.diagnostics
summary = calculate_headlines(SummaryRequest(restored.value))
```

## Economic and consumer boundaries

Monthly and quarterly budget figures retain their cumulative YTD basis; annual
figures remain annual. NWF tables retain mixed row semantics, and the headline
profile derives liquid assets from its specifically reviewed rows. Publication
dates never replace observation periods. Historical flake methods survive
replay; calculation admission checks the registered method, frequency, basis, declared
unit and the monetary scale of each required row. The current flake methods use
edition 2; old processing checkpoints therefore request reprocessing. Headline
calculator method edition 2 retains exact stock differences and strict unit admission.

Caller-owned checkpoints distinguish publisher markers, exact material identity
and processing method. They are persisted after confirmed storage. Source
monitoring, cross-source mapping policy, scheduling, notification delivery
and application database lifecycle belong to their consumers. The three
historical NWF document series remain outside the workbook flake route.


## Semantic owners and independent operations

| Owner | Responsibility | Independent operations |
| --- | --- | --- |
| `publications` | Source registry, release markers, asset identity and acquisition | discover, inspect, acquire, plan updates |
| `documents` | Ordered PDF/DOCX blocks and complete release context | extract document, document snapshot, read document, render document |
| `tables` | Exact workbook cells and source-local wide flakes | extract, validate, compare, JSON encode/replay, build flake, flake snapshot/replay |
| `integration` | Explicit units, metric definitions, perimeters and reporting periods | integrate, observation snapshot, read observations |
| `analytics` | Reviewed headline calculations and durable results | summarize, summary snapshot, read summary |
| `products` | Prepared selections of calculated values and their comparison qualifications | prepare view, view snapshot, read view, render view |
| `operations` | Runtime admission, evidence, limits and composition | One registered owner and per-series source cards |

Encoding and replay are classified independently of processing stages. A replay
operation does not claim that it reran extraction or integration. Storage is an
optional consumer-selected operation: `dataset.write_snapshot` and
`dataset.read_snapshot` consume the same complete snapshots across supported
logical stores. `material.save_artifact`/`material.read_artifact` retain rendered
representations and their descriptors.

### Integration is an explicit economic boundary

`IntegrateRequest(flake, dataset_id, release_id, bindings=())` returns the common
`ObservationBatch`. With no supplied bindings, the reviewed mappings cover the
three budget headlines and two NWF source rows (total and other permitted
assets). Other rows require `RowBinding` values specifying the metric definition,
unit, scale, subject, perimeter and value basis. The full source flake always
remains available separately; a selected economic mapping never claims to
interpret every source row. Caller bindings for ratios, indices and counts also provide explicit
`periods` mappings from each source period ID to a typed `PeriodRef`, so their
point-in-time or interval meaning is chosen explicitly.

Monthly and quarterly `ytd` values become intervals from January 1 through the
source period end. `annual` values cover the full year; `period_flow` uses the
individual month or quarter, and `stock` uses a point at period end. A NWF row can
therefore carry a flow or a different currency without inheriting the workbook's
headline stock interpretation. Null, empty, dash and reported-zero values remain
qualified. Numeric values use `Decimal`; publication dates remain release
metadata.

```python
from stratbox.domains import minfin

integrated = minfin.integrate(minfin.IntegrateRequest(
    restored.value, "minfin.budget.observations", "release-2026-10",
))
assert integrated.outcome == "succeeded", integrated.diagnostics
retained = minfin.build_observation_snapshot(
    minfin.ObservationSnapshotRequest(integrated.value)
)
```

### Calculations and views are independently replayable

`build_summary_snapshot` stores the result values, prior-year comparison status,
calculator profile/version, exact source-flake identity and publisher context.
`read_summary` restores those values without consulting today's source workbook
or calculator. `prepare_view` accepts that admitted result; its prepared view
contains current values, prior values and qualified growth values. A
`build_view_snapshot`/`read_view` round trip preserves the complete selection and
lineage. `render_view` emits CSV, JSON or JSONL from the prepared view.

### Documents and source evidence

`PublicationContext` retains the logical series, issue and asset, publisher
publication/modification dates, document ID and source URL. Capture supplies it
from the observed asset; offline callers can supply it explicitly. Source-cell
and flake replay retain the context verbatim. OOXML reading preserves the exact
numeric token, merged ranges, cached formula evidence, indentation and formula
attributes. Formulas are retained as evidence and are never executed.

`extract_document` requires explicit publication context and emits ordered
PDF/DOCX evidence. `build_document_snapshot` and `read_document` retain both
ordered blocks and all publisher context; `render_document` emits readable
JSONL. PDF text and DOCX main-body coverage remain qualified. Legacy DOC assets
are retainable originals; the document decoder admits PDF/DOCX and does not
claim a legacy DOC conversion.

The common source catalog exposes all thirteen series and binds the exact
applicable operations. Historical document series are distinct from the ten
workbook series, and conditional document/semantic availability is explicit.
