# LCD documentation-source executable algorithm probes

**Date:** 2026-10-12. **Result:** `SCOPED_SYNTHETIC_DESIGN_BEHAVIOR_PASS` at exact `stratbox@16fbe7acd5d1b817c4613247cad902f38aa4160c`. **GitHub Actions:** [run 38206600725](https://github.com/ForestTiger-GH/stratbox/actions/runs/38206600725), **SUCCESS**. **Tool:** `_mw/epochs-001-strategy-box-development/consolidation/tools/test_lcd_candidate_behavior.py`. **Effect:** Work-only test tool and CI, no product source changes. No native platform or financial source was used.

## Execution method and trust boundary

The test reads the **actual maintained Markdown LCD documents**, parses their fenced `~~~python` fragments, and selectively compiles an exact allowlisted set of named top-level AST definitions. The tool **does not recreate a second implementation** of the candidate's control flow. Selected bodies execute with narrowly injected standard-library classes and synthetic recorder/scheduler/ledger/projection ports. The source-document AST must parse and the selected class or function must be unique at that path; a future change of the documented body can fail the test.

Executing the fragment can establish specific deterministic candidate behavior only. Dependencies not represented by those fakes, private OS/library imports, process races, disk/network durability and security policies are outside this test. The test is producer-authored and thus is not an independent design challenge. It does not grant Product Authority, turn a draft method into a shipped function, or mark an LCD `READY_FOR_IMPLEMENTATION`.

## Direct tested scopes

| Literal LCD source and actual function/class selected | Synthetic challenge | Observed bounded result |
| --- | --- | --- |
| `docs/lcd/application/local-scenario-execution-construction.md` — `CaseOutcome`, `EffectCertainty`, `aggregate_outcome()` | Complete two-step success; required step fails with known no effect; optional step fails; failed operation leaves uncertain effect; incomplete run | Five assertions passed: `SUCCESS`, `FAILED`, `WARNING`, `OUTCOME_UNKNOWN`, qualified incomplete `WARNING` |
| Same document — `LocalScenarioService.submit()`, `_run_and_release()` and exact documented exception classes | Admit one run; reject a second; release only when definitely not started; preserve reservation after schedule ACK loss; release after callback; do not invert successful result if display projection raises | Synthetic in-process control tests passed. True native Qt thread/worker race and hard process kill remain untested |
| `docs/lcd/hosting/host-authority-and-client-contract-construction.md` — `HostAdmission.submit()`, `AdmissionKind`, `AdmissionReceipt` | Scheduling loses ACK after admitted Run, then replay identical intention; same key with different digest; actor denied | Four assertions passed: `OUTCOME_UNKNOWN` preserves Run ref, replay does not schedule twice, conflict denied, unauthorized invocation denied. The fake ledger does **not** prove transaction durability |
| `docs/lcd/observability/execution-evidence-and-problem-boundary-construction.md` — `OptionalProblemBridge.record()`, `ProblemRegistration` | Recorder may have committed but ACK lost; ACK without genuine ref; confirmed ref; no recorder | Four assertions passed: unknown remains unconfirmed, authentic acknowledgment alone supplies a confirmed ref, absent recorder is unavailable. Real AppDock recorder contract/lookup untested |

## Limits and follow-up

- The tests **execute exact candidate code-shaped definitions**, not the underlying analytical `stratbox` nor current `stratbox-windows` production paths. Earlier *different* pinned current-code synthetic tests exist separately; passing those must not be presented as fixing the current behavior.
- **No production import, complete module, exact type-checker, real persistence/transaction, OS kill, concurrent native scheduling, network/browser authorization, AppDock installation, Android client, realistic bank dataset, source-catalog read or filesystem fault injection** was exercised by this LCD test.
- No `LCB-01..11` blocker was closed by fake execution. In particular, the host still needs an atomic admission+dispatch ownership contract, real permission policy and actual installed platform.
- A future verifier may expand *selected* tests to artifact bytes, FRG resource-generation fencing, machine and provider contracts if implementation relevance justifies it. Do not inflate a passing function count into a claim of system availability or a literal full-code implementation.
- A different competent reviewer must independently perform cold coding/meaning assessment, while separate research source-preservation and 14-case blind amputation remain open.

**Scoped assurance grade:** `PRODUCER_EXECUTED_DESIGN_FRAGMENT_TEST`, stronger than AST parse and weaker than target implementation conformance. **Program state:** `LCD_CANDIDATE`/`LCD_BLOCKED`; `LCD_READY_FOR_IMPLEMENTATION` **NONE INDEPENDENTLY ATTESTED**, `GLOBAL LOSSLESS_PASS=BLOCKED`.
