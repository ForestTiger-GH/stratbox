# Ministry of Finance (Minfin) — Source Profiles and Independent Operations

The Minfin domain is the first Strategy Box source pilot with a **four-part
separation**: logical **sources**, subject-specific **profiles**, independently
callable **operations**, and caller-owned **plans/checkpoints**. It implements
four publisher families and ten XLSX statistical series (three monthly, three
quarterly, three annual budget series and one monthly NWF workbook). Three
historical NWF DOC/DOCX assets remain in publisher discovery but outside the
standard flake preparation route.

All `REGISTRY_*.yaml` declarations live **at the domain root**. They do not
contain filename patterns, Python paths, execution recipes, message routes,
checkpoint data, schedules or duplicate operation-ID inventories. Each record
carries source/series identities, economic period characteristics and **stable
profile IDs**. A location is only a publication entrypoint, not an identity.

## Directory responsibilities

```text
minfin/
├── REGISTRY_FEDBUD.yaml
├── REGISTRY_CONBUD.yaml
├── REGISTRY_SUBBUD.yaml
├── REGISTRY_NWF.yaml
├── __init__.py               # compact public API, lazy handlers
├── _registration.py         # the one operation owner, "minfin"
├── publications/
│   ├── contracts.py         # source identity, publication/material/processing evidence
│   ├── catalog.py           # bounded discovery and strict decoding of root registries
│   ├── profiles.py          # document-card and asset identification profiles
│   ├── access.py            # explicit publisher HTTPS admission
│   ├── discovery.py         # source index parsing, classification, conflict detection
│   ├── materials.py         # acquisition and readable-document adapters
│   └── updates.py           # marker-first evaluation and checkpoint candidates
├── tables/
│   ├── contracts.py         # exact source cells, flake and mapping contracts
│   ├── profiles.py          # approved table geometries and cleaning method identities
│   ├── extraction.py        # source-native reading, validation and cell comparison
│   ├── cleaning.py          # profile-based source-local flake preparation
│   ├── periods.py           # period normalization (including trailing footnote marks)
│   ├── mapping.py           # explicit source-cell/metric binding
│   └── representation.py    # reproducible extract and clean-flake representations
├── analytics/
│   ├── contracts.py         # headline and notification-candidate schemas
│   ├── profiles.py          # reviewed budget/NWF calculation dispatch
│   ├── indicators.py        # calculations and like-for-like YoY comparisons
│   └── notices.py           # channel-neutral, deterministic notice facts
└── operations/
    ├── contracts.py         # cross-stage capture contract
    ├── bindings.py          # strict source/series → profile resolution
    ├── definitions.py       # the same 17 OperationDefinition objects
    └── handlers.py          # thin adapters to the existing core runner
```

The domain never creates a second operation runner, background scheduler,
network transport, file store, delivery service, or public extension system.
`stratbox.core.execution` retains ownership of invocation, evidence, outcomes,
resource limits and `OperationCatalog`. All 17 operation IDs remain discoverable
through the single domain owner declared in `_registration.py`.

## Registry and profile contract

A source family may contain several statistical series. Each `REGISTRY_*.yaml`
uses the JSON-compatible subset of YAML 1.2 and the declared schema
`stratbox.minfin.registry.v2`. `publications/catalog.py` discovers **all**
root `REGISTRY_*.yaml` files using `importlib.resources`, with strict shape,
uniqueness, safety and bounded-inventory validation. Adding a source descriptor
does not require editing a hard-coded Python filename list.

```json
{
  "schema": "stratbox.minfin.registry.v2",
  "family_id": "minfin.fedbud",
  "publisher_id": "minfin",
  "title": "Federal budget execution",
  "location": {"kind": "publication_page", "url": "https://minfin.gov.ru/ru/statistics/fedbud/execute/"},
  "profiles": {
    "discovery": "minfin.document_cards.v1",
    "identification": "minfin.fedbud_assets.v1",
    "table": "minfin.budget_table.v1",
    "metrics": "minfin.budget_headlines.v1"
  },
  "series": [
    {"source_id": "minfin.fedbud.annex3.monthly", "slot": "monthly",
     "title": "Monthly federal budget", "periodicity": "monthly",
     "basis": "ytd", "kind": "table"}
  ]
}
```

Example above is abbreviated to one series; the actual registry contains all
three. Profile IDs refer to statically registered **typed** domain profiles,
never dynamically imported callable names. `operations/bindings.py` validates
publisher-profile, series-slot, format, frequency and economic-basis matches.
Validation is available independently of running an operation using
`validate_all_profiles()`.

