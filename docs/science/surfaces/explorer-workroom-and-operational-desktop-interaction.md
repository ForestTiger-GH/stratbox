# Explorer, workroom and operational desktop interaction: competing mental models

**Scientific question:** how to make a banking-statistics workbench learnable and operationally truthful when files, conversations, repeatable scenarios and long-running Jobs share one screen. **Status:** research-qualified, unapproved interface options; descriptions of the current desktop are bound to the [pinned Windows implementation](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b). No user study, accessibility audit, native-device trial or deployed redesign is asserted here.

## 1. Why four different metaphors coexist

A dashboard centers monitoring indicators; an IDE centers files/editors and developer command surfaces; a messenger centers human discussion and unread state; a computation control plane centers authoritative Jobs, steps, progress and failure. Strategy Box needs elements of all four without making any one the universal representation.

| Mental model | What is valuable | What goes wrong when dominant |
| --- | --- | --- |
| Dashboard | Fast health and issue scanning | Cards hide file discovery, parameter preparation, provenance and multi-step execution |
| IDE | Strong panel geometry, keyboard search, logs, file navigation | Technical density and terminal vocabulary impose developer expertise on analysts |
| Messenger | Chronological context, collaborators, recoverable history | A Run wrongly becomes a text bubble and a Job failure becomes social “message delivery” |
| Workbench + control plane | Object-specific actions, lifecycle visibility and persistent outputs | Excess technical panels can crowd analytical content |

An effective synthesis uses **one active object**—Work, folder, Scenario, Run or Artifact—and a stable shell: navigation destination → contextual selector → main object view → optional inspector. The right pane is details for the selected object, not another competing global navigation system. The main surface should retain enough width for tables and documents; technical logs should expand only when needed.

The currently observed [manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json) enters Scenario chat, and the dated desktop implements six rail modes: Explorer, Scenarios, Cascades, Background, Participants, Assignments. Those existing modes are historical implementation facts. The **four proposed logical destinations** below are an information-architecture experiment, not evidence of released navigation.

## 2. Four logical work areas, but not four mandatory buttons

| Destination | Primary user question | Core interaction | Context rather than separate root |
| --- | --- | --- | --- |
| Work | What am I investigating or discussing, and what needs my attention? | Thread/Work history, decisions, messages, linked Runs, approvals | Participants and assignments unless their real workload justifies a task center |
| Explorer | Which input, working file or published result is available to me? | Root-scoped file tree, details list, preview, provenance | Artifact metadata and permitted actions |
| Scenarios | What repeatable capability can I invoke? | Search, category, typed parameters, previews, favorites, presets | Cascade as composition/category of scenario |
| Runs | What is actually executing, queued, waiting, interrupted or completed? | Node/work-scoped run table, steps, accurate progress, logs, retry/cancel eligibility | Background as execution property, not a parallel job system |

A global Runs view and a Thread timeline should reference the **same Run identity**: the former optimizes cross-Work supervision; the latter answers how a particular investigation evolved. Each filtered view must respect access rights. A standalone “Participants” top-level route is warranted only if independent team administration or presence tasks actually emerge; a local avatar model does not prove that threshold. An empty “Background” screen without a scheduler must never suggest that enabling a flag schedules real execution.

The earlier idea of placing six distinct technical concepts on the activity rail maximizes feature discoverability in a prototype, but grows navigation entropy with every new entity. Conversely, compressing everything into Chat creates a weaker operational map. Both drawbacks explain the four-area candidate; empirical learnability and discoverability remain untested.

## 3. Long-lived Work and concrete Run must remain distinct

A Thread/dialog can contain several human and permitted machine messages, two or more Runs, evidence attachments, an approved result, a request for review and a later correction. Its reason to persist is *collaborative context*. A Run is one frozen execution with its own plan, attempts, outputs, effects, status and evidence. They have different closure and retention semantics.

```text
Work: monthly banking-source review
  Thread: questions, assigned review, approval of final claim
  Run A: refresh source snapshot, partial validation
  Run B: repeat after upstream schema diagnosis
  Artifact A: outdated workbook (superseded, retained by policy)
  Artifact B: verified workbook
  Outcome: accepted with one named residual uncertainty
```

