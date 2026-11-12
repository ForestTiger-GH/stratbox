# Install and call the core library

Stratbox 0.9 requires Python 3.10 or later. Install the verified wheel into
the interpreter that runs the caller. In Jupyter or Colab use `%pip install
/path/to/stratbox-0.9.0-py3-none-any.whl` in the target kernel.

| Install profile | Use |
| --- | --- |
| Base | Typed contracts, local storage, daily OFFICES, SME JSON and territorial office XLSX parsing. |
| `http` | Built-in Requests HTTPS adapter. A supplied transport can satisfy the same contract. |
| `dataframe`, `excel` | Banking analytics and workbook rendering. The `excel` extra also supplies the 1-YUR OOXML reader. |
| `excel-legacy` | 1-YUR BIFF/XLS and legacy Excel format commands. |
| `dbf`, `rar` | Bank form DBF and an explicitly constructed `RarArchiveReader`. Compressed RAR members can require a system extractor. |
| `sors-restoration` | SORS analytical dependencies and HiGHS for the global feasibility and optimization stages. |
| `excel-binary`, `pdf`, `documents`, `dbf-write` | Additional format commands. |
| `test` | Local test environment with the dependencies used in the suite. |

For an independently installed wheel, provide the selected extras on the
wheel path, for example `python -m pip install
'./stratbox-0.9.0-py3-none-any.whl[http,dataframe,excel]'`.

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
