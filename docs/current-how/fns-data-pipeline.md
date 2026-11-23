# FNS: complete evidence and independently retained processing stages

The FNS domain has one operation registration and two publication families:
`fns.sme` for the SME register and `fns.legal_entities` for source series
`fns.1yur`. Its family registries, publication access, physical tables,
integration, calculations and products have separate owners.

## Processing contract

| Boundary | SME register | Form 1-YUR | Independent continuation |
| --- | --- | --- | --- |
| Original | Complete JSON response bytes | Exact XLS/XLSX or ZIP/RAR asset bytes | `source.save_original` / `source.read_original` |
| Full flake | Every record, every field, order, JSON kind and literal value token | All admitted workbook members, sheets and decoder-visible cells; member inventory | `extract`, `flake_snapshot`, `read_flake_snapshot` |
| Source checks | Dates, levels, count types, duplicate identities and reported arithmetic | Reviewed Part I structure, geographic coverage, legal kinds and orientation cross-checks | `validate`, `compare_flakes`, `readable` |
| Reported projection | All present reviewed counters at country, federal-district and subject levels | Selected historical indicators with printed source codes and cell coordinates | `project`, `projection_snapshot`, `read_projection_snapshot` |
| Integrated dataset | Nine reviewed stock-counter aliases | Dated identity-only construct and legal-kind mappings | `align`, `dataset_snapshot`, `read_dataset_snapshot` |
| Calculation | Net stock changes and explicit stock shares | The same operations for qualified stock constructs | `calculate_changes`, `calculate_shares`, `calculation_snapshot`, `read_calculation_snapshot` |
| Prepared view | Explicit metric, subject, period and dimension selection | The same selection with source qualifications intact | `view`, `view_snapshot`, `read_view_snapshot` |
| Representation | CSV, JSON, JSONL or XLSX | CSV, JSON, JSONL or XLSX | `render` or `render_artifact` |

These boundaries do not prescribe a storage location. Original storage,
logical dataset storage and file artifacts are independently selectable. A
consumer can retain originals before extraction, save a flake for later
interpretation, save integrated data without rendering a workbook, or render a
previously retained view without opening the original file.

Snapshot encoders use the `encode` technical function; their readers use
`replay`. Neither operation implies ingestion, calculation or another source
extraction. Ingestion occurs when the neutral dataset writer receives a
snapshot and a selected adapter.

Each encoder exposes a precise `snapshot` port for its source family and layer,
plus a generic `dataset_snapshot` port for neutral storage. The precise port's
contract equals the actual `DatasetSnapshot.manifest.contract`. Replay accepts
the exact wrapper contract. A live dataset, another family's snapshot, another
layer's snapshot or an unclassified generic snapshot cannot masquerade as the
required wrapper in declarative handoffs.

## Offline SME route

```python
from datetime import date

from stratbox.shared.evidence import SourcePayload
from stratbox.domains.fns.operations import sme


def require_value(result):
    if result.outcome != "succeeded":
        raise RuntimeError([item.code for item in result.diagnostics])
    return result.value


release = sme.ReleaseContext(
    series_id="fns.sme",
    issue_id="2026-11-10",
    observation_date=date(2026, 11, 10),
)
# response_bytes is an already acquired original response.
flake = require_value(sme.extract(sme.ExtractRequest(
    SourcePayload(response_bytes, "application/json"), release,
)))
report = require_value(sme.validate(sme.FlakeRequest(flake)))
projection = require_value(sme.project(sme.FlakeRequest(flake)))
dataset = require_value(sme.align(sme.ProjectionRequest(projection)))
view = require_value(sme.view(sme.ViewRequest(
    dataset,
    metric_ids=("total", "ul_total", "ip_total"),
    dimensions=(("geographic_level", "0"),),
)))
csv_file = require_value(sme.render(sme.RenderRequest(view, "csv")))
```

`validate` returns a report even when the reviewed source profile fails.
`report.valid` distinguishes errors from warnings. Raw extraction succeeds for
valid JSON objects even if the declared reporting date or a numeric construct
later fails domain validation. This makes the original evidence inspectable
without presenting invalid numbers as integrated facts.