The publisher-card profile knows how Minfin exposes per-document `Опубликовано`
and `Изменено` markers; identification profiles know the actual official
publisher document IDs, file signatures and admitted formats. A verified
publisher document ID still identifies a logical series after its XLSX
filename changes. Contradictory document ID and filename evidence is reported
as **conflicted**, not accepted as a new or changed statistical series.
The discovered index has `coverage="unknown"`; absent links on a partial page
do not prove absence from the publisher's full inventory.

Table profiles define column roles, accepted native formats, header limits,
period normalization and method versions. The actual cleaning algorithm accepts
a resolved `TableProfile`, frequency and economic basis: it does not read
registry files or select behavior through `if family_id`.

Calculation profiles dispatch to reviewed budget/NWF methods through fixed
callables registered in Python. They have separate economic basis and
periodicity admission rules; no YAML text is evaluated as code.

## Execution and data lifecycle

```text
Source Registry → Source/Series Binding → Publication Discovery
                                           │
                                           ▼
                                      Update Preflight
                                           │
                    ┌──────────────────────┴─────────────────────┐
                    ▼                                            ▼
              Skip download                           Source Acquire (if needed)
                    │                                            │
                    └─────────── Retained/Acquired Source ────────┘
                                                       │
                                                       ▼
                                         Exact cells → Source Flake
                                                        ├──→ CSV representation
                                                        └──→ headline calculation
                                                                   │
                                                                   ▼
                                                        neutral notice candidate
```

The **consumer** chooses which independently callable operations to invoke.
A `profile` is not an ordered recipe or task runner; `OperationCatalog` owns
operation definitions. `SourceCheckpoint` makes independent publisher, material
and method state views available through `.publication`, `.material`, and
`.processing` properties. Marker preflight is a cheap decision, not proof of
byte equality. A same-byte rediscovery does not by itself authorize a notice.
A parser-profile change can require reprocessing a retained original without
downloading again. The effective flake method version is taken from the
resolved table profile unless a caller deliberately provides another method
identity. Checkpoint persistence follows the consumer's confirmed storage
boundary and is never performed by the pure Minfin domain.

Monthly and quarterly budget values remain source-reported cumulative YTD.
Annual budget values remain annual. NWF values are monthly stocks; liquid
assets are the **derived** total minus assets placed in other permitted
instruments, not an independent source observation. Like-for-like growth
compares the same month, quarter, or year in the previous year. Publication
modification dates do not replace economic observation periods.

For Tabularium, `minfin.build_flake` yields a table of indicator codes, labels,
normalized period headers and exact values. `minfin.render_flake` produces a
portable CSV (without document notes or header decoration). Neither operation
owns the target path or persistence. For notifications, `minfin.summarize`
yields a typed economic summary and `minfin.prepare_notice` yields an eligible,
deterministic candidate; the event journal, notification service, Telegram
formatting, deduplication and delivery are responsibilities of higher layers.

## Offline caller example

```python
from pathlib import Path
from stratbox.shared.evidence import SourcePayload
from stratbox.domains.minfin import (
    bind_series, BuildFlakeRequest, ExtractRequest, RenderFlakeRequest,
    SummaryRequest, extract, build_source_flake, render_source_flake,
    calculate_headlines,
)

series_id = "minfin.fedbud.annex3.monthly"
binding = bind_series("minfin.fedbud", series_id)
assert binding.table is not None and binding.metrics is not None

payload = SourcePayload(
    Path("Prilozhenie_3_dannye_109-111_—_mes.xlsx").read_bytes(),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", series_id,
)
raw = extract(ExtractRequest("minfin.fedbud", payload, "xlsx"))
assert raw.outcome == "succeeded", raw.diagnostics
flake = build_source_flake(BuildFlakeRequest(raw.value, series_id))
assert flake.outcome == "succeeded", flake.diagnostics
csv_result = render_source_flake(RenderFlakeRequest(flake.value))
headline = calculate_headlines(SummaryRequest(flake.value))
assert csv_result.outcome == "succeeded" and headline.outcome == "succeeded"
```

## Verified scope and limits

The domain's source-specific profiles were checked offline against the four
saved Minfin HTML pages (3+3+3+4 visible assets) and eleven provided XLSX
snapshots (nine budgets and two successive NWF monthly files). The simple
publisher HTML does not guarantee a complete historical inventory.

No permanent source binaries are bundled. Repository tests use small synthetic
material fixtures, including publication-card modification dates, renamed
attachments, conflicts, retained-input processing and financial consistency.
A complete installed-package test and live publisher acquisition remain
necessary before enabling a production scheduled consumer.

**Out of scope here:** generalizing `SourceCatalog`/`ProfileCatalog` into
`core`, changing any other publisher domain, persistent cross-source databases,
platform-specific scheduling and machine-protocol servers.