A Run card in the Thread shows a stable link and truthful summary. It does not duplicate technical log lines, create another Run when the user scrolls, or silently mark Work complete on `job.succeeded`. A human message proposing an action, a permissioned action proposal, an accepted Job and a textual answer are four different visual and semantic objects. An agent suggestion should show target capability, parameters, expected effects, risk, required approval and outcome status rather than an ambiguous “I did it”.

## 4. Explorer should borrow familiarity, not the operating-system trust model

For analysts on Windows, **folder tree + Back/Forward/Up + breadcrumb + Search + Details list + optional preview + context menu** minimizes relearning. A spreadsheet directory is easier to scan in rows than as a wall of decorative cards. Base columns are Name, Type, Modified and Size; optional Scenario/Run/Provenance metadata belongs in a toggleable view rather than polluting the default file mental model.

The breadcrumb must be navigable, not a painted path. Suggested keyboard map: `Enter` open; `Alt+Left` back; `Alt+Right` forward; `Alt+Up` parent; `F2` permitted rename; `Ctrl+L` location; `Ctrl+F` contextual search; `F6` pane cycle. These bindings are **candidates** subject to collision checks with Qt native controls, screen readers and OS conventions.

A logical workspace tree does not imply permission to read the host filesystem directly. The current desktop has a local Explorer provider scoped to a workspace. A future remote client should obtain authoritative File/Artifact metadata and scoped actions from the application host. The UI can feel Windows-like while never exposing arbitrary server paths, other users' personal files or system storage. A “Reveal in Explorer” action has a meaning on a local desktop but may be unavailable on Web/Android; render only actions supported by the client *and* permitted by current server policy.

Dangerous actions require a true plan/apply distinction when consequences are material: show the candidate objects, identity, constraints and consequences; confirm the exact plan or ask for authorization; execute; then display observed result and partial failures. A green toast after a best-effort remote deletion is a false claim.

## 5. Scenario discovery and forms should scale with the catalog

When there are a few operations, cards are helpful. When there are tens or hundreds, searchable lists with stable categories, Favorites and Recent are more efficient for scanning; a secondary card view can support browsing. Users search for *what they want to do*; internal Command/Operation/handler identities are advanced metadata, not required navigation knowledge.

Form fields are generated from permitted parameter schemas. Recommended behaviors: basic fields first; advanced collapsed; bounded number/date pickers; derived or locked values displayed read-only; inline validation beside the erroneous field; a workspace-aware file picker; explicit effective defaults. Presets store **user-controlled parameter choices and references**, not duplicated mutable scenario definitions. A preset revision must be resolved under the current operation schema before launching.

A composite/cascade often reads best as a vertical sequence showing order, state and future actions. A graph is justified for real branching, parallel dependencies or debugging, not automatically for a four-step upload→parse→compute→export pipeline. The runtime plan can be more complex than the initial human-facing preview, but no omitted destructive effect may be hidden by that simplification.

## 6. Operational view and evidence-based progress

The global Runs surface answers operational questions that a conversation does poorly: *what is running across my authorized scopes, who initiated it, which resources are waiting, and what can I cancel?* A table can expose Scenario, actual stage, start/duration, initiator, foreground/background location, verified artifact links and status; sorting active/waiting first is a candidate, not a universal standard.

Progress is *determinate* only when a valid numerator and denominator exist. A step number does not equal fraction of total computational cost; animations that march toward 100% with elapsed time fabricate precision. During unknown-duration work, display the current stage, last reliable update, elapsed time, and a genuinely indeterminate activity indicator. “Cancel” and “Pause” only appear when executor capabilities and policies support them. A `cancel_requested` control is not proof that an external effect has stopped.

A dependable distinction is:
```text
Level 1 — Run card: stage + status + important actionable message
Level 2 — Inspector: per-step warnings, causal problem ID, artifact/attempt links
Level 3 — Separate log/problems panel: structured filtered technical evidence
```
A bottom execution panel has better horizontal width for long log lines, search and large file paths than a permanently narrow inspector. It should open contextually, virtualize large logs, allow copy with redaction, and separate raw debugging from an accessible user error explanation. Never broadcast restricted technical stack traces to everyone on a shared node.

