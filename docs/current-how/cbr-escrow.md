# Escrow publication flakes, integration and workbook replay

The escrow domain implements independent boundaries for XLSX extraction,
semantic integration, view preparation and rendering. Complete values at the
flake, integrated-dataset and prepared-view boundaries can be stored and restored
through the common logical dataset adapters. The renderer also returns a normal
material representation for a caller-selected output destination.

This route covers the supported regional XLSX layout. Historical HTML issues
are retained in discovery with an explicit unsupported extraction status and can
be acquired as originals. Their economic definitions require a separate reviewed
interpretation profile before entering the same integrated series.

Contents:

1. Publication-local extraction — exact original identity, cell tokens and status.
2. Complete snapshots — domain reconstruction after storage and a new process.
3. Integration — keys, source editions, periods and publication coverage.
4. Prepared views — explicit selection, missing values and numeric precision.
5. Calling the route — independent operations and infrastructure boundaries.
6. Limits — supported interpretation and failure behavior.

## 1. Publication-local extraction

`parse(ParseEscrowRequest(payload, source_name, as_of))` accepts supplied bytes
from any admitted input provider. The parser checks XLSX structure, identifies
the regional table, and verifies the supplied observation date against a date
encoded in the filename when both are present. A publication date is not
substituted for the observation date.

The returned `ParsedEscrowFile` is a source-local flake:

| Component | Content |
| --- | --- |
| Original identity | SHA-256 and length of the exact input workbook; optional caller source ID. |
| Publication context | Observation date, source filename, sheet, header row and interpretation method. |
| Row dimensions | Source row position, row kind, original display order, region label, federal district and published number. |
| Column dimensions | Source column position, original header and resolved indicator specification. |
| Source cells | One-based worksheet coordinates, decoded token kind, token, status and optional decimal value. |
| Numeric projection | Recognized numeric observations available to existing tabular consumers. |
| Unknown headers | Preserved source columns and their cells, with no invented indicator mapping. |

Cell statuses distinguish `numeric`, `blank`, `marker`, `unparsed` and
`formula_unresolved`. For example, a blank cell, `0`, an em dash and an unknown
word remain different observations. A formula is preserved as a formula token;
this profile does not evaluate it. The token is the decoded XLSX scalar,
not a claim to preserve the XML spelling of numeric storage. The retained
original supplies the byte-faithful carrier.

Numbers use `Decimal` during interpretation. A supplied text token such as
`0012.2500` remains in the cell while its numerical interpretation is
`Decimal("12.2500")`. Unknown source columns survive flake replay even though
they cannot yet contribute a named integrated indicator.

## 2. Complete snapshots

Each conversion has an independent operation:

| Domain value | Encode | Restore |
| --- | --- | --- |
| Publication-local flake | `build_flake_snapshot` | `read_flake_snapshot` |
| Integrated dataset | `build_dataset_snapshot` | `read_dataset_snapshot` |
| Prepared view | `build_view_snapshot` | `read_view_snapshot` |

These operations produce or consume the shared `DatasetSnapshot` contract.
`dataset.write_snapshot` and `dataset.read_snapshot` select the physical adapter.
A file-backed snapshot can be read in a fresh process without the original
workbooks or live parser objects. An application database can implement the same
ports without changing the interpretation or renderer.

Decoders validate component membership, exact schemas, observation keys,
indicator specifications, row dimensions, source lineage and method version.
A selected subset of components is useful for inspection but fails admission as
a complete domain value. The source identity and cell positions must agree with
the declared source manifest. Mutation of a sealed in-memory table is detected
before a subsequent operation consumes it.

Default version IDs are deterministic content identities including coverage and
source context. Callers may supply explicit dataset/version IDs. Physical paths
and provider IDs remain outside logical dataset identity.

## 3. Integration

`integrate_flakes(IntegrateEscrowRequest(flakes, coverage))` accepts already
extracted and restored flakes. It does not reopen workbooks. The result is an
`EscrowDataset` with observation and row tables, publication editions, indicator
specifications, source coverage and selection status.

An observation key consists of period, row kind, region label and indicator
code. Repeated releases and duplicate observation keys fail explicitly. Values
are never averaged as a side effect of pivot construction. Revision selection
belongs to the caller: the supplied set must contain one selected edition for
each period. Two editions assigning different definitions to one indicator code
also fail integration.

Every release keeps its own row order and geography labels. A view showing the
latest geography can therefore omit a historical region from that particular
view while the integrated dataset still retains its earlier observations.
Published labels are local keys; cross-publication geographic alias resolution
is a separate semantic operation.

