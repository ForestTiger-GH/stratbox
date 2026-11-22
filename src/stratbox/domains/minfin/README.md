# Minfin source operations

Minfin owns logical statistical series, publisher recognition, source-cell
extraction, source-local flake cleaning and headline calculations. The core owns
execution, provider selection, storage, archive creation and data handoff.

## Source declarations and acquisition

Root `REGISTRY_*.yaml` files use `stratbox.minfin.registry.v3`. They contain
logical identities, frequency/basis and registered profile IDs. Physical URLs,
paths and filenames are outside these records. Typed acquisition profiles in
[publications/profiles.py](publications/profiles.py) hold convenient official
landing-page defaults. `DiscoverRequest.page_url` overrides the default;
`DiscoverRequest.index` supplies already acquired HTML. A supplied input is
used exclusively, including when its content is invalid.

`discover`, `acquire` and `capture` accept an HTTP `ProviderSelection` alongside
an `ExecutionContext`. Offline `extract` accepts the same `SourcePayload`
obtained through any admitted source adapter. Domain parsing and economic rules
are independent of whether the bytes came from HTTPS, a disk or a retained
material reference. Publication index coverage remains unknown.

## Complete flake replay and database snapshots

`build_source_flake` returns a typed `FlakeTable`. `serialize_source_flake` and
`read_source_flake` provide a complete versioned JSON interchange preserving
original byte identity, source coordinates, period headers, exact value strings,
nulls, economic basis, method version and unit hints. `render_source_flake`
exports a readable CSV; the JSON codec restores the complete typed value.
Source-cell extracts have the separate `serialize_extract`/`read_representation`
pair. Representations can be retained through the core material operations in
any supported store.

`build_flake_snapshot` exposes the same flake as a logical dataset with typed
metadata, columns and rows. `read_flake_snapshot` validates all three components
and restores the original domain value. The generic dataset reader/writer can
use an application adapter or an immutable file-backed snapshot without changing
headline calculations. Selected components remain partial and cannot be decoded
as a complete flake. Exact nullable text values are preserved without automatic
numeric conversion.

The [table contracts](tables/contracts.py) and [operation definitions](operations/definitions.py)
are the public semantic owners. [Profile binding](operations/bindings.py) validates
registered series, publisher rules, economic basis and calculation methods.
Every table transformation records its actual canonical typed input, parameters
and output identity. Changed values or changed original evidence produce
separate computation keys even when a CSV export happens to be identical.

```python
from stratbox.domains.minfin import (
    ExtractRequest, BuildFlakeRequest, SerializeFlakeRequest, ReadFlakeRequest,
    SummaryRequest, extract, build_source_flake, serialize_source_flake,
    read_source_flake, calculate_headlines,
)

# payload is a SourcePayload supplied by the chosen acquisition operation.
raw = extract(ExtractRequest("minfin.fedbud", payload, "xlsx"))
assert raw.outcome == "succeeded", raw.diagnostics
flake = build_source_flake(BuildFlakeRequest(raw.value, payload.source_id))
assert flake.outcome == "succeeded", flake.diagnostics
encoded = serialize_source_flake(SerializeFlakeRequest(flake.value))
assert encoded.outcome == "succeeded", encoded.diagnostics
restored = read_source_flake(ReadFlakeRequest(encoded.value))
assert restored.outcome == "succeeded", restored.diagnostics
summary = calculate_headlines(SummaryRequest(restored.value))
```

## Economic and consumer boundaries

Monthly and quarterly budget figures retain their cumulative YTD basis; annual
figures remain annual. NWF stocks retain mixed row units, and the headline
profile derives liquid assets from its specifically reviewed rows. Publication
dates never replace observation periods. Historical flake methods survive
replay; calculation admission still checks the registered method and basis.

Caller-owned checkpoints distinguish publisher markers, exact material identity
and processing method. They are persisted after confirmed storage. Source
monitoring, cross-source integration policy, scheduling, notification delivery
and application database lifecycle belong to their consumers. The three
historical NWF document series remain outside the workbook flake route.
