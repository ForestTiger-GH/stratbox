# Minfin — Ministry of Finance of the Russian Federation

This is an independent publisher-owned domain. It deliberately does **not** introduce a second operation runner, a cross-domain `SourceCatalog`, a background scheduler, or physical storage policies. All `REGISTRY_*.yaml` source records live directly in the `minfin/` package root, as the domain's canonical declarations.

## Four publication families

| Registry | Publisher landing page | Recognized series in supplied 2026-11-22 HTML |
| --- | --- | --- |
| `REGISTRY_FEDBUD.yaml` | `https://minfin.gov.ru/ru/statistics/fedbud/execute/` | Annex 3, monthly / quarterly / annual XLSX |
| `REGISTRY_CONBUD.yaml` | `https://minfin.gov.ru/ru/statistics/conbud/execute` | Annex 8, monthly / quarterly / annual XLSX; includes state extrabudgetary funds |
| `REGISTRY_SUBBUD.yaml` | `https://minfin.gov.ru/ru/statistics/subbud/execute` | Annex 6, monthly / quarterly / annual XLSX; consolidated budgets of regions |
| `REGISTRY_NWF.yaml` | `https://minfin.gov.ru/ru/perfomance/nationalwealthfund/statistics/` | NWF management XLSX, VEB deposit DOC, fund-volume DOCX, preferred-share DOCX |

The saved HTML pages contained 13 recognized files in total. Their links and **full document `title` attributes** are used as evidence in the offline tests. Other files on future or paginated pages are recognized as unclassified candidates and are never silently discarded merely because the registry has no special variant for them.

The registry format is the JSON subset of YAML 1.2 (`.yaml` files) to retain the dependency-free core install. It records source identity, known publisher link patterns, the *source's description* of publication basis and logical operation IDs. No dynamic state (`last_seen`, file paths, access tokens, schedules, notification recipients) is stored there. Loading it uses `importlib.resources` so packaged wheels and source installs behave alike.

## Independent operations

| Operation | Responsibility |
| --- | --- |
| `minfin.discover` | Inspect caller-supplied or fetched HTML for bounded publisher-file candidates. Returns **unknown inventory coverage**. |
| `minfin.inspect` | Compare available candidates, without claiming publisher revisions or absence. |
| `minfin.acquire` | Obtain a specifically selected official asset with HTTP receipt and basic envelope checking. |
| `minfin.capture` | Convenient acquisition + source-cell extraction for table-compatible formats. |
| `minfin.extract` | Extract XLSX/XLSM/XLS/CSV or an explicitly chosen spreadsheet member of a ZIP, preserving cells, formulas and cached formula values; comments and merged-cell layout require separate coverage qualification. |
| `minfin.validate` | Check structural geometry, missing formula cache, blank sheets; **not** economic equivalence. |
| `minfin.compare` | Compare cell coordinates **and** sheet membership/geometry for compatible source editions. |
| `minfin.serialize` / `minfin.read_representation` | Reversible JSON representation of source-cell extracts including empty-sheet geometry. |
| `minfin.map_observations` | Convert **explicitly supplied/reviewed cell bindings** to typed metric/period/geography/unit values. No inferred budget codes. |
| `minfin.render_csv` | Render source-cell observations as deterministic UTF-8 CSV. |
| `minfin.readable` | Partial text-only PDF/DOCX reading. Legacy binary DOC can be acquired but requires an external, separately qualified converter. |

For untouched originals use the shared `source.save_original` / `source.read_original` operations with caller-chosen storage. This domain does not change their contracts. The `operation_catalog()` automatically discovers this one root owner through `_registration.py`.

## Offline usage

```python
from pathlib import Path
from stratbox.shared.evidence import SourcePayload
from stratbox.domains.minfin import DiscoverRequest, ExtractRequest, discover, extract

html = SourcePayload(
    Path("page.html").read_bytes(), "text/html", "minfin.fedbud.index", charset="utf-8"
)
index = discover(DiscoverRequest("minfin.fedbud", index=html))
assert index.outcome == "succeeded"
for asset in index.value.assets:
    print(asset.source_id, asset.filename, asset.label)

# Start a *separate* operation from a locally retained original. The original
# file bytes, not the page, are supplied; no network call is made.
original = SourcePayload(
    Path("published.xlsx").read_bytes(),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "minfin.fedbud.annex3.monthly",
)
result = extract(ExtractRequest("minfin.fedbud", original, "xlsx"))
assert result.outcome == "succeeded"
print([(sheet.name, len(sheet.cells)) for sheet in result.value.sheets])
```

Use `MapRequest(..., bindings=(MetricBinding(...),))` only after separately verifying a particular workbook layout, reporting period, units and classification meanings. The official HTML title marks monthly and quarterly budget tables as **cumulative since the beginning of the year**; this hint never automatically converts source cells into monthly flows. A source filename's folder date is not a statistical observation date.

## Qualification and scope

- **HTML evidence:** Four actual saved publisher pages, observed 2026-11-22. They show 3 + 3 + 3 + 4 currently visible files; dynamic/paginated historical inventories may be broader.
- **Binary evidence:** The corresponding 13 official files were not attached. Structural parsers are covered by synthetic Excel fixtures. Exact budget headings, official classification codes, historical layout variations, economic row bindings and non-text PDF/DOCX information remain unverified against native binaries.
- **Source change:** Stable source IDs are separate from URLs, issuer issue identities and byte digests. Source inventory comparison with unknown coverage cannot claim an official publication was removed. Real material revisions require downloaded bytes and a qualified baseline.
- **Stages:** Integration, ingestion, calculated economic summaries and external publication remain visible as gaps for later domain work. This is an explicit scope boundary, not an executable stub that returns fake success.
- **Safety:** Only official HTTPS upload paths are admitted. Untrusted HTML `base` is rejected; redirects must stay within declared hosts/path roots. Book/ZIP admission uses existing bounded core primitives. The domain never chooses a storage destination or a network schedule.