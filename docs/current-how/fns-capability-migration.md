# FNS retained evidence, observations and products

The SME register and Form 1-YUR execute through the common capability catalog,
preparation service and bounded session. Both families expose physical
extraction, reviewed projection, semantic alignment, calculations, views,
rendering and portable replay as independent operations. Source acquisition and
storage are explicit effects.

## 1. Independent scientific boundaries

| Boundary | SME register | Form 1-YUR |
| --- | --- | --- |
| Physical extraction | Every supplied record, field, JSON type and literal token. | Every decoder-visible cell of every admitted workbook, archive inventory, formulas and available cached values. |
| Reviewed projection | Every present reviewed counter at each supplied geographical level. | Reviewed Part I indicators and complete legal-kind sheets under the observation date's layout epoch. |
| Alignment | Explicit aliases of the nine published counters. | Dated identity mapping of reviewed source fields and legal kinds. |
| Qualification | Missing counters remain absent; unknown fields remain in physical evidence. | Omitted fields, unselected members, sparse sheets and unresolved flow bases remain explicit. |
| Geography | Source country, district and subject namespaces remain separate. | Published country, district and territory rows retain their source perimeters. |

An archive or JSON asset can be physically complete while its analytical
projection remains partial. The reviewed June 2019 sparse legal-kind edition
retains all sheets and reports the excluded incomplete categories. The same
sparsity in an unreviewed edition fails the reviewed projection. Part II can be
retained and inspected independently; it does not acquire Part I semantics.

## 2. Callable route and publication context

```python
from datetime import date
from stratbox.sdk import StrategyBox
from stratbox.shared.evidence import SourcePayload
from stratbox.domains.fns.publications.contracts import ReleaseContext

release = ReleaseContext("fns.sme", "2026-11-10", date(2026, 11, 10))
with StrategyBox() as box:
    result = box.invoke(
        "fns.sme.process",
        inputs={"payload": SourcePayload(source_bytes), "release": release},
    )
    physical = result.output("flake")
    source_observations = result.output("projection")
    integrated = result.output("dataset")
    prepared_view = result.output("view")
    encoded_product = result.output("representation")
```

`fns.1yur.process` uses the same named inputs and outputs. `extract`, `project`,
`align`, `view` and `render` can each run separately. `view_calculation` prepares
a view from an accepted calculation. Supplied output references stop upstream
work: rendering a retained view requires neither an original asset nor an
acquisition provider.

`capture_full` first runs the family's explicit acquisition operation and then
the same processing scenario. Its `release` input carries the issue and
observation date; the returned context records the actual capture timestamp
separately. SME acquisition uses the official read-only POST endpoint. Form
1-YUR additionally requires the dated official link as the `url` parameter.

`discover` enumerates a supplied `index` payload. Form 1-YUR requires `year` and
the specific publisher index `base_url`. `discover_online` acquires an explicit
`index_url` before invoking the same parser. Closed discovered membership
describes that index's observed members; it does not prove complete history.

## 3. Retained layers and regional CSV

Each family supplies `{layer}_snapshot` and `read_{layer}_snapshot` for `flake`,
`projection`, `dataset`, `calculation` and `view`. The snapshot contracts retain
publication context, periods, metric definitions, raw status, source uses,
coverage, qualifications, field dispositions and lineage. Replay validates the
specific family and layer and requires no original decoder. Generic snapshot
encoding, storage and publication consume these values through the neutral
stage operations. Replay inputs also admit a generic dataset-store envelope;
the embedded manifest still has to match the exact family and scientific layer.

`parse` is a regional product scenario: it retains full physical evidence and
returns an independently encoded regional CSV. `regional_product` generates
that CSV from retained evidence. `read_representation` admits an already saved
regional CSV directly as a partial dataset. Its byte identity is preserved;
source fields outside that CSV and the original workbook or JSON remain
explicitly unavailable. A CSV dataset can participate in subsequent calculation
runs under the same scientific admission rules.

## 4. Calculation and revision meaning

`compare_flakes` and `compare` report changes in literal source cells and JSON
tokens for the same issue. `compare_datasets` compares qualified economic
observations. `calculate_changes` requires two matching reported stock datasets
at strictly ordered dates and retains both input versions. The result is a net
stock change, with an explicit qualification that it does not measure births,
registration entries or exits. Shares require matching subjects, periods,
perimeters, metric definitions and explicit numerator/denominator selections.
National, district and subject aggregates remain distinct observations.

The catalog pins reviewed extraction/projection profiles and field-mapping
fingerprints. An additional reviewed method/profile can specialize the same
operation contract without changing the compiler, executor or generic parser
selection. Unsupported source layouts fail at their scientific boundary.
