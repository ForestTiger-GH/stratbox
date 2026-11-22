# Minfin — source-local budget and NWF data processing

**Scope:** Four publisher families, ten currently selected statistical XLSX streams (three monthly, three quarterly, three annual, and one monthly NWF workbook), publisher date-marker inspection, clean source-local extracts, reproducible CSV representations, limited headline calculations, and channel-independent notification candidates. The data owners and domain-specific rules live under `stratbox.domains.minfin`. Shared acquisition, execution, evidence, format admission, storage and notification delivery remain in `stratbox.core` and `stratbox.shared`.

All four canonical `REGISTRY_*.yaml` records are stored **directly in the domain root**. They describe the source family, variants, periodicity, reporting basis and operation IDs; they do not hold live checkpoints, target directories, bot settings or executable Python references. These YAML files use JSON-compatible YAML 1.2 to keep the base distribution dependency-free. `pyproject.toml` packages them in wheel/sdist.

## Domain directory architecture

The root contains **only** the four canonical `REGISTRY_*.yaml` files, the
single `_registration.py` operation-owner manifest, `__init__.py` and this README.
The internal packages group work by **semantic responsibility**, not by when
an implementation was introduced:

```text
minfin/
├── REGISTRY_FEDBUD.yaml   # canonical source declarations (root-owned)
├── REGISTRY_CONBUD.yaml
├── REGISTRY_SUBBUD.yaml
├── REGISTRY_NWF.yaml
├── __init__.py             # small, lazy public API
├── _registration.py       # exactly one operation owner: minfin
├── README.md
├── publications/           # source identity, discovery, access, revision markers
│   ├── contracts.py
│   ├── catalog.py
│   ├── access.py
│   ├── materials.py
│   ├── discovery.py
│   └── updates.py
├── tables/                 # exact extraction, cleaned flakes, typed representations
│   ├── contracts.py
│   ├── extraction.py
│   ├── cleaning.py
│   ├── periods.py
│   ├── mapping.py
│   └── representation.py
├── analytics/              # source-local calculations and channel-neutral notices
│   ├── contracts.py
│   ├── indicators.py
│   └── notices.py
└── operations/             # only operation contracts and runner adapters
    ├── contracts.py        # cross-stage capture request/result
    ├── definitions.py      # all 17 OperationDefinition declarations
    └── handlers.py         # all 17 callable wrappers
```

Each internal package has an `__init__.py`. No nested package declares a second
`_registration.py`; source-record ownership stays at the domain root. The
`operations` package delegates to independent publisher/table/analytics
functions and the existing `stratbox.core.execution.run` runner. Actual HTTP,
format admission, storage and notification delivery remain provided by the
neutral core and the caller. Cross-stage `CaptureRequest` belongs in
`operations/contracts.py`, rather than making source publication contracts
depend on table extracts. The root API lazily exports the existing operation
IDs and request models. The old `models.py`, `pipeline_models.py`,
`definitions.py`, `pipeline_definitions.py`, `operations.py` and
`pipeline_operations.py` are removed, with no duplicate compatibility layer.

## Source families and confirmed HTML markers

| Root registry | Series | Last `Изменено` marker in supplied HTML, 22 Nov 2026 |
| --- | --- | --- |
| `REGISTRY_FEDBUD.yaml` | Federal budget, monthly; quarterly; annual | 2026-11-12; 2026-11-12; 2026-05-05 |
| `REGISTRY_CONBUD.yaml` | Consolidated RF budget and state extrabudgetary funds, monthly; quarterly; annual | 2026-11-12; 2026-11-12; 2026-05-05 |
| `REGISTRY_SUBBUD.yaml` | Consolidated budgets of RF regions, monthly; quarterly; annual | 2026-11-12; 2026-11-12; 2026-05-05 |
| `REGISTRY_NWF.yaml` | NWF movement and management, monthly XLSX | 2026-11-13 |

The NWF landing page also lists three archival DOC/DOCX reports. They remain discoverable/acquirable, but are **not** members of the ten-XLSX processing contour. All dates above describe publisher **documents**, not observation periods or proof of equality of downloadable bytes. Page coverage remains `unknown` for inventories outside the observed HTML snapshot.

## Processing model

```text
REGISTRY_*.yaml ───► discover page / card dates ───► plan_updates
     │                                                    │
     │                                publisher marker unchanged + confirmed
     │                                checkpoint => skip redundant download
     │                                                    │
     ├──► existing core HTTP/acquire (when required) ──────┤
     │                                                    ▼
     └──► caller-supplied saved bytes ───► minfin.extract (complete source cells)
                                                     │
                                                     ▼
                                         minfin.build_flake (clean, wide series)
                                            │                    │
                                            ▼                    ▼
                                      minfin.render_flake    minfin.summarize
                                            │                    │
                                            ▼                    ▼
                                      CSV Representation  minfin.prepare_notice
                                            │                    │
                                            ▼                    ▼
                                  consumer-owned storage   domain facts candidate
```

**Stages remain independent.** Source discovery never downloads XLSX files. `plan_updates` is pure and takes caller-owned confirmed `SourceCheckpoint` values. An unchanged publisher date and stable document identity/locator allow a cheap skip, subject to the caller's actual retained-material and processing requirements. A missing date, ambiguous document, changed locator or failed prior check yields an explicit state; none is silently called unchanged. The date is an operational optimization, not a content digest. The caller retains the prior SHA-256, commits updated checkpoints only after the necessary downstream effects are confirmed, and may choose occasional forced full verification.

