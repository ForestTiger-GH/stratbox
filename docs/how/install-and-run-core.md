# Install and call the core library

Stratbox 0.11 requires Python 3.10 or later. Install the verified wheel into
the interpreter that runs the caller. In Jupyter or Colab use `%pip install
/path/to/stratbox-0.11.0-py3-none-any.whl` in the target kernel.

| Install profile | Use |
| --- | --- |
| Base | Typed contracts, local storage, daily OFFICES, SME JSON and territorial office XLSX parsing. |
| `http` | Built-in Requests HTTPS adapter. A supplied transport can satisfy the same contract. |
| `dataframe`, `excel` | Banking analytics and workbook rendering. The `excel` extra also supplies the 1-YUR OOXML reader. |
| `excel-legacy` | 1-YUR BIFF/XLS and legacy Excel commands, with OLE admission before decoding. |
| `dbf`, `rar` | Bank form DBF and an explicitly constructed `RarArchiveReader`. Compressed RAR members can require a system extractor. |
| `sors-restoration` | SORS analytical dependencies and HiGHS for the global feasibility and optimization stages. |
| `excel-binary`, `pdf`, `documents`, `dbf-write` | Additional format commands. |
| `test` | Local test environment with the dependencies used in the suite. |

For an independently installed wheel, provide the selected extras on the
wheel path, for example `python -m pip install
'./stratbox-0.11.0-py3-none-any.whl[http,dataframe,excel]'`.

## Parse a saved HTML page

```python
from datetime import date
from pathlib import Path

from stratbox.data import SourcePayload
from stratbox.macrobanks.cbr_offices import ParseOfficesRequest, parse

original = SourcePayload(Path("offices.html").read_bytes(), "text/html")
parsed = parse(ParseOfficesRequest(original, date(2026, 11, 11)))
if parsed.outcome != "succeeded":
    raise RuntimeError(tuple(item.code for item in parsed.diagnostics))
csv_file = parsed.value.representation
print(csv_file.identity.sha256)
```

Pass `expected_sha256` to `SourcePayload` when replaying an independently
identified original. Use `write_verified_bytes` for a separate storage
operation. Supply the destination, exact bytes, expected digest and an
explicit FileStore. Inspect the returned status before reporting completion.

For network acquisition, construct an approved `HttpTransport` and pass it
to `acquire` or `capture`. Domain discovery returns official release links
and dates. The caller supplies the selection and controls repetition.

The offline examples `parse_offices_from_bytes.py` and
`acquire_store_parse_notify.py` use the synthetic office HTML fixture.
The second example substitutes a recorded HTTP response and an in-memory
notification acknowledgement.

[Operation and effect contracts](../current-how/universal-business-core.md)

[Managed bindings, JSON invocation and workbook preview](../current-how/core-execution-and-admission.md)

## Receive an original and replay it later

```python
from datetime import date

from stratbox.base.filestore import LocalFileStore
from stratbox.base.net import HttpRequest, HttpsEndpoint, RequestsTransport
from stratbox.execution.originals import (
    OriginalDestination,
    ReadOriginalRequest,
    ReceiveOriginalRequest,
    ReceiveToStoreRequest,
    read_original,
    receive_to_store,
)
from stratbox.macrobanks.cbr_offices import ParseOfficesRequest, parse

host = "www.cbr.ru"
path = "/banking_sector/credit/cstat/"
request = HttpRequest("GET", f"https://{host}{path}", (HttpsEndpoint(host, path),))
source = ReceiveOriginalRequest(request, "cbr-offices", frozenset({"text/html"}))
store = LocalFileStore("originals")
saved = receive_to_store(
    ReceiveToStoreRequest(source, OriginalDestination("offices.html")),
    transport=RequestsTransport(),
    store=store,
)
if saved.outcome != "succeeded":
    raise RuntimeError(tuple(item.code for item in saved.diagnostics))

replay = read_original(ReadOriginalRequest(saved.value.material), store=store)
if replay.outcome != "succeeded":
    raise RuntimeError(tuple(item.code for item in replay.diagnostics))

capture_day = date.fromisoformat("2026-11-12")  # Supply the actual capture date.
parsed = parse(ParseOfficesRequest(replay.value, capture_day))
```

Use `saved.value.storage` with `ReconcileOriginalRequest` after an unknown
commit. The reconciliation result describes the observed destination under
the same effect key. For a later conditional read, pass a stored original
as `ReceiveToStoreRequest.baseline`. In the local profile the original is
reopened, checked by revision and SHA-256, and copied in bounded chunks.
For managed acquisition with a stored reference, the current path requests
a full representation. An inline baseline can use the transport's
`verify_baseline` hook.

## Work with changing workbook layouts

Use `preview_workbook(data, sheet=..., start_row=..., max_rows=...)` to
inspect a range. For OFFICES-REG, pass `sheet`, `national_row` and
`last_row` to `ParseOfficesRegRequest` for an explicitly selected fragment.
The qualification reports its scope and the affected fields.

The industry domains accept the result of `build_stream` as the input to
`CalculateApkRequest` or `CalculateIssuanceApkRequest`. Pass the APK result
to the matching `build_pivots` and then pass the pivot set to
`render_pivots`. Use the parent receipts in `rendered.computation` to
retrieve the stream and workbook identities. A caller can pass a separate
DataFrame for a local analysis with its own source identity.
