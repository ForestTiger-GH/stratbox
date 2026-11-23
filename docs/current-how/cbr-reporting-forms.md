# CBR reporting forms: physical source records, semantic observations and financial models

Reporting forms have separate owners for source acquisition, physical layouts,
semantic alignment, financial calculations and presentation. The source route
admits eight form families and preserves every regular archive member before any
financial model is selected. Six reviewed layouts support source projection,
semantic observations and the existing financial models. Complete typed
snapshots provide an explicit continuation boundary at each implemented layer.

Source history and semantic alignment have different meanings. A history packs
selected source projections with their reporting dates and evidence. Alignment
assigns subject namespaces, metrics, units, periods and value statuses. The
financial-model engine consumes explicitly prepared inputs from aligned
observations. A convenience source-projection call composes alignment, model-input
admission and the same calculation boundary.

## 1. Responsibility boundaries and admitted families

| Owner | Responsibility |
| --- | --- |
| `cbr.publications.catalog` and `profiles` | Logical source identity, acquisition profiles, official index routes and dated archive URLs |
| `cbr.tables.reporting_forms` | All-member extraction, literal DBF flakes, reviewed physical layouts, source projection, readable records and source comparison |
| `cbr.integration.reporting_forms` | Explicit subject mappings and semantic observation alignment |
| `cbr.analytics.reporting_forms` | Reviewed semantic model-input admission, model registry, formula/direct evaluation, subject selection and calculated tables |
| `cbr.products.reporting_forms` | Output profiles, prepared presentation tables and workbook rendering |
| `cbr.operations.reporting_forms` | Typed callable boundaries, metadata, execution evidence and portable result codecs |

These paths are relative to `stratbox.domains`. The source registry, layout
registry, financial-model registry and output-profile registry are independent.
A source being known proves neither its physical layout nor an analytical model.

| Form | All-member source route | Reviewed projection and alignment | Financial-model resource | Presentation profile |
| --- | --- | --- | --- | --- |
| `101` | Available | Account balances, account plan and account side | `form101.csv` | Standard |
| `102` | Available | Income/expense source values; alignment requires an explicit reporting interval | `form102.csv` | Standard |
| `123` | Available | Own-funds source rows | `form123.csv` | Standard |
| `134` | Available | No reviewed projection | None | None |
| `135` | Available | Reviewed prudential-ratio table; all other members remain in flakes | `form135.csv` | Standard |
| `802` | Available | Consolidated-group own-funds rows and optional adjustment channels | `form802.csv` | Hierarchical |
| `803` | Available | No reviewed projection | None | None |
| `805` | Available | Reviewed prudential-ratio table | `form805.csv` | Standard |

`LAYOUT_REGISTRY` owns the current physical edition `cbr.forms.layout.v1`.
`MODEL_REGISTRY` identifies model editions as `cbr.forms.model.<code>.v1` and
selects the packaged resources. `FORM_VIEW_PROFILES` owns presentation choices.
A caller-supplied model is admitted and pinned as a separate input.

## 2. Independently callable operations

The public API is `stratbox.domains.cbr.operations.reporting_forms`. Registry IDs
below use the `cbr.forms.` prefix; storage operations remain neutral.

| Operation ID suffix | Public function | Result and scope |
| --- | --- | --- |
| `discover_sources` | `discover_sources` | Actual indexed links, index identity, selection scope and unsupported candidates |
| `select_sources` | `select_sources` | Canonical routes for explicitly selected registered form keys |
| `acquire` | `acquire` | Exact source archive and acquisition receipt |
| `extract` | `extract_forms` | All regular members, literal decoded records, original bytes and per-member status |
| `make_readable` | `make_readable` | Schemas, records, deletion flags and member coverage as a reading representation |
| `compare` | `compare_sources` | Separate byte, structure, source-record and method comparison layers |
| `flake_snapshot`, `restore_flakes` | Same names | Complete typed flake encoding and replay |
| `render_flakes`, `read_flake_export` | Same names | CSV collection with descriptors, member originals and manifest |
| `normalize` | `normalize_form` | One reviewed physical table projected to source fields; an extraction stage |
| `parse` | `parse_form` | Extraction followed by source projection |
| `build_history`, `restore_history` | `build_source_history`, `restore_history` | Selected unique dated projections for one form; an extraction stage |
| `align` | `align_forms` | Semantically qualified `ObservationBatch` from reviewed projections |
| `observations_snapshot`, `restore_observations` | `snapshot_observations`, `restore_observations` | Exact portable aligned observations |
| `prepare_model_inputs` | `prepare_model_inputs` | Reviewed semantic variables with validated units, subject identity, period and formula axes |
| `calculate` | `calculate` | Financial-model indicators from prepared inputs with exact source-version lineage |
| `build_data` | `build_form_data` | Explicit source projection → alignment → model-input admission → calculation composition |
| `build_views` | `build_form_views` | Prepared product tables with their output profile |
| `result_snapshot` | `snapshot_result` | Typed encoding of a source projection, calculated tables or prepared views |
| `restore_normalized`, `restore_data`, `restore_views` | Same names | Kind-specific result replay with identity validation |
| `render_workbook` | `render_workbook` | Workbook bytes from prepared views |

