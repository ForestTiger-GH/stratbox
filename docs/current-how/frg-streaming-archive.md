# FRG: streaming archives from a verified file selection

Use `frg.scan` and `frg.plan_cleanup` to identify the latest recognized
member of each file family. For large collections, publish the approved
selection directly to a filesystem ZIP with `frg.prepare_archive_to_store`.
This operation keeps only a fixed-size transfer chunk in memory.

```python
from stratbox.base.filestore import LocalFileStore
from stratbox.macrobanks import frg

inputs = LocalFileStore(root='/content')
outputs = LocalFileStore(root='/content/stratbox_outputs/frg')
planned = frg.plan_cleanup(frg.PlanCleanupRequest('.'), store=inputs)
assert planned.outcome == 'succeeded', planned.diagnostics
result = frg.prepare_archive_to_store(
    frg.StreamArchiveRequest(planned.value, 'FRG_latest.zip', compression='stored'),
    store=inputs, output_store=outputs,
)
assert result.outcome == 'succeeded', result.diagnostics
print(result.value.path, result.value.identity.sha256)
```

The source plan is rebuilt from the directory and compared with the original
before writing. For each member, source content is streamed and checked
against the source digest from the plan. The output ZIP is staged in the
destination directory and atomically replaced after successful verification.
If a source changes, an existing output remains intact.

Output may reside in a separate directory on the same local or mounted
filesystem. ZIP64 is supported. Limits: 500 entries, 64 GiB of source data,
and 8 MiB for optional extra in-archive report members. `compression='stored'`
is recommended for XLSX/XLSB inputs already compressed; `deflated` is optional.

`frg.prepare_archive` remains the small in-memory representation operation.
It retains its 32 MiB/member and 100 MiB aggregate safety bounds. Use the
disk-streamed operation for large selections.

Directory mutation is separate: only after ZIP success may a caller choose
to invoke `frg.apply_cleanup` using an authorized, still-current plan.