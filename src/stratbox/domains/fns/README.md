# FNS: publication evidence, reported tables and population statistics

FNS has one operation owner, `fns`, and two meaningful publication families:

| Family | Source series | Reviewed interpretation |
| --- | --- | --- |
| SME register | `fns.sme` | Published country, federal-district and subject counters, including legal-entity and individual-entrepreneur totals |
| Legal entities | `fns.1yur` | Dated Form 1-YUR Part I fields and identity-only historical legal-kind mappings |

Canonical source, operation and profile resources live under
`stratbox/registry/fns`. `publications.catalog` projects validated publication
metadata; `operations.source_catalog` exposes the shared source-card view.
Domain algorithms and reviewed interpretation remain in the functional packages.

## Functional ownership

- `publications/` owns official indexes, dates, source routes, acquisition and
  `ReleaseContext`. An issue key, the date described by the observations, the
  publication date and the acquisition timestamp are separate values.
- `tables/` owns full source flakes, validation, source comparisons, readable
  evidence and the explicitly selected reported-field projections.
- `integration/` owns reviewed metric identity aliases, historical legal-kind
  mappings, map identities and qualified datasets. FNS geographic identifiers
  remain in FNS namespaces.
- `analytics/` owns matched net stock changes and explicit stock shares, with
  both input vintages and precise comparison boundaries.
- `products/` owns prepared views and CSV, JSON, JSONL or XLSX rendering. The
  selected regional CSV profiles are product-specific exporters.
- `operations/` owns typed requests, stage declarations, orchestration,
  computation receipts and neutral storage bindings.

## Route and retained boundaries

`extract` first preserves every JSON record/field or every admitted workbook
member/cell. `project` selects reviewed reported fields from that retained flake.
`align` applies versioned identity mappings. The resulting dataset feeds
`calculate_changes`, `calculate_shares` and `view`; `render` consumes a prepared
view. `readable`, `validate` and `compare_flakes` operate independently on flakes.
`compare_datasets` compares complete semantic keys at the same observation
period, while `calculate_changes` explicitly compares two dates.

Every flake, reported projection, integrated dataset, calculation and prepared
view has independent `*_snapshot` and `read_*_snapshot` operations. Snapshot
encoding and replay are technical functions rather than invented economic
processing stages. The snapshot version includes the complete context,
interpretation, coverage and lineage, so reinterpreting the same source bytes
produces a distinct immutable version.

`process` composes the offline route and returns the original payload and all
five derived boundaries: flake, projection, dataset, view and representation.
`capture_full` adds official acquisition and retains its receipt. Neither
composition chooses a store.

`source.save_original` retains exact original bytes. `dataset.write_snapshot`
retains any prepared logical snapshot. `render_artifact` and
`readable_artifact` package representation bytes, source association and
computation evidence for `material.save_artifact`. Local directories, mounted
network storage and other adapters are consumer-selected destinations.

## Source-specific safeguards

SME flakes retain all geographic levels, all fields, JSON kinds and literal
value tokens, including unfamiliar nested fields. Source validation is a
separate operation. The reviewed projection keeps every present supported
counter; absent counters stay absent, and unknown fields retain explicit
dispositions in the projection. Source-readable JSON preserves literal value
tokens; exact original whitespace remains in the separately retained original.

1-YUR flakes retain all admitted workbook members, sheets, cells, source tokens,
cached formula information and an inventory of unparsed members. Excel engines
are used at extraction; the historical Part I selector runs against retained
cells. It preserves reviewed cross-checks and the specific June 2019 sparse
release safeguard. Incomplete legal-kind sheets remain in the flake and become
explicit omissions in the selected projection. Mappings A, B, C1, C2 and C3
copy reported values only. In particular, the epoch-B LLC category is not
silently equated with the later LLC-including-additional-liability category.

The `not_ceased` and `bankruptcy_proceedings` constructs are stock counts.
`ceased_bankruptcy_liquidation` retains a qualified count with an unresolved
accumulation basis; a reporting date alone does not establish a monthly flow.
Net changes are differences between reported stocks, not entries, births or
exits. Shares require matching periods, perimeters, reference editions and
measurement scales; zero denominators produce a missing result and a qualifier.

`parse`, `capture`, `read_representation` and `compare` remain explicit
regional CSV product conveniences in the new operation packages. Their
metadata identifies selected product compositions/replay and their envelopes
declare qualified subset coverage. They are separate from full-source flake
retention.

See [the FNS route guide](../../../../docs/current-how/fns-data-pipeline.md) and
[the offline example](../../../../examples/fns_portable_route.py).