`source.save_original` / `source.read_original` preserve original bytes.
`dataset.write_snapshot` / `dataset.read_snapshot` preserve and read complete
logical snapshots through the selected adapter. Neither the form code nor a
presentation profile chooses a storage destination.

`select_sources` constructs reviewed routes; it does not establish that a
release was published. `discover_sources` reads the supplied or acquired index
and keeps its identity. Unknown three-digit form links appear in
`FormInventory.unsupported_sources` with `source.form_profile_unsupported`.
They do not automatically become admitted acquisition or extraction profiles.
Date filters apply to discovered links and never generate speculative requests.

## 3. Exact source flakes and bounded DBF interpretation

A `FormFlakes` value binds a supplied form code and reporting date to the exact
container identity. Every regular member retains its relative name, hash, exact
bytes and individual status. Decoded DBF members additionally retain:

- Dialect profile, version byte, raw header-date bytes, language driver,
  selected character encoding and the reason for that selection.
- Field order, names, types, widths, decimal counts and offsets.
- Physical record order, one-based ordinals and deleted-record flags.
- Source values as strings, with declared fixed-width padding removed.
- EOF-marker state and the geometry required to validate replay.

`"000001.2300"`, `"0012"`, an empty token and `"0"` remain different values.
Numeric lexemes never pass through binary floating point. A date field remains
a literal token until a later interpretation step. The DBF header update date
does not replace the reporting date in `FormKey`.

The decoder admits classic dBASE III headers with version bytes `0x03` and
`0x83`, and textual `C`, `N`, `F`, `D` and `L` fields. Other dialects, binary
fields and memo interpretation need explicit decoder profiles. Invalid geometry,
missing field terminators, truncated records, unexpected physical flags and
undeclared trailing records fail admission. Original member bytes remain
separate evidence; decoded tokens do not claim to reconstruct stripped padding.

`strict=True` is the default. A malformed or unsupported DBF fails extraction.
With `strict=False`, every member remains inventoried and rejected DBFs retain
bytes and diagnostics. The result is explicitly partial, and source projection
requires a complete extraction. Auxiliary files are retained even when their
content format has no decoder.

`make_readable` transcribes every decoded DBF, field schema and deletion flag.
It reports a partial outcome if any member lacks a decoded table, including
auxiliary material. This qualifies the readable coverage independently of
whether all original bytes have been retained.

## 4. Save source flakes and resume a reviewed projection

The following example assumes `archive_bytes` and a caller-selected dataset
adapter. An HTTP response, a local reader or another byte provider can supply
those exact bytes.

```python
from datetime import date
from stratbox.domains.cbr.operations import reporting_forms as forms
from stratbox.shared.evidence import SourcePayload
from stratbox.core.storage.datasets import operations as datasets

extracted = forms.extract_forms(forms.ExtractFormRequest(
    forms.FormKey("802", date(2026, 4, 1)),
    SourcePayload(archive_bytes, "application/zip"),
))
assert extracted.outcome == "succeeded", extracted.diagnostics
encoded = forms.flake_snapshot(forms.FormFlakeSnapshotRequest(
    extracted.value, "cbr.form.802.source", "2026-04-01-v1",
))
assert encoded.outcome == "succeeded", encoded.diagnostics
written = datasets.write_snapshot(
    datasets.WriteSnapshotRequest(encoded.value), store=selected_dataset_store,
)
assert written.outcome == "succeeded", written.diagnostics

# A later process opens its own adapter and reads this exact pinned reference.
loaded = datasets.read_snapshot(
    datasets.ReadSnapshotRequest(written.value.reference),
    store=selected_dataset_store,
)
assert loaded.outcome == "succeeded", loaded.diagnostics
restored = forms.restore_flakes(loaded.value)
assert restored.outcome == "succeeded", restored.diagnostics
normalized = forms.normalize_form(forms.NormalizeFormRequest(restored.value))
assert normalized.outcome == "succeeded", normalized.diagnostics
```