The metric aliases are:

| Source field | Integrated metric | Meaning |
| --- | --- | --- |
| `cnt_total` | `total` | All published SME subjects |
| `cnt_ul_total` | `ul_total` | Legal entities |
| `cnt_ip_total` | `ip_total` | Individual entrepreneurs |
| `cnt_ul_micro`, `cnt_ul_mini`, `cnt_ul_normal` | `ul_micro`, `ul_small`, `ul_medium` | Legal entities by size |
| `cnt_ip_micro`, `cnt_ip_mini`, `cnt_ip_normal` | `ip_micro`, `ip_small`, `ip_medium` | Individual entrepreneurs by size |

Their unit is `count`, scale is exactly one, quantity kind is `stock`, and the
definition version identifies the reviewed mapping. Source identifiers remain
in `fns.ssrf`, `fns.sme.federal_district` and `fns.sme.country`. A label
diagnostic does not change a geographic identifier.

The source `stat_date` establishes the observation date. `issue_id` identifies
the publication issue, `published_on` records a known publication date, and
`captured_at` records the actual timezone-aware acquisition or supplied capture
timestamp. `capture_full` obtains its capture timestamp from the acquisition
receipt. Missing publication metadata stays unspecified.

## Form 1-YUR: physical extraction precedes historical interpretation

Use the same contracts through
`stratbox.domains.fns.operations.legal_entities` and a release context with
`series_id="fns.1yur"`. The reported projection requires a reviewed first-of-month
reference date from January 2012 onward.

The physical flake is a workbook bundle. An archive's member inventory records
each member's name, exact identity and disposition. All admitted workbooks are
decoded before the Part I selector runs. A valid Part II workbook is retained
even though the current economic projection uses Part I. Unreadable workbook
members are qualified explicitly; non-workbook members remain identifiable in
the original archive. A workbook-only Part II archive can therefore produce a
physical flake while its Part I projection returns a qualified failure.

The shared physical reader retains exact OOXML numeric tokens, cached values,
formula expressions, number formats, merged ranges and sheet coordinates.
Legacy BIFF decoding retains exact decoded binary numeric values and marks its
evidence level. Its decoder does not expose formula expressions. XLSB
decoder limitations are carried as qualifications. No formula is evaluated,
and external workbook relations are not followed.

The historical selector consumes a sparse adapter over the retained cells.
It never needs the original binary workbook during replay. Its reviewed
cross-checks cover legal-kind sheets, transposed geographic controls,
geographic order, source national-versus-territorial differences and overlapping
territory codes. Source inconsistencies remain diagnostics rather than being
silently reconciled.

The projection retains printed field identities such as `c01_1130`. Each
observation identifies the member, legal-kind worksheet and cell coordinate.
Unselected indicators, incomplete legal-kind sheets and other workbooks receive
explicit dispositions. The reviewed June 2019 release may project the one
complete all-entities category while retaining all 32 incomplete category sheets
in the physical flake. That exception is restricted to the reviewed date and
the reviewed missing-territory pattern.

Alignment then applies epochs A, B, C1, C2 and C3 from
`integration/legal_entities/mapping.py`. The mapping is identity-only. Its
version and content hash participate in lineage. Categories lacking a reviewed
identity alias remain in the source projection and flake; the integrated
dataset records their omission. The epoch-B LLC-excluding-additional-liability
category is not treated as the later inclusive category.

`not_ceased` and `bankruptcy_proceedings` are reviewed stock counts.
`ceased_bankruptcy_liquidation` remains a count at the reporting date with an
explicit unresolved accumulation-basis qualifier. Neither a filename nor an
issue date turns that construct into a monthly flow.

## Retention and replay

