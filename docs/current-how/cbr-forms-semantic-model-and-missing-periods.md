# Current HOW — regulatory forms, semantic indicator models and skipped source dates

**Evidence status:** direct read-only code and model schema review at pinned `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`; no downloaded regulatory archive, live run or Excel package test was executed in this consolidation. The subject owner is `src/stratbox/macrobanks/cbr_forms`.

## 1. Supported user-facing work and physical domain structure

The public [`run_all_forms_to_xlsx`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/api.py) selects forms, dates and a legacy bank registry, downloads requested archive periods and writes one XLSX per form. The [form registry](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/forms/registry.py) includes **101, 102, 123, 135, 802 and 805**; 802 uses a quarterly cadence and the `hierarchical_statement` Excel profile. The API expressly rejects any `banks_mode` other than `legacy`, and a missing reporting-date range is skipped with an informational print.

Physical loading is deliberately separated from semantic definition:
```text
form module: official archive address + DBF layout + physical field/channel normalization
  → physical normalized records
model/formXXX.csv: stable IndicatorId, kind, source code, measure, hierarchy, units
  → semantic canonical long
Excel profile: pivot and presentation only
  → downloadable workbook
```
This architecture is a meaningful local example of source versus semantic model versus artifact representation. It does not establish that all domain forms already share the same completeness, validation and physical-layout guarantees.

## 2. Stable semantics are supplied by versionable CSV models

The [model loader and validator](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/common/models.py) enforces exact headers, form identity, nonempty unique `id` and `order`, allowed `kind`/`unit`, required fields for direct/formula/passthrough and parent relations within a dataset. Every form has its own `models/formXXX.csv`, with columns `form,order,id,kind,dataset,source_code,parent_code,measure,name,expression,section,unit,params`.

`direct` binds an original row code; `formula` calculates an analytical indicator; `passthrough` represents source-defined rows without hand-copying them into the model CSV. Their presence in a schema does not prove equal implementation maturity for every form.

Canonical long carries a stable `IndicatorId` independently from the Russian display name. This is necessary because the same bank balance-sheet label can appear in multiple official source rows. A pivot keyed only by display name can overwrite or conflate distinct source meanings. The canonical long has fields such as Form, Date, REGN, Bank, IndicatorId, Code, Indicator, Section, Measure, Value and Unit.

## 3. Full 802 versus derived report views

The [802 form module](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/forms/form802.py) directly binds required physical fields `REGN_GKO`, `STR`, `VSEGO`; historical correction channels `KORR_P`, `KORR_M`, `KORR_GR` are optional source features. The standardized long uses **`measure=total`**, while `run_raw` preserves all available physical channels with a stable empty representation for absent optional adjustments. The [semantic model](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/models/form802.csv) contains **86 official rows**. The [domain README](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/README.md) reports **34 top-level rows**; those are distinct from the full hierarchy.

The [Excel profile builder](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/common/excel_profiles.py) creates:
- `Обзор`: only top-level 802 indicators in indicator→bank order;
- `Полная форма`: 86 rows per bank, ordered using the semantic model, with explicit parent-code-derived indentation and outline levels;
- `Данные`: canonical long plus order, parent and computed hierarchy level for machine reprocessing.

The hierarchy is calculated from `parent_code`, not guessed from punctuation in source labels. The builder detects duplicate `IndicatorId + Bank + Date` keys before pivoting and fails explicitly. This is a meaningful correctness guard: visual convenience does not silently collapse distinct banking measures.

## 4. Failure semantics: missing download periods are currently suppressed locally

The generic [archive runner](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/common/runner.py) resolves an external `unrar`/7z command, fetches bytes and extracts DBF files. At **lines 105–106**, if the transport result is unsuccessful or carries no content, it executes `continue` for that date; the date contributes **no record** to the returned series. This is **current code behavior**, not an approved data-quality policy.

The [API](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/api.py) then iterates forms, handles empty **calendar date grid** separately with `print(... skipped...)`, and builds exports. This route does not in itself prove that a missing downloaded period becomes a typed `SOURCE_UNAVAILABLE` in the final workbook/manifest. A consumer inspecting only the exported file path can mistake a partly populated date series for complete coverage. A missing archive is different from an officially published zero, an empty indicator or a form that is not due for publication.

Additional handling gaps are distinct:
- [DBF selection](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/common/dbf_picker.py) scores files by required field names and preference hints; it ignores unreadable candidate files but reports failure if no usable layout is selected. The chosen layout reflects physical schema detection, not universal validity of source content.
- [RAR extraction](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/common/runner.py) invokes an external tool and raises on missing executable/nonzero exit; production packaging and restricted input safety would need separate review.
- [Workbook output](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/common/output.py) applies a fixed creator/title/category metadata block and presentation styles. That is the actual dated implementation; personal author metadata and a cross-format style set remain **future candidate features**, not current code.
- The full [registry](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/forms/registry.py) is curated and static; calendar defaults and source availability must not be equated with reporting obligation or successful retrieval.

## 5. Negative tests required by the observed design

| Test | Expected honest distinction |
| --- | --- |
| Three dates requested, middle archive times out | Missing date must be visible and distinguishable from a valid zero or publication not due |
| 802 source schema lacks optional `KORR_GR` | Physical correction channel remains missing, standard `total` can still be qualified if valid |
| Two source rows share same Russian text label | `IndicatorId` preserves two independent observations in long and pivot |
| Historical DBF candidate has different field layout | Selection detects compatible fields or fails, rather than reading arbitrary numeric columns |
| Same form requested monthly but reporting cadence quarterly | Actual eligible dates follow registry period semantics; absence of monthly filing must not be called an error |
| Semantic model contains duplicate `id` or a parent-cycle | Explicit model/pivot guard rejects ambiguous hierarchy |
| RAR tool absent or extraction fails | Technical source processing fails explicitly; no fabricated completed form |
| User selects an unsupported bank list mode | API raises; implementation does not silently pretend to support an all-bank registry |

These are proposed end-to-end checks; no passing verdict is claimed.

## 6. Status and scope

**Observed:** six curated forms, one unified API, CSV semantic metadata, an explicit specialized 802 conversion, two Excel profile families, and the exact suppressed-download behavior. **Not established:** complete-period guarantees, live source freshness, all release schema coverage, workbook equality to regulator tables, independent statistical reconciliation, installed package compatibility or browser/Android execution. An approved future work plan should repair or explicitly qualify period missingness and source receipts without silently changing historical form meaning.

Related maintained Science: [source observations and comparability](../science/data-and-knowledge/observation-semantics-comparability-and-claims.md), [format recognition versus support](../science/data-and-knowledge/format-recognition-and-semantic-support.md), [source vintage and replay](../science/data-and-knowledge/source-observation-vintages-and-replay.md). Reopen on actual form-schema revision, a confirmed missing-period failure, or installed pipeline tests.
