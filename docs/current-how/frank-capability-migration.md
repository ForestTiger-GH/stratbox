# Frank RG report capabilities

The Frank RG contribution supplies canonical commands, operations and scenarios
for fourteen registered report series. File recognition, acquisition, physical
workbook extraction, semantic interpretation, integration, revision analysis and
products run through the common capability session. The semantic scope is
explicitly qualified: the package contains no verified publisher business-layout
editions for these fourteen series. A supplied byte-bound profile or an explicitly
reviewed external layout supplies that interpretation.

## 1. Logical report scope

| Family | Series | Delivery period |
| --- | --- | --- |
| Express | `issuance`, `portfolios`, `passives`, `issuance_cards` | Snapshot label |
| Express | `issuance_weekly` | Numbered week within a month |
| RBM | `volumes_q`, `portfolios_q`, `volumes_cards_q` | Snapshot label with recognition marker |
| Regional | `issuance`, `portfolios`, `issuance_mortgage`, `portfolios_mortgage`, `issuance_cards` | Snapshot label; recognition scope starts in April 2026 |
| Special | `mortgage_refinancing` | Snapshot label |

Identifiers use the `frg.<family>.<series>` form. Delivery dates, week numbers and
Q markers establish report identity. Economic periods, units, scales, quantity
kinds and population perimeters come from semantic bindings.

## 2. Independent processing boundaries

| Capability | Inputs and result |
| --- | --- |
| `frg.discover` | Directory parameters produce a bounded file index. |
| `frg.inspect` | An index produces recognized report assets. |
| `frg.select` | An inventory produces period selections, including missing and ambiguous states. |
| `frg.scan` | A scenario composes discovery, recognition and selection while retaining their outputs independently. |
| `frg.acquire` | One recognized asset produces a report and exact original payload after file-version checks around the read. |
| `frg.capture` | Supplied bytes, source, report period and format produce the same report contract. |
| `frg.prepare_file` | A report produces a canonical filename and unchanged payload. |
| `preserve.material` | The acquired or captured original payload produces a confirmed storage receipt at an explicit destination. |
| `frg.extract` | A report produces complete decoder-visible workbook cells, literal values, formulas, coordinates and source evidence. |
| `frg.build_flake` | A physical extract and byte-bound semantic profile produce qualified observations. |
| `frg.bind_layout` | An extract, externally reviewed layout and explicit economic periods produce a fresh byte-bound profile. |
| `frg.integrate` / `frg.align` | Qualified observations receive explicit dataset identity or compatibility-checked composition. |
| `frg.build_history` | Supplied releases remain separately versioned; a closed input collection does not assert publisher-wide history completeness. |
| `frg.calculate` | Two integrated releases produce same-semantic-key revision deltas. |
| `frg.prepare_view` / `frg.render_view` | Integrated or calculated observations produce an independent view and representation. |
| `ingest.observations` | An integrated Frank observation batch receives the common semantic snapshot encoding and an immutable dataset-provider reference. |
| `publish.release` | Confirmed original/product receipts, expected member identities and a coherent input-version vector produce a conditionally committed release manifest. |

Physical extraction supports XLSX/XLSM and qualified XLS/XLSB decoding. Binary
decoder qualifications remain attached to the result. Successful physical
extraction establishes workbook evidence; semantic acceptance additionally checks
every selected cell, value status, scale, quantity kind, period and perimeter.

An exact-byte profile preserves selected analytical cells separately from the
complete physical extract. Blank, dash, withheld, missing and zero remain distinct.
Formula cells require an available cached value before numeric interpretation.
Integration rejects duplicate semantic keys and incompatible metric definitions.
Revision deltas compare releases of the same economic observation; their contract
does not infer growth between different periods.

## 3. Reusable layout admission and replay

`LayoutProfile` records explicit source and format scope, exact ordered sheet
geometry, typed anchor values, selected cell bindings, review-original identities
and a review qualification. `bind_layout` checks that scope and requires explicit
economic periods for all period keys. Changed units, missing headers and altered
sheet geometry reject the layout. A successful binding targets the new original
byte identity, preserving the layout identity and review qualification in the
semantic profile fingerprint. A synthetic test review remains qualified as such.

`frg.extract_snapshot` / `frg.read_extract`, `frg.flake_snapshot` /
`frg.read_flake`, `frg.observation_snapshot` / `frg.read_observations`, and
`frg.view_snapshot` / `frg.read_view` provide semantic replay. Restored values
retain source coordinates, literal values, statuses, periods, metric definitions,
source uses, lineage, profile identity and qualifications. A retained extract or
view can enter its corresponding downstream stage independently.

`frg.report.product` accepts `report` and `profile` inputs, with `dataset_id`,
`release_id` and `view_id` parameters and optional `format`. It exposes `extract`,
`flake`, `observations`, `view` and `representation`. Source goals `source.extract`
and `source.product` select these routes by exact source identity. Callers can
publish the resulting representation through the common storage contract.
The shared ingestion route accepts the actual integrated `ObservationBatch`;
querying its dataset reference restores a complete snapshot with the same
observations, lineage and source uses. Release publication follows preservation
of every selected member. Declared per-member version vectors must match the
release vector, and expected member digests identify the preserved bytes.

## 4. Cleanup and archive effects

`frg.plan_cleanup` produces a revision-bound proposal. `frg.prepare_archive`
packages its selected originals without applying the proposal. The archive
manifest identifies each source, issue, asset and exact member bytes independently
of the storage path. `frg.prepare_archive_to_store` streams a selected archive
through a staged destination transaction, retaining partial and unknown outcomes.

`frg.apply_cleanup` is a separate operation requiring the plan, authorized
directory and exact plan digest. It revalidates the directory and plan, applies
conditional mutations, and returns a receipt for every action. Confirmed,
failed, unknown and unattempted actions remain distinguishable. Extraction and
product preparation perform no cleanup effects.
