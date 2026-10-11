# Developer-annotated Strategy Box research goals — primary text and Product admission

**Evidence status:** `FULL_PRIMARY_TEXT_READ / ORIGINAL_DOCX_SHA_UNVERIFIED / PRODUCT_DECISIONS_OPEN`. This document conveys the goals expressed in **ten developer answers** in an annotated research questionnaire. Its full source text was read from an authorized user Library file, but source DOCX bytes were not made available for checksum verification. No original private source text is copied into the repository. Subsequent Research contains twelve topics; the last two have **no corresponding developer answers** in this ten-topic original.

**Authority distinction:** the developer's direct reply, a question written by the researcher, an engineer's later proposal, a fact in current code and a formally admitted Product Decision are different evidence classes. Tentative statements about priority, schedule, implementation and ownership retain their qualifications.

## Ten source-grounded directions

| Topic | What the developer answer actually supports | What it does NOT settle |
| --- | --- | --- |
| **01 — Operation, Scenario, Cascade, Scheme** | Analytical functions should be usable from Python, notebooks, and the app. A large catalog needs intuitive groupings into scenarios/cascades; machine-readable Schemes help authorized AI consumers use subject-matter procedures. | Mandatory new DSL, single giant Operation catalog, every helper as a callable public product operation, physical Scheme owner. |
| **02 — Execution and interruption** | Closing/interruption of **local** work generally ends active processing. Preserve meaningful work context; protect important file writes and make interrupted/failed work visible through compact warning status. Tray operation is a future, not immediate, preference. | Universal durable remote Jobs, deep automatic restart after every failure, precise queue/status enumeration, checkpoint storage format. |
| **03 — State and recovery** | Start with a minimal reliable foundation that permits later growth, without constant state-loss problems. | Specific database/storage platform, replication protocol, consistency algorithm or adopted recovery objective. |
| **04 — Results and artifacts** | Non-file computed results can be presented in chat. Files belong in the available data workspace; a moved/deleted file may simply become unavailable on next use, with a small inactive/missing indicator. | Compulsory global filesystem search, automatic resurrection, immutable archive of every version or a universal managed artifact database. |
| **05 — Participants and security** | A known **trusted local team** values simple participant names, shared appropriately scoped error notifications and appropriately placed detailed diagnostics. | Public Internet authorization by nickname alone, automatic disclosure of raw logs, broad agent permissions, remote ACL model. |
| **06 — Machine interfaces** | The same analytic domain functionality should serve direct Python, local clients and future authorized local/remote machine or AI callers. | Implemented MCP/A2A host, particular transport, always-on autonomous AI or universal wire contract. |
| **07 — Cross-platform clients** | Web interface is expressly wanted; Android is a prospective **remote/host-first** client. Shared functional semantics can have different responsive layouts. Two extra repositories were tentatively suggested. | Fixed timing of Web/Android releases, a mandatory repository split, Android offline Python runtime, public identity implementation. |
| **08 — Chats and diagnostic UX** | Users may execute commands **concurrently in different chats**. A familiar team-workspace can expose appropriate shared chat context and compact status/error signals. | Chat as authoritative execution storage, arbitrary concurrent writes, unrestricted cross-user visibility, final UI navigation taxonomy. |
| **09 — Source currency and evidence** | Record actual download time; let qualified experts judge statistical trust and recency; link existing method code when useful. Preserve proportional operating cost. | Exhaustive globally monitored series catalog, surveillance of every source value, mandatory per-indicator methodology documents. |
| **10 — Host versus local ownership** | Meaningful data/history should reside where operations actually execute: device for local work; shared host for hosted work; clients may retain secondary preferences. | Named SQL engine, detailed synchronization, exact AppDock package/runtime architecture, future network services already working. |

These ten rows are **source-grounded intent summaries**. Neither the suggested mechanisms nor this editorial consolidation automatically grants Product approval.

## Three implementation tensions that must remain visible

**Trusted team versus public Web:** light participant naming within a closed team cannot authorize Internet-facing requests. A remote Web deployment requires authenticated principals, server-side access checks, safe scoped projections and protected technical logs. Good UX and safe access are compatible, but security enforcement cannot be inferred from informal team trust.

**Local stop versus hosted detached work:** a local UI shutdown can be expected to interrupt local computation. A separately admitted persistent host can continue acknowledged Jobs after client disconnection if its runtime, permissions and recovery are real and tested. Status and cancellation must name the execution owner and distinguish these profiles.

**Lightweight source trace versus global registry:** acquisition time is a useful default observation receipt but does not establish byte identity, source authenticity or replay readiness. A bounded digest, actual-used-source reference or method version can be introduced where justified. Universal monitoring of all macro/banking statistics is not implied.

## Audit of 30 previously source-tagged human-intent statements

A producer comparison of all 30 historic `HUMAN_INTENT` records against the recovered annotated primary text classified **14 as direct comments; 4 as supported but engineering/security qualified; 8 as researcher interpretations; 2 as technical details absent from the comment; 1 as an item introduced by a research question; and 1 as a composite of several separate answers**.

The per-item JSONL provenance now records the recovered primary text as its basis and explicitly notes that the original DOCX hash remains unverified. The old semantic tag is retained for forensic provenance; it does **not** override the assessment field. The classifications are a **producer** review, not an independent assurance pass, and they do not establish Product decisions.

## Admission frontier

Before product commitments are frozen, separate at least the **local foreground**, **trusted shared node**, **authenticated Web/host**, and **remote Android** deployment profiles. For each, define permitted Work/Run actions, durable state owner, file/artifact behavior, chat visibility, diagnostic audience and machine actor restrictions. Keep toolkit, storage engine, repositories, queues, and transport in HOW/Architecture until approved against actual scope and evidence.

**Supporting evidence:** [human-source recovery and hash limits](../../../_mw/epochs-001-strategy-box-development/consolidation/coverage/HUMAN-CARRIER-RECOVERY-AND-ASSURANCE-DELTA-2026-10-11.md), [research-versus-comment reconciliation](../../../_mw/epochs-001-strategy-box-development/consolidation/reconciliation/HUMAN-ANNOTATED-EXECUTION-SCOPES-VS-RESEARCH-DEFAULTS-2026-10-11.md). The architecture carrier `SB-EXT-0001` is SHA-256 verified; the original `SB-EXT-0002` DOCX binary remains unverified.