`minfin.extract` preserves source-local cell structure, nonempty values, formula/cache and source digest. `minfin.build_flake` accepts one admitted workbook source and produces a **clean wide table**: two descriptor columns (`code`, `indicator`), then normalized `YYYY-MM`, `YYYY-Qn` or `YYYY` period columns. Preambles, section labels, footnote blocks and trailing footnote markers are omitted. Original column spellings, original cell coordinates and the exact original digest remain available on the `FlakeTable` result; they are not written into the clean CSV. All source numbers retain their source precision. Empty measurements remain empty, not zero. Dates stored as the first or last day of a calendar month map to the same month.

Budget monthly and quarterly values remain **cumulative year-to-date** (`ytd`); annual values remain full-year (`annual`). They are **not** converted into artificial monthly flows. The NWF table is a **monthly stock** (`stock`), with mixed physical units across its auxiliary rows; headline metrics use billion RUB only.

## Source-local headline calculations

`minfin.summarize` selects the latest observed period by default (or an explicit period) and compares it with the **same month/quarter in the previous year**, or with the preceding year for annual tables. Budget metrics are identified by reviewed source codes `1`, `2`, `3` and their labels; their signed balance must equal revenues less expenses to the configured tolerance. NWF uses reviewed source codes `2` and `5`:

- `nwf.total`: row 2, fund volume at period end.
- `nwf.liquid`: row 2 minus row 5, a **Strategy Box-derived** liquid-assets measure.

Year-on-year figures compare like-for-like periods and preserve full Decimal precision in the typed result. If the previous balance is zero, absent or changes sign, a comparison state is returned instead of a misleading growth rate. Consumer presentation can round to one decimal and render a negative balance as a *deficit magnitude*. The core library never hardcodes Telegram formatting.

Validated in a local review against 11 supplied official XLSX originals (nine budget files, October and November NWF versions):

| Source | Latest observation period in the uploaded workbook |
| --- | --- |
| Federal monthly, regional monthly | 2026-10 |
| Consolidated RF monthly | 2026-09 |
| Three quarterly workbooks | 2026-Q3 |
| Three annual workbooks | 2025 |
| NWF `Dannye_20261001.xlsx` | 2026-09 |
| NWF `Dannye_20261101.xlsx` | 2026-10 |

Those observed periods can differ from the publication modification date. The complete XLSX binaries are intentionally **not** checked into this repository; tests use synthetic fixtures. A separate offline check against the eleven provided files confirmed normalized headers without duplicate periods and recovered all source-local headline rows. This does not establish future publisher schema stability.

## Notification boundary

`minfin.prepare_notice` returns a **typed fact candidate**, not a Telegram request or a delivery receipt. It requires an eligible publisher transition, a successfully completed and consistent source-local summary, source SHA-256 and publisher document marker. Ordinary initial observations/backfills are quiet unless the consumer opts in. Repeated preparation of the same revision yields the same `event_key`; the consumer/journal owns deduplication, qualified event recording, subscription, channel routing, retries and delivery confirmation. An unchanged source can still be reprocessed when its parser version changes, without being advertised as a *new publication*.

## Offline use

```python
from pathlib import Path
from stratbox.shared.evidence import SourcePayload
from stratbox.domains.minfin import (
    ExtractRequest, BuildFlakeRequest, RenderFlakeRequest, SummaryRequest,
    extract, build_source_flake, render_source_flake, calculate_headlines,
)

source_id = "minfin.fedbud.annex3.monthly"
payload = SourcePayload(Path("Prilozhenie_3_dannye_109-111_—_mes.xlsx").read_bytes(),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", source_id)
raw = extract(ExtractRequest("minfin.fedbud", payload, "xlsx"))
assert raw.outcome == "succeeded", raw.diagnostics
flake = build_source_flake(BuildFlakeRequest(raw.value, source_id))
assert flake.outcome == "succeeded", flake.diagnostics
csv = render_source_flake(RenderFlakeRequest(flake.value))
assert csv.outcome == "succeeded", csv.diagnostics
headline = calculate_headlines(SummaryRequest(flake.value))
assert headline.outcome == "succeeded", headline.diagnostics
# The caller chooses where to store csv.value.data and how to present headline.value.
```

For the complete page workflow: `discover(DiscoverRequest(family_id, index=SourcePayload(html,...)))` yields assets with publisher `published_on`, `modified_on`, `document_id`; `plan_updates(UpdateRequest(index, checkpoints, selected_sources=...))` returns one decision per selected series. `checkpoint_for(asset, completed_flake)` builds a checkpoint **candidate**; durable state publication is the host's responsibility.

## Explicit boundaries

- **In domain now:** publication-card dates and links; candidate update decisions; source-faithful cell extraction; clean source-local flakes; deterministic CSV bytes; limited budget/NWF headlines; notification-ready neutral facts.
- **Already shared elsewhere:** `OperationResult`, `ExecutionContext`, HTTP, typed input receipts, original storage, package delivery and notifications infrastructure. No replacement runner, scheduler, persistence ledger or messenger was introduced.
- **For later core/generalization:** moving source-registry composition and generic publisher-marker evaluation to a shared, evidence-qualified abstraction after cross-domain pilots; connecting facts to admitted observability schemas and subscription-based notifications; persistent destination-specific processing checkpoints.
- **Out of scope:** database integration, cross-source harmonization, forecasting, Telegram delivery, actual Tabularium Git storage, full visual-readable PDF conversion and unrelated NWF archive DOC processing.