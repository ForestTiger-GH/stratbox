# Reporting-form originals, source flakes and reproducible calculations

CBR reporting forms expose independent acquisition, extraction, normalization,
integration, calculation and presentation operations. Every DBF in a supplied
release can be retained before choosing a financial model. Typed dataset snapshots
and CSV collections provide explicit persistence boundaries.

The implemented source decoder has a bounded dialect profile. It accepts classic
dBASE III headers with version bytes `0x03` and `0x83` and textual `C`, `N`, `F`,
`D` and `L` fields. Other dialects, binary fields and memo-aware decoding require
separate profiles. The original bytes and unsupported status remain available in
an explicitly partial extraction.

## 1. Responsibilities and supported source families

| Stage | Public operation | Result |
| --- | --- | --- |
| Published inventory | `discover_sources` | Selected links found in a supplied or acquired CBR index |
| Explicit selection | `select_sources` | Canonical acquisition routes for specified form keys |
| Acquisition | `acquire` | Exact archive payload and acquisition receipt |
| Source extraction | `extract_forms` | All regular members, decoded DBF records and preserved auxiliary bytes |
| Flake persistence | `flake_snapshot`, `restore_flakes` | Typed tables with source schema, physical flags and member identities |
| Source publication | `render_flakes`, `read_flake_export` | CSV files, complete descriptors, original members and collection manifest |
| Normalization | `normalize_form` | Selected physical table projected through the form specification |
| Convenience composition | `parse_form` | Extraction followed by normalization |
| History integration | `integrate_forms`, `restore_history` | Selected unique dated releases, suitable for a dataset adapter |
| Calculation | `build_form_data` | Selected bank/model indicators, exact Decimal values and computation lineage |
| Presentation preparation | `build_form_views` | Explicit form profile and prepared tables |
| Result persistence | `snapshot_result`, `restore_normalized`, `restore_data`, `restore_views` | Reconstructed values with scalar types, axes and computation receipts |
| File rendering | `render_workbook` | Workbook bytes independent of the destination |

The common CBR publication registry identifies source families `101`, `102`,
`123`, `134`, `135`, `802`, `803` and `805`. Acquisition and extraction also accept
syntactically valid three-digit form keys discovered in the official index.
Financial models currently exist for `101`, `102`, `123`, `135`, `802` and `805`.
Thus an original or supported DBF from form `134` or `803` can be preserved and
published even though normalization through a financial model is unavailable.

`select_sources` constructs explicit routes; it does not prove publication.
`discover_sources` selects actual links from the supplied index, preserving the
index identity. A future end date does not generate speculative HTTP requests.
The caller may provide index bytes from another reader or let the operation
acquire the official index through its HTTP provider.

## 2. What a source flake preserves

Each `FormFlakes` value binds a form code and supplied reporting date to the exact
container identity. It includes all regular archive members, their original
relative names, hashes, exact bytes and individual status. Decoded DBF members
add:

- The declared dialect profile, version byte, raw header date bytes, language
  driver, selected encoding and the basis of that selection.
- Field order, names, types, widths, decimal counts and offsets.
- Physical record order and one-based record ordinals, including deleted records.
- Every decoded value as a string, with only the declared fixed-width padding
  removed. Textual numeric fields never pass through binary floating point.
- The original EOF marker state and the geometry required to validate replay.

`"000001.2300"`, `"0012"`, an empty token and `"0"` stay distinct. Date fields
remain source tokens, so a malformed calendar date can be preserved for later
interpretation. Header update dates never replace the reporting date supplied
with `FormKey`. Calendar validation, identifier normalization, deletion policy,
model selection and arithmetic belong to later operations.

The decoder rejects unsupported dialects, invalid field geometry, missing field
terminators, truncated rows, unexpected physical flags and undeclared trailing
records. It retains exact original DBF bytes separately from the decoded values;
the decoded flake does not claim to reproduce removed fixed-width padding.

`strict=True` is the extraction default. A malformed or unsupported DBF fails the
operation. With `strict=False`, every member remains inventoried and unsupported
or failed DBFs retain their bytes and diagnostics. The operation returns a
`partial` outcome, and `normalize_form` requires a complete extraction. Auxiliary
files such as dictionaries and memo companions are retained even when their
format is outside the decoder profile.

## 3. Continue after saving a flake

The following offline route uses exact bytes supplied by any caller-owned reader:

```python
from datetime import date
from stratbox.domains.cbr import reporting_forms as forms
from stratbox.shared.evidence import SourcePayload
from stratbox.core.storage.datasets import operations as datasets

extracted = forms.extract_forms(forms.ExtractFormRequest(
    forms.FormKey("802", date(2026, 4, 1)),
    SourcePayload(archive_bytes, "application/zip"),
))
assert extracted.outcome == "succeeded"

encoded = forms.flake_snapshot(forms.FormFlakeSnapshotRequest(
    extracted.value, "cbr.form.802", "release-2026-04-01-raw",
))
written = datasets.write_snapshot(
    datasets.WriteSnapshotRequest(encoded.value), store=selected_dataset_store,
)
```