Flake replay validates schemas, profile, member identities, physical order,
record flags and coverage without invoking the DBF decoder. Missing components
cannot be admitted as a complete flake.

Source projection selects an unambiguous physical table using the reviewed
field aliases and preferred member name. It retains `_source_member` and
`_source_record` beside the projected fields. Deleted records are excluded by
default; `include_deleted` makes the caller's alternative policy explicit.
Form `101` preserves account-plan and side fields. Form `802` preserves optional
adjustment channels, including the difference between an absent field and an
empty value in a present field.

A retained source history is constructed independently:

```python
history = forms.build_source_history(forms.FormHistoryRequest(
    (normalized.value,), "cbr.form.802.source-history", "selected-releases-v1",
))
assert history.outcome == "succeeded", history.diagnostics
```

A history rejects mixed forms and duplicate reporting dates. The caller selects
the intended revision before packing a history. Its coverage describes the
selected releases and leaves publisher-wide historical completeness unknown.
The current history contract contains reviewed `FormSnapshot` projections, so
forms `134` and `803` use individual complete flake snapshots instead.

## 5. Semantic alignment and exact observation replay

`align_forms(AlignFormRequest(...))` produces a shared `ObservationBatch`.
Alignment records the reviewed layout edition, original subject identity,
source dataset, indicator code, measure channel, account plan/side when present,
value status and evidence down to member, physical record and source field.

| Semantic property | Admission rule |
| --- | --- |
| Registration namespace | Physical `REGN_GKO` becomes `cbr.banking_group.registration`; ordinary registration becomes `cbr.bank.registration` |
| Canonical subject | Optional `FormSubjectMapping` supplies a target `SubjectRef` and mapping edition; the original identity remains in dimensions |
| Monetary source values | Forms `101`, `102`, `123`, `802`: `RUB`, scale `1000` |
| Prudential ratios | Forms `135`, `805`: `percent`, scale `1`, ratio quantity kind |
| Source stock date | Forms other than `102`: supplied reporting date as `PeriodRef("as_of", ...)` |
| Income/expense period | Form `102`: caller-supplied `PeriodRef("interval", start=..., end=...)`, keyed by reporting date; the interval cannot end after that date |
| Value qualification | Decimal numeric values, zero, blank, dash and absent fields remain distinct |
| Revisions and duplicates | Select one revision for each form/date; duplicate semantic observations fail admission |

The operation preserves source values and scale as separate properties. It does
not multiply values into base rubles or infer an income/expense interval from
a filename. Banking groups and credit institutions have separate namespaces even
when their numeric registration tokens happen to match.

```python
aligned = forms.align_forms(forms.AlignFormRequest(
    (normalized.value,), "cbr.form.802.observations", "aligned-v1",
))
assert aligned.outcome == "succeeded", aligned.diagnostics
portable = forms.snapshot_observations(forms.SnapshotFormObservationsRequest(
    aligned.value, "cbr.form.802.integrated", "aligned-v1",
))
assert portable.outcome == "succeeded", portable.diagnostics
```

After the neutral dataset write/read boundary, `restore_observations` restores
subject namespaces, metric definition versions, units/scales, all period fields,
dimensions, perimeter, exact scalar types, statuses, raw tokens and evidence.
The shared observation codec preserves logical batch identifiers even when the
outer stored dataset has different identifiers. Its coverage describes exactly
the supplied batch and makes no inference about publisher completeness.

## 6. Financial models, selections and presentation

The financial-model route can start from restored integrated observations:

```python
# restored_batch is the value returned by forms.restore_observations.
prepared = forms.prepare_model_inputs(forms.PrepareFormModelInputsRequest(
    restored_batch,
))
assert prepared.outcome == "succeeded", prepared.diagnostics
calculated = forms.calculate(forms.CalculateFormRequest(prepared.value))
assert calculated.outcome == "succeeded", calculated.diagnostics
views = forms.build_form_views(calculated.value)
assert views.outcome == "succeeded", views.diagnostics
workbook = forms.render_workbook(views.value)
assert workbook.outcome == "succeeded", workbook.diagnostics
```

`prepare_model_inputs` admits one reviewed form and checks the complete metric
identity and layout edition, unit, scale, quantity kind, source registration,
canonical subject mapping, perimeter, reporting date and observation period.
It requires all declared source-variable channels, including explicitly missing
optional channels. Formula inputs retain account-plan and side axes; a required
account-plan axis cannot be inferred. Many source registrations cannot silently
collapse into one canonical subject, and contradictory namespace/identifier
bindings fail admission.

`FormModelInputs` retains the immutable semantic batch and admission edition.
`calculate` revalidates it before constructing calculation variables. Arbitrary
observations, derived metrics, unknown dimensions, unsupported units and missing
axes therefore cannot masquerade as source model inputs. The exact integrated
snapshot identity and model-input rules are pinned in calculation lineage.
No DBF parsing or source-snapshot reconstruction is used on this route.

`build_form_data(BuildFormDataRequest(snapshots=...))` remains an explicit
composition for reviewed source projections, including those returned by
`restore_history`. It performs alignment, prepares model inputs and invokes the
same calculator. Form `102` requires the request's explicit `periods` mapping,
just as independent alignment does.

When `banks=None`, the default `selection_profile="all_admitted"` includes every
registration present in the admitted source projections. Default labels are the
registration identifiers. An explicit tuple of `BankSelection(regn, label)`
chooses a narrower analytical perimeter. The packaged historical selection is
available only through the named `selection_profile="legacy"` and is intersected
with admitted source subjects. Explicit registrations absent from the supplied
batch fail admission. Selection uses the CBR registration identifiers; canonical
subject namespaces and identifiers remain separate calculated columns. The
selected subjects, labels, model bytes and exact integrated identities become
calculation inputs.

`FormData` retains the calculated long table, selected subjects, model table,
indicator order and computation receipt. Its long table includes canonical
`SubjectNamespace` / `SubjectId`, the source subject namespace, and exact period
kind, as-of date and interval endpoints beside the familiar model columns. `build_form_views` prepares product
tables using the separate output-profile registry. `FormViews` retains its
profile, sheet order, table metadata and evidence. `render_workbook` consumes
these prepared views and returns workbook bytes; acquisition and source parsing
are independent of that render step.

`snapshot_result(FormResultSnapshotRequest(value, dataset_id, version_id))`
encodes a source projection, calculated result or prepared view. Following the
neutral storage boundary, use `restore_normalized`, `restore_data` or
`restore_views` for the expected kind. These readers check reconstructed
computation fingerprints. Changing a table while retaining its previous receipt
fails validation.

The DataFrame codec preserves Decimal values, empty strings, nullable sentinels,
dtypes, row/column axes and ordering. No arbitrary Python object or imported
class name is accepted as a deserialization instruction.

## 7. Source exports, output destinations and practical limits

`render_flakes` emits one UTF-8 CSV per decoded DBF, a `form.json` descriptor and
a shared `CollectionManifest`. The descriptor records schemas, deletion flags,
blank/numeric policies, encoding, original/member identities and per-member
status. The caller can select a path prefix independently of logical identity.

By default, the export includes exact DBF originals and auxiliary members.
`read_flake_export` reconstructs flakes from the CSV files and descriptors
without invoking DBF decoding. A compact export with
`include_member_originals=False` is suitable for publication, while complete
replay requires the original members. Unsupported and auxiliary members remain
retained.

The shared `material.archive` operation can package the exported collection and
manifest. The generic artifact operations can place readable material or a
rendered workbook in a selected file store. A source archive, a flake collection,
a typed dataset and a product workbook retain distinct roles even if their
physical destination is the same directory or network drive.

RAR extraction uses the archive-provider boundary. Managed execution requires
an admitted decoder. Extraction handles one bounded release; larger histories
are composed from retained releases and remain subject to dataset-adapter
limits. Additional DBF dialects, physical layouts, semantic mappings and
financial models each require their own explicit admission scope.
