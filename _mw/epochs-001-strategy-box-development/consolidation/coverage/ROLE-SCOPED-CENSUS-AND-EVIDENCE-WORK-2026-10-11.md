# Role-scoped closure plan for 566 frozen Git sources: code evidence versus Research meaning

**Checkpoint:** 2026-10-11. **Status:** verified census grouping and evidence-work triage; **NOT** a source-level terminal disposition, independent semantic assurance or a code safety certificate. The original source IDs and exact blob SHAs remain authoritative in `sources/CENSUS.csv`; this file contains only aggregated public-safe roles and procedural criteria.

## Source universe, counted directly from the frozen census

| Repository / evidence origin | Frozen Git identities | Appropriate treatment |
| --- | ---: | --- |
| Public subject-matter repository `stratbox` | **351** | Research meaning into Science; implementation, tests and old docs as code/evidence/provenance. |
| Public desktop consumer `stratbox-windows` | **198** | Observed Current HOW, desktop/presentation/application contracts, tests and historical generated developer artifacts. |
| Public platform contract input `AppDock` | **17** | External authority and deployment/activation interface **only to the verified public contract revision**. |
| **Total** | **566** | No private implementation content is admitted. |

The census currently has **77 `full_read`**, **10 `governing_read`**, **479 `not_full_read`**. The 77 reads comprise 53 substantive Research originals, three orientation Research READMEs and 21 fully read code/test sources. **566/566 whole-source material dispositions remain `unaccounted`**, even though 53/53 substantive originals now have at least one line-addressed English/quoted knowledge trace.

## Roles and remaining primary-evidence work

| Frozen source role | Total | Already fully read | Not yet fully read | Appropriate subsequent disposition |
| --- | ---: | ---: | ---: | --- |
| Historical Research | 5 | 5 | 0 | Four substantive historical originals preserve time/proposal status; one orientation. Final all-material Science check still needed. |
| Base Research | 28 | 28 | 0 | Twenty-seven substantive originals + orientation; preserve every distinct material meaning, counterargument and rejected option. |
| Consolidation Research | 11 | 11 | 0 | Ten substantive originals + orientation; map derived claims to original grounds and verify conflicts with earlier sources. |
| Late AI-raised Research | 12 | 12 | 0 | Reconcile with human primary comments, independent evidence and Research-only interpretations. |
| Core implementation | 212 | 12 | **200** | Exact code/module purpose, public API/side effects, tests and Current HOW citation. Do not mechanically copy all Python lines into Science. |
| Core unit/integration tests | 28 | 9 | **19** | Read assertions and fixture provenance; keep absent/skip/expected-fail distinct from executed pass. |
| Windows implementation | 178 | 0 | **178** | Read current execution/Qt/JSON/permission/cancellation boundaries; represent accepted state of current code only. |
| Windows tests | 10 | 0 | **10** | Test authoritativeness, actual assertions, package/manifest and concurrency; no claim of successful execution unless verified. |
| Windows integration manifest | 1 | 0 | **1** | Explicit install/activation/public platform contract, pinned by revision. |
| Windows documentation | 3 | 0 | **3** | Historical implementation documentation; verify actual code or mark drift. |
| Platform contract witness files | 17 | 0 | **17** | Public external lifecycle/manifest/session/observability contract only, not domain Work authority. |
| Legacy public docs | 19 | 0 | **19** | Historical claim/methodology provenance; classify superseded/current against direct code, retain scientific differences. |
| Publication bootstrap docs | 7 | 0 | **7** | Owner navigation and original architecture context; some may now be edited and require frozen-content comparison. |
| Core auxiliary sources | 20 | 0 | **17** | Build/config/resources/README; 3 were governance-read, not full-read. Count by role and content, not mere file name. |
| Governance/work and Research README | 7 | 0 | **0** | Seven `governing_read` sources; file identity/authority and revision are governed evidence, not scientific claims. |
| Engineering scripts | 2 | 0 | **2** | Direct read plus invocation/CI behavior; preserve deployment-risk findings only if material. |
| Generated historical developer artifacts | 6 | 0 | **6** | Use strict privacy and historical-role filters; never publish raw user/workspace data by default. Read only if authorized and necessary for a claim. |
| **Total** | **566** | **77 full-read** | **479 not-full-read**, plus 10 governance reads | Counts are census states, not independent Research conservation. |

**Accounting caveat:** the sum of `full_read` across rows is 77; governance/Research README grouping is discussed separately. `governing_read` is a distinct read state and cannot be represented as a full primary-source study read. Generated historical files may be material as evidence of data leakage or development setup without their raw content being public-safe Knowledge.

## Correct workflow by evidence role

1. **Research:** establish fine-grained meanings and negative cases with exact spans; compare all material claims to canonical Science with correct status. Merely assigning one English source-row to a Research manuscript does not close it.
2. **Implementation code:** identify source module/API role and important behavior/failure branches; direct execution and test evidence take priority for Current HOW. Original frozen code bytes are already retained as Git objects; copying every function into a Science article would not improve research completeness.
3. **Tests/engineering scripts:** distinguish assertion in source, actual suite invocation, passed/failed/skipped outcome, fixture dependencies and environment. Existing GitHub Actions verification of the **knowledge verifier** does not execute domain/Windows suites by implication.
4. **External/platform and desktop evidence:** keep product/application authority separate from public installation/session/node lifecycle; derive profiles by actual contract. UI client code must not become a substitute source of bank/macro domain truth.
5. **Historical docs and generated files:** preserve historical claims, significant negative findings and reproducible references; do not turn stale docs or generated personal data into public baseline evidence.
6. **Auxiliary and governance:** pinned configuration/import/release/package evidence can receive a justified **supporting, not substantive Science** disposition after role verification. Different data formats require different preservation criteria.

## Explicit non-claims and blockers

There is no justification to set all 566 source records to `verified` from a Git tree hash, a source-row trace or a functioning checkout. The separate original-byte SHA check for `SB-EXT-0002` DOCX remains open. Distinct human or delegated independent semantic challenge and source-to-Science/cold-reader review are unperformed. Remote host, browser, Android, machine execution and shared state guarantees still require owner admission and actual tests.

**Next concrete evidence batch:** begin with the 17 public platform contract witness files, desktop installation manifest and 10 desktop tests because these establish whether planned remote/surface/health assumptions have direct implementation support. Continue the 19 unread core tests and 200 unread core modules by domain risk, not alphabetic count alone. In all cases preserve the exact source blob and material source role with a reviewable destination before terminal disposition.