After a new process opens the chosen dataset adapter and obtains the pinned
reference, processing continues from the retained typed data:

```python
loaded = datasets.read_snapshot(
    datasets.ReadSnapshotRequest(reference), store=selected_dataset_store,
)
restored = forms.restore_flakes(loaded.value)
normalized = forms.normalize_form(forms.NormalizeFormRequest(restored.value))
history = forms.integrate_forms(forms.IntegrateFormsRequest(
    (normalized.value,), "cbr.form.802", "release-2026-04-01-history",
))
```

Flake replay validates the tables, profile, member identities, physical order,
flags and coverage. It does not reopen the original DBF decoder. A subset of
dataset components cannot be admitted as a complete flake.

Normalization selects an unambiguous physical table using each form's field
aliases and declared preferred name. Deleted records are excluded by default;
the caller can select a different explicit policy. Form `101` retains account
plan and account-side information for its existing financial rules. Form `802`
retains optional adjustment channels and its hierarchical presentation model.

`integrate_forms` rejects mixed forms and duplicate reporting dates. It does not
silently resolve revised releases. The caller chooses the intended revision
before building a history. The history manifest states that publisher-wide
historical coverage is unknown rather than inferring it from selected inputs.

## 4. Resume calculations and presentation independently

`restore_history` returns normalized snapshots accepted by `build_form_data`.
The selected banks, model table, indicator ordering, inputs and calculation
receipt are carried by `FormData`. `FormViews` retains its profile, sheet order,
complete table metadata and calculation receipt.

`snapshot_result(FormResultSnapshotRequest(value, dataset_id, version_id))`
encodes a normalized snapshot, calculated dataset or prepared view. After the
same neutral write/read boundary, use the matching `restore_normalized`,
`restore_data` or `restore_views` operation. Restore operations verify the exact
kind and the reconstructed computation fingerprint. Modifying a table while
retaining its old receipt fails identity validation.

The shared DataFrame codec preserves Decimal values, empty strings, nullable
sentinels, column dtypes, row and column axes and ordering. The restored calculated
data can directly build views; restored views can directly render a workbook.
No live Python object, solver, imported class name or environment-specific path
is used as a serialization instruction.

## 5. Publish CSV flakes or workbook products

`render_flakes` creates one UTF-8 CSV per decoded DBF and a `form.json` descriptor.
The descriptor records field schemas, deleted record ordinals, numeric and blank
policies, original/member identities, paths, encoding and individual statuses.
The result also carries a shared `CollectionManifest` suitable for
`material.archive`.

The caller owns the optional path prefix. A corpus profile may choose
`regulatory-reporting/2026/2026-04-01/form-0409802`; another receiver may choose a
different layout. Prefixes never alter the form or release identity.

By default, the collection includes exact DBF originals and auxiliary members.
After restoring its manifest and reading the files through any byte provider,
`read_flake_export` reconstructs the decoded flakes from CSV and descriptors
without parsing DBF again. A compact export may set
`include_member_originals=False`; it remains useful for publication but the
complete replay operation requires the original members. Unsupported members and
auxiliary files are always retained.

```python
from stratbox.core.operations.materials.archive import archive_materials
from stratbox.core.operations.materials.archive_definitions import ArchiveMember, ArchiveRequest
from stratbox.core.operations.source.original_definitions import OriginalDestination

exported = forms.render_flakes(forms.RenderFormFlakesRequest(restored.value))
members = tuple(
    ArchiveMember(name, SourcePayload(value.data, value.media_type))
    for name, value in exported.value.files
)
packed = archive_materials(ArchiveRequest(
    members, OriginalDestination("form-release.zip"),
    manifest=exported.value.manifest,
), output_store=selected_filestore)
```

The common archive operation verifies the exact selected names, hashes and media
types against the manifest. It supports nested relative names and publishes the
manifest together with those files. It never discovers successful files by
scanning a temporary directory.

`render_workbook` produces a `Representation` with product semantics. The common
material artifact save/read operations handle its placement and restoration.
A workbook, source archive and source flake retain different semantic roles even
when they share the same physical store.

## 6. Scope of verification and limits

Local checks cover malformed geometry and dialect rejection; preservation of
numeric lexemes, date tokens, blank/zero distinction and deleted records; all
DBFs and auxiliary files in one release; form families without analytical models;
file-adapter replay through history, calculation, prepared views and rendering;
and CSV collection replay without invoking the DBF decoder.

RAR decoding continues to use the archive-provider boundary. A managed execution
must provide its admitted decoder. The extraction operates on one bounded
release, and a dataset adapter applies its own object and storage limits. Large
histories are composed from separate retained releases. Supporting additional
DBF dialects, memo content interpretation or a new form's financial model requires
an explicit profile with corresponding source fixtures.
