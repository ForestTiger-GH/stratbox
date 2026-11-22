# Frank RG report files

This domain identifies delivered Frank RG reports, selects report periods,
assigns standard filenames, and prepares verified file effects and archives.
Workbook bytes remain unchanged. Table interpretation and calculations have
explicitly missing stage coverage.

## Source and method boundaries

Root `REGISTRY_*.yaml` resources describe four logical report groups and their
series. They contain source IDs, titles, period-label kinds and profile IDs.
Directories, URLs, filenames and Python entry points belong to other owners:

| Owner | Responsibility |
| --- | --- |
| [Publications](publications/) | Registry admission, typed file evidence, recognition, selection, names and cleanup plans |
| [Profiles](publications/profiles.py) | Supplier naming rules, supported formats, period cutoffs and executable methods |
| [Bindings](operations/bindings.py) | Resolve logical sources to compatible registered profiles |
| [Operations](operations/) | Independent operations through the shared runner and explicit file-effect handlers |
| Caller | Runtime directory, storage providers, supplied bytes and output destination |

`families()`, `all_sources()` and `validate_all_profiles()` expose the available
logical sources. The operation catalog discovers one `frank_rg` owner with
the `frg.*` operation namespace. Importing the domain requires no spreadsheet
or dataframe dependency.

## Directory input in Colab or a mounted filesystem

```python
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains import frank_rg as frg

inputs = LocalFileStore(root="/content")
catalog = frg.scan(frg.DiscoveryRequest("."), store=inputs)
assert catalog.outcome == "succeeded", catalog.diagnostics

planned = frg.plan_cleanup(frg.PlanCleanupRequest("."), store=inputs)
assert planned.outcome == "succeeded", planned.diagnostics
plan = planned.value
print(plan.actions)

# Apply the exact reviewed plan. The default copies selected originals.
applied = frg.apply_cleanup(
    frg.ApplyCleanupRequest(plan, ".", plan.identity.sha256), store=inputs,
)
assert applied.outcome == "succeeded", applied.diagnostics
```

Use a different `LocalFileStore(root=...)` for a filesystem mount, or pass a
different `FileStore` implementation. Network transport, mounting and access
configuration belong to that provider. Discovery, identification and selection
are also independently callable as `discover`, `inspect` and `select`.

`delete_others=True` explicitly plans renaming and removal of recognized older
reports. Unknown files and reports with invalid period labels remain untouched.
Applying a plan rechecks its directory, profile methods, file versions and exact
digest. Same-period candidates with different bytes block cleanup. Byte-identical
copies can be resolved after verification, making repeated copy runs idempotent.

## Input supplied by a specialized method

An external method can supply bytes and explicit report context without a
directory, filename or file-store provider:

```python
from datetime import date
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.operations.source.original_definitions import OriginalDestination, SaveOriginalRequest
from stratbox.core.operations.source.originals import save_original
from stratbox.domains import frank_rg as frg
from stratbox.shared.evidence import SourcePayload

# raw_bytes is the exact material returned by the caller's acquisition method.
captured = frg.capture(frg.CaptureRequest(
    source_id="frg.express.issuance",
    period=frg.ReportPeriod(date(2026, 5, 1)),
    payload=SourcePayload(raw_bytes),
    format="xlsx",
))
assert captured.outcome == "succeeded", captured.diagnostics
prepared = frg.prepare_file(frg.PrepareFileRequest(captured.value))
assert prepared.outcome == "succeeded", prepared.diagnostics

outputs = LocalFileStore(root="/content/stratbox_outputs/frg")
saved = save_original(
    SaveOriginalRequest(prepared.value.payload,
                        OriginalDestination(prepared.value.filename)),
    store=outputs,
)
assert saved.outcome == "succeeded", saved.diagnostics
```

`acquire` reads an identified filesystem asset with before/read/after version
verification. Both acquisition routes feed the same `prepare_file` operation.
The supplied source and period are caller assertions checked against the
registered profile; this scope does not decode the workbook to confirm them.

## Revision evidence and archive output

`plan_updates` can compare observed metadata with `SourceCheckpoint` values.
Its `metadata_unchanged` result is only a filesystem observation.
`force_refresh=True` requests exact material verification; `assess_material`
compares acquired byte identities. `checkpoint_for` returns a candidate that
the consumer commits after its intended effects complete.

Weekly labels mean a numbered week within a month. A `Q` filename marker is
part of recognition; it does not establish an economic aggregation period.

Frank RG prepares the selected members and their standard names. Shared core
archive functions create and verify ZIP bytes. Use `prepare_archive` for a small
in-memory result and `prepare_archive_to_store` for staged streaming to a caller
selected store. The latter supports large files, immutable retries and conditional
replacement. See the [streaming archive usage](../../../../docs/current-how/frg-streaming-archive.md).