```python
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.definitions import (
    ReadSnapshotRequest, WriteSnapshotRequest,
)
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot
from stratbox.core.storage.filestore import LocalFileStore

files = LocalFileStore(root=destination_directory)
datasets = FileDatasetStore(
    files, "datasets", provider_id="consumer.files", scope_id="fns",
)
snapshot = require_value(sme.dataset_snapshot(sme.DatasetRequest(dataset)))
reference = require_value(write_snapshot(
    WriteSnapshotRequest(snapshot), store=datasets,
)).reference
retained_snapshot = require_value(read_snapshot(
    ReadSnapshotRequest(reference), store=datasets,
))
restored_dataset = require_value(sme.read_dataset_snapshot(
    sme.SnapshotRequest(retained_snapshot),
))
```

Equivalent encoders/readers exist for flakes, projections, calculations and
views. Snapshots preserve the context, typed observations, exact values and
raw tokens, coverage dimensions, qualifications, field dispositions, method
profiles, input receipts and parent identities. Workbook snapshots keep the
shared sheet/cell partitions inside the FNS bundle. Partial component selections
are useful to a neutral query operation, but full domain replay requires the
complete declared snapshot.

Snapshot versions derive from the complete logical envelope. The same original
bytes with a different issue context, capture timestamp, map edition or
interpretation receive a different immutable version key. This avoids
overwriting or colliding with an earlier interpretation of the same source.

Each domain operation records its computation identity and admitted inputs.
Returned logical components and representations participate in output budget
accounting. Storage adds its own confirmed write receipts; parsing and rendering
alone do not imply a write.

## Calculation and presentation

`compare_flakes` compares literal source evidence for the same issue.
`compare_datasets` compares full semantic keys, including the period,
definition, scale, dimensions and perimeter. It does not infer time-series
growth from differently dated observations.

For a time comparison, use `calculate_changes(ChangesRequest(before, after,
metric_ids))`. It requires matching selected stock coverage and a later
observation date. The result is a `net_change` count with an interval and both
dataset/evidence identities. It is not a count of business births, registrations,
entries, exits or liquidations. Gaps and duplicate observations are rejected
instead of being filled with zero.

For a share, use `calculate_shares(SharesRequest(dataset, numerator_metric,
denominator_metric, numerator_dimensions, denominator_dimensions))`. The
selections must match on period, subject, perimeter, definitions and scale.
For example, SME micro legal entities divided by all legal entities can be
selected at geographic level `0`. Form 1-YUR legal-kind shares can select a
specific `legal_kind` in the numerator and `all` in the denominator. Zero
denominators produce missing observations with an explicit qualifier. Decimal
ratios use the declared 36-digit, half-even calculation profile.

`view` selects existing integrated or calculated observations while preserving
their order and evidence. `render` consumes only a prepared view. XLSX output
has an observation sheet and a context/qualification sheet. Exact numeric
representations are written as literal text to preserve arbitrary-size integers
and decimal precision. Spreadsheet formulas and hyperlinks are not introduced.

For consumer-selected file delivery, `render_artifact` and
`readable_artifact` return a `MaterialArtifact`. Pass that value to
`material.save_artifact` with a destination. Its bytes and immutable descriptor
can be independently read or transferred by the neutral material operations.
Publication policy remains with the consumer.

## Compositions and regional CSV products

`process(ProcessRequest(payload, release, format))` composes the offline route
and returns the original payload, flake, reported projection, integrated dataset,
view and file. The returned original remains independently storable.
`capture_full(CaptureFullRequest(release, url, format))` adds official
acquisition. SME acquisition uses its fixed read-only POST endpoint; 1-YUR
acquisition uses an admitted official release URL. `capture_full` retains the
acquisition receipt separately from the publication dates.

The established `parse`, `capture`, `read_representation` and `compare`
conveniences live under the new operation owners. They explicitly represent
selected regional CSV products and carry qualified subset coverage. Their
metadata classifies the compositions and product replay accordingly. Use the
full route for complete source retention, country/district coverage, original
field evidence, reusable integration and independent presentation.

The executable [offline retention example](../../examples/fns_portable_route.py)
shows how to save the original, all intermediate snapshots and the rendered
artifact through neutral adapters.