## 7. Meaningful notifications, limited interruptions

A timeline with every heartbeat, retry or log record becomes useless. Keep *meaningful Work events*: admitted/run completed, significant warning, artifact published, approval requested, work assigned, correction or closure. Use a toast/OS notification for off-screen action needed, failed background work or explicit alert policy—not routine success while the user watches a Run.

The user-facing error should state **which action failed, on what stage, how trustworthy the partial results are and what can be done**. If next action is unknown, say so instead of fabricating a “Retry” button. A “technical details” drawer can contain safe identifiers for support while keeping full traces access-restricted. Accessibility means labels, focus, and textual statuses, not simply colored badges.

## 8. Geometry, typography, motion and responsiveness are hypotheses

The 2026 interface study proposed a four-part shell plus an optional bottom panel and quiet status strip, 4/8/12/16/24/32/48 spacing tokens, several radius tiers, and restrained type scale from compact metadata to prominent page titles. It suggested logical width regimes: **up to 640**, **641–1007**, **1008–1399**, **1400+**. These are *proposed thresholds* for testing, not measured invariants, and should be judged by content fit, translated text, font scaling, assistive technology and actual device widths. A right inspector that overlays at a smaller window must not make core work inaccessible.

The study's native-language proposal prefers Windows control and keyboard conventions, system/accessible typography, system/light/dark/high-contrast variants, quiet backgrounds and meaningful semantic colors. Styling should not convert success, failure or queued states into brand accents. It argued for small context-explaining animations rather than bouncing, parallax and ornamental transitions. It proposed inspector motion around 120–180 ms, subject to measured user experience and explicit reduced-motion preference. Later dedicated motion and visual studies refine timings and token values; the early numerical proposal is historically preserved here, **not** promoted as the current design specification.

The essential portability relation is:
```text
same authorized action and same state meaning
        → different desktop/web/mobile presentation profiles
        → equivalent accessible user consequence
```
A touch client may use bottom navigation, pages and sheets instead of the Windows rail, splitters and hover menus. Native layouts can differ radically without forking authorization, Work identity or operation meaning.

## 9. Accessibility and falsification

Target candidate acceptance families: keyboard-only navigation from a new Work through parameter validation, Run submission, result review and safe cancellation; visible focus and tooltips for icon-only buttons; status and warning independent of color; screen-reader descriptions that distinguish a message, Run, Artifact and approval; high-contrast and 125%/150%/200% scaling; reduced-motion behavior; no controls clipped under narrower window and long text; keyboard alternatives for drag-and-drop.

Failure experiments should explicitly exercise: a very long path and filename; hundreds of scenarios; tens of thousands of Run/Artifact records; streaming logs at high rate; a disconnection during an approval; missing workspace while diagnostic screens must remain reachable; a successful Job with failed artifact publication; user access revocation while the Work is open; a Run blocked indefinitely without progress denominator; dynamic language expansion and font scaling; many simultaneous notifications. No passing measured results are yet recorded for these experiments.

## 10. Trade-offs and open authority

**Observed:** the dated desktop has Scenario-first chat, local stores, inspector and six-mode navigation, plus Qt orchestration. **Research conclusion:** the workbench, dialogue and execution-control semantics are complementary; Work and Run must remain distinct if collaboration/history become real product needs. **Unaccepted design candidates:** four logical destinations, global Runs table, panel composition, keyboard shortcuts, default Details view, search/palette, responsive breakpoints, color and motion tokens. **Counterarguments:** four destinations may bury team approvals for a heavily collaborative deployment; a dedicated Team/Inboxes screen may become necessary, and highly expert analysts may prefer denser layouts than a calmer default. **Reopen:** actual user workflows, accessibility tests, screen-size evidence, accepted information architecture, device-specific interactions or implementation updates.

Related Science: [Work navigation](work-context-navigation-and-authorized-actions.md), [visual tokens](visual-token-values-contrast-and-layout-profiles.md), [state-driven motion](state-driven-motion-scrolling-and-execution-feedback.md), [client portability](semantic-portability-and-client-authority.md), [shared warnings](../collaboration/shared-conditions-and-log-access.md), and [operational failure truth](../execution-and-diagnostics/causal-observability-and-failure-truth.md).
