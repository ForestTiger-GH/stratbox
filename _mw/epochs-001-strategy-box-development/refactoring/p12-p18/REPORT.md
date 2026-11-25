# Canonical processing stages, domain routes and supplied tasks

Date: 2026-11-25. Scope: P12-P18. Status: executable route migration implemented; publisher-edition and financial-model obligations remain qualified. Full plan closure is pending those obligations and the separately scoped public/machine and transition-owner packages.

The implementation connects the complete declared source inventory to typed capabilities and one preparation/execution service. Source-stage coverage is audited independently from scientific support for particular publisher editions. A callable method requiring a reviewed field profile does not certify an unavailable original or provide an absent financial formula model.

## 1. Implemented routes

| Package | Implemented behavior | Verification owners |
| --- | --- | --- |
| P12 | Independent acquisition/read/preservation, bounded archive members, readable and document/workbook extraction, semantic snapshots/replay, explicit alignment, memory/file dataset ingestion/query, reference editions, revision transitions and coherent publication | Standard-stage and generic-admission tests; materials and processing regression suites |
| P13 | All 57 CBR sources and 156 declaration dispositions; explicit collection folds, financial/source-field boundaries, APK and SORS method routes, source products and physical evidence | CBR capability, publication, collector, reporting-form, statistical workbook and scientific regression suites |
| P14 | Both FNS families and 62 declaration dispositions; full JSON/workbook evidence, reviewed projections, exact historical epochs, stock calculations, products and independent replay | FNS scientific and canonical integration tests |
| P15 | All 13 Minfin sources and 34 declaration dispositions; fiscal periods/units, source documents, explicit DOC conversion, reviewed document fields, separate economic calculation and storage | Minfin physical, source, semantic and canonical tests |
| P16 | All 14 Frank sources and 32 declaration dispositions; physical extraction, strict reusable reviewed layout bindings, calculations/history, explicit archive and cleanup effects | Frank physical/scientific/canonical tests and unknown-effect receipt regressions |
| P17 | All four Rosstat families and 36 declaration dispositions; KEP2 mixed frequency, source-native geography, reviewed population/industrial editions, archive evidence and retained products | Rosstat publication, scientific, canonical and retained-store tests |
| P18 | Source recipes, exact reusable scenarios, frozen cascade membership, pinned child/method identities, independent required completions, coherent products and explicit release manifests | Supplied workflow, ordered fold, hierarchy and retained-release integration tests |

Coverage verification retains dispositions for all 356 original declarations, 90 sources, 1,350 source-stage cells, 144 profiles and 19 templates. The machine report is `coverage.json`; its route admission status is distinct from publisher certification.

## 2. Common contracts corrected during integration

Input and output ports retain accepted outcomes and explicit schema alternatives. A generic technical consumer can accept an arbitrary schema while retaining its outcome, qualification, coverage and type checks. The enclosing operation validates its own used input boundary before forwarding a value to that consumer. Actual retained ValueEvidence survives a new direct invocation.

Partial results expose only permitted ports. Optional absent outputs remain absent; raw unknown-effect values and receipts survive without a successful output claim. Accepted values are checked again after ownership transfer under the same outcome rules. Generic dataset wrappers can reach domain replay codecs; each codec still validates the actual manifest, family and layer.

Canonical collection folds expose individual members, attempts and aggregate limits. A failed member retries independently. Required completion roots remain in the plan when another output is selected and allow an independent accepted output to be used while other work continues. Optional goals, actual completion checks and confirmed effects have separate consequences.

Scenario references retain child definition and resolved method/profile/group/schema/reference identities. Catalog reconstruction cannot silently replace an authored exact binding. Membership selectors freeze their admitted scenario set, including when a matching definition is added during a live run.

## 3. Reviewed publisher scope and remaining obligations

| Scope | Available implementation | Remaining obligation |
| --- | --- | --- |
| CBR forms 134 and 803 | Reviewed published numeric-field layouts, literal/typed values, source identities, units and explicit period admission; source-level alignment, views and admitted ratios | Financial formula models and their control fixtures; broader historical editions |
| CBR territorial-office workbook decoding | Dedicated qualified lexical OOXML reader with source-specific header/formula evidence | Consolidation of this method with the shared workbook decoding path |
| Historical CBR escrow HTML | Original preservation and explicit unsupported interpretation diagnosis | Reviewed historical business interpretation |
| Frank RG 14 series | Physical evidence, byte-bound and reusable exact reviewed layout contracts, strict anchor/unit/period checks and full downstream routes | Actual licensed publisher originals and built-in reviewed semantic layouts for the promised editions |
| Minfin NWF documents | Ordered physical blocks, independent conversion identities, reviewed field profiles, source-qualified observations, ratio and replay contracts | Real publisher document editions and reviewed economic field mappings; official originals returned HTTP 503 |
| Rosstat socioeconomic Russia PDF | Physical document evidence and exact reviewed geometry/semantic mapping mechanism | Actual publisher PDF original and reviewed automatic layout; official source returned HTTP 503 |

Actual Rosstat population originals for 2022-2024 and regional industrial workbooks for June/August 2026 were examined. Population 2024 native codes are TERSON-MO, not OKTMO; repeated codes and distinct population perimeters retain separate identities. Regional monthly, YTD and previous-month indices retain different bases and source notes. Verification applies to those explicit layouts and profile scopes.

Synthetic fixtures establish execution and reviewed-profile contracts within their stated conditions. They do not replace the missing publisher originals above. `--require-publisher-evidence` intentionally fails while these obligations remain open. External durable hosting and the actual external protocol adapter remain H01/H02.

## 4. Reproduction and validation

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
python -B scripts/check_capability_migration.py
python -B scripts/check_internal_imports.py
python -B scripts/check_release_integrity.py
python -B scripts/check_readme_links.py
python -B scripts/admit_registry.py --level executable
python -B scripts/reference_editions.py verify --reference all
PYTHONDONTWRITEBYTECODE=1 python -m build --no-isolation
```

The final code tree `98cb13bd803fb04161eaafbf4e76397166f5c3d8` passed 2,075 tests with 7 skipped in 521.92 seconds. The tested tree stayed unchanged during that run. The validation record identifies the implementation commit, commands and exact distribution digests. Cold metadata admission is tested without optional numerical, workbook or HTTP packages. A separately installed wheel runs a canonical command outside the checkout. No GitHub Actions are used.