The average-rate and weighted-average-rate headers resolve to separate indicator
codes. Similar wording does not establish identical statistical meaning.

`SnapshotCoverage` describes the claimed source universe. Its default is
`unknown`, even when every explicitly selected file succeeds. The
`selection_complete` flag separately records whether the selected composition
finished successfully. These two statements must not be conflated with full
publisher-history coverage.

## 4. Prepared views

`build_views(BuildEscrowViewsRequest(dataset, options))` uses an integrated
dataset as its direct input. It prepares `EscrowPivotPack`: typed table values,
indicator definitions, row order, row kinds, period order, missing-value policy,
coverage and the exact source dataset identity.

`regions_mode="latest"` selects the last publication's row order.
`regions_mode="custom"` requires a unique explicit selection of known regions.
The default `missing_display="source_token"` displays source markers and
unparsed text; `missing_display="blank"` selects a blank presentation instead.
Neither option changes the underlying integrated observations.

`render_workbook` only formats prepared tables. Percentage-point values such as
`7.25` retain that value and use two visible decimal places. They are not scaled
again by an Excel percent format. Other numerical values retain fractional
precision through an optional-decimal format. Row highlighting follows prepared
row kinds rather than guessing hierarchy from a region name.

A prepared-view snapshot preserves the exact selected tables and interpretation
of blanks, markers and text. Reading it and rendering it again produces the same
workbook representation under the same renderer version.

## 5. Calling the route

```python
from stratbox.domains.cbr import escrow
from stratbox.core.storage.datasets.definitions import (
    WriteSnapshotRequest, ReadSnapshotRequest,
)
from stratbox.core.storage.datasets.operations import write_snapshot, read_snapshot

# payload is supplied through the chosen source/material reader.
parsed = escrow.parse(escrow.ParseEscrowRequest(payload, "01062026.xlsx"))
assert parsed.outcome == "succeeded", parsed.diagnostics
encoded = escrow.build_flake_snapshot(escrow.EscrowFlakeSnapshotRequest(parsed.value))
assert encoded.outcome == "succeeded", encoded.diagnostics
stored = write_snapshot(WriteSnapshotRequest(encoded.value), store=dataset_adapter)
assert stored.outcome == "succeeded", stored.diagnostics

# This part may run in a separate process with a newly constructed adapter.
loaded = read_snapshot(ReadSnapshotRequest(stored.value.reference), store=dataset_adapter)
assert loaded.outcome == "succeeded", loaded.diagnostics
flake = escrow.read_flake_snapshot(escrow.ReadEscrowSnapshotRequest(loaded.value))
assert flake.outcome == "succeeded", flake.diagnostics
dataset = escrow.integrate_flakes(escrow.IntegrateEscrowRequest((flake.value,)))
assert dataset.outcome == "succeeded", dataset.diagnostics
views = escrow.build_views(escrow.BuildEscrowViewsRequest(dataset.value))
assert views.outcome == "succeeded", views.diagnostics
workbook = escrow.render_workbook(views.value)
assert workbook.outcome == "succeeded", workbook.diagnostics
```

The integrated dataset and prepared view have corresponding encode/read pairs
for the same storage pattern. `build_history` remains a composition for callers
starting from multiple supplied workbooks; independent integrations use
`integrate_flakes` instead.

A rendered representation can become a `MaterialArtifact` through the common
operation-handoff API and be saved with `material.save_artifact`. The caller
chooses local files, mounted storage or another admitted adapter. Publication
into an external corpus requires that receiver's explicit destination policy.

## 6. Limits

Discovery recognizes supported XLSX links and dated historical HTML issue
links. It reports format and extraction status for each discovered issue; it
does not assert that an index enumerates the entire history. Supplied source
bytes remain authoritative for that invocation, with no automatic Internet
fallback after an error.

The XLSX extractor requires the reviewed regional layout and a sufficiently
recognized indicator header. It preserves the selected table rather than
claiming to interpret every sheet, footnote or workbook feature. Historical
HTML can be retained exactly, while `parse` returns
`source.escrow_layout_unsupported` for it. Additional historical definitions can
be introduced as separate reviewed profiles and indicator editions.

Snapshots are bounded in-memory logical values. Large histories should be
partitioned by publication or a bounded set of periods. Durable scheduling,
retries, remote publication, and database lifecycle remain responsibilities of
the caller and selected adapters.
