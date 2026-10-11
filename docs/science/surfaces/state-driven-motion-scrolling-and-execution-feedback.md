# State-driven motion, scrolling continuity and execution feedback

**Scientific question:** how can a dense economic-analysis client make long, parallel and sometimes remote work legible without converting animation into false execution state, input latency or visual noise? **Original:** complete 2026-10-07 motion Research `SB-SRC-0040`, frozen blob `199ebe15e1dae7e3003c1976d5ea9093dde9cbe9`, L1–L3414. **Status:** research-derived bounded design model, not a shipped motion API, approved visual contract, measured Qt performance or independently certified accessibility. Some vocabulary reflects the original Scenario-centric interface era; Work/Run/Job/Artifact owners are separately studied and must be reconciled with later execution semantics.

## 1. Motion communicates a cause, not decoration

A useful transition answers at least one user question: Was my action accepted? What changed? Where did the selected object go? Is processing actually occurring, and at what stage? Where is the new result? In the source's formulation, the desired experience is **many tiny transitions, almost no large animations**. The visual style is *precise, calm, connected, responsive and computational*.

A motion event must be derived from an authoritative projection:

```text
authoritative work or application event
    → updated semantic state / projection
    → MotionRole(from, to, presentation context)
    → resolved MotionSpec and effective accessibility policy
    → native client animation or immediate static representation
```

A button widget playing a “Run succeeded” animation is not evidence that an operation succeeded. A local click may precede remote acknowledgement, queuing, execution, output transfer and durable publication; these are distinct claims. Rendering may omit intermediate states when a fast operation reaches the final one, but must never postpone showing the truthful final state in order to complete a storyboard. Business handlers must not manipulate QWidget animation state.

Motion is justified by acceptance feedback, actual state transition, hierarchy/navigation, source-to-result continuity, validated progress or a new item. It is insufficiently justified by “looks modern.” High-frequency selection gets a tiny fade/fill; opening an inspector can use restrained spatial motion; a newly accepted Run can use a visible but brief handoff. When no relevant event remains, the interface returns to **rest**. No permanent animated “selected,” “success” or “error” decorations.

## 2. Proposed timing, easing, geometry and interruptibility

The original proposed the following shared semantic timing profile, distinguished from platform-specific input physics:

| Duration role | Candidate value | Main use |
| --- | ---: | --- |
| instant | 0ms | snap, reduced motion or urgent truth |
| xfast | 80ms | press, focus, tiny color state |
| fast | 160ms | quick insertion, close, select |
| normal | 240ms | reveal, ordinary structural transition |
| slow | 320ms | capped large reposition/scroll |
| emphasis | 480ms | rare meaningful connected emphasis |
| ambient-fast / ambient-normal | 1,400 / 1,800ms loop | only genuinely ongoing process |

Candidate easings: `enter = cubic-bezier(0,0,0,1)`, `exit = cubic-bezier(1,0,1,1)`, `move = cubic-bezier(.55,.55,0,1)`; `linear` is reserved for continuous or short determinate movement, not generic navigation. Distances are 2/4/8/12/16px or native density-independent units. Ordinary spatial feedback belongs near **4–12px**, with e.g. press scale `1→0.985` and soft-enter `0.99→1`. Groups of 2–5 related elements may have a restrained 20–30ms stagger; large lists must not stagger every item.

All animations must be *cancelable, retargetable and non-blocking*. Repeated navigation targets the **most recently requested state**, not a queue of all discarded intermediate transitions. Reversing an inspector animation can start at its current presented position; selecting 20 rows rapidly must not accumulate 20 pending moves. Keyboard focus/input is authoritative and immediate. Input feedback is a candidate **50–80ms maximum** aspiration; actual operations start immediately without waiting for an 80–240ms transition.

A rough per-surface visual budget is **one clearly noticeable ongoing animated cluster**: one selected Run may show process sheen while an inspector and inactive rows show static state. Offscreen/virtualized items and minimized surfaces stop nonessential motion. Multiple timers, per-row effects and full-widget geometry changes are resource expenses that must be measured rather than assumed free.

## 3. Execution state is more important than a running gradient

The original gives an explicit user-observable sequence:

| Actual event | Appropriate motion or static treatment | False inference to avoid |
| --- | --- | --- |
| Form ready / parameters validated | Stable primary action | “valid form” proves authorization of a Run |
| User presses/submits | Instant pressed state, then new Run/Work card only on accepted object | animation delays actual submit or invents backend receipt |
| Prepared or remotely queued | Static queue/state label; no ambient execution sheen | queued means CPU work is running |
| Running | Low-amplitude process rail, stage/status and validated progress | moving gradient proves actual progress percentage |
| Awaiting user approval or input | Stable actionable waiting state | ambient shimmer disguises blocked work |
| Cancel requested | Cooperative “Stopping…” while real cancellation is outstanding | cancel click means already cancelled |
| Success / partial warning / error | Immediately stop running meaning, show actionable terminal details, then quiet one-time settle | celebratory motion or alarming pulse replaces evidence |
| Artifact produced / published | Appearance of actual available result with identity and destination | artifact chip implies durable publication if bytes are only staged |

This table is a *translation of the dated Scenario study*, not a replacement for the current whole-system lifecycle and permission model. An accepted Run, queued Job, running Attempt, source transfer and available Artifact can be different objects and events. Actual state changes must be observable even when no animation can be rendered.

The source's signature **process sheen** is a 1–3px strip or border segment, occupying a tiny area of the card; it uses one semantic accent with low-opacity peaks (the source gives examples around 6% and 16–22%) and travels in 1.4–1.8 seconds per loop. It stops after actual work ends. One aggregate status may represent many concurrent processes; a moving row for each of 20 running items is explicitly rejected. High contrast and reduced motion replace shimmer with static rail, icon and readable “Running” label.

### Truthful progress and step transitions

Prefer determinate progress only when the engine knows a valid denominator: steps, files, periods or entities. If the true denominator is unknown, “Stage 2 of 4” or “Processing 18 files” can be more accurate than arbitrary “73%”. A stage-level counter may restart; a **single cumulative progress bar must not silently reset** or regress without explaining a changed scope/revision. Smooth interpolation (e.g. 120–240ms) may bridge *already confirmed values*, never predict a percentage beyond reported fact.

A composite execution can show a calm step rail with completed, active and upcoming markers. Parallel steps need multiple truthful active indicators and an aggregate, not theatrical racing. Error stops presentation of running state immediately and exposes retry/log actions after a brief transition; a failed computation is a consequence requiring reasoning, not a flash/shake animation. Warning and success have equivalent geometry with different explicit labels and icons.

## 4. Scrolling is an information-preservation mechanism

**Direct physical scrolling is platform-native.** Desktop wheel/touchpad physics and Android touch kinetics differ; their semantics do not require identical pixel interpolation. App-initiated scroll, by contrast, may have shared semantic roles: to current Run, validation error, selected file or highlighted log line.

The source proposes capped programmatic scroll intervals: **160ms** for less than half a viewport, **240ms** for up to roughly 1.5 viewports, **320ms** maximum for larger distances. A very distant target may use a quick jump followed by destination highlight. Motion must keep a selected object visible without creating long compulsory travel.

In Work timelines and logs, **tail following is conditional**: when the reader has scrolled upward to inspect history, new events must not drag the viewport to bottom. Instead show “New activity” with an unread count. Clicking it performs a controlled jump or capped scroll. Prepending historical items preserves a stable scroll anchor rather than shifting currently read text. Editing a message locally highlights only the changed region; the whole message should not re-enter and reset reading position.

A high-rate log is not a chat. For large log streams, insert in throttled batches **without per-line animation**; suspend follow-tail after manual upward scroll; annotate critical lines without flashing red. Large table sort/filter and a refresh of ten thousand rows should avoid per-row animation. If one new row appears, a short highlight may be useful.

This aspect of the study is a substantive **data-consumption guarantee**: viewport movement controls what evidence the analyst can read and whether a new event obscures historical context. Smoothness is not the same as correctness; anchoring, latency, accessibility, scrollbars, selection and history retention must be tested independently.

## 5. Connected objects and surface-specific transitions

The original interface proposal used four top-level surfaces—Work, Explorer, Scenarios and Runs—and a secondary inspector/bottom diagnostics panel. This is a **dated proposed navigation vocabulary**, not a current product commitment. The useful general concept is preserving one object's identity as it moves between authorized views.

- Main navigation changes content with brief crossfade and a few pixels of displacement, not whole-screen flights.
- Rail selection may use one moving active indicator; content in a sidebar can crossfade while its physical container remains stable.
- Opening an inspector can use a 160–240ms fade + ~12px reveal; if resizing a large Qt layout, the exact cost must be benchmarked. Closing is shorter; direct window resizing/splitter dragging is unanimated.
- Explorer folder navigation resembles native Explorer and retains an explicit selection policy. “Reveal artifact in Explorer” can navigate to the actual folder, scroll to a row and briefly highlight it; this conveys result destination, not a storage permission.
- Scenario parameters use a small reveal; validation uses border/helper text, **not shake**.
- Messages, system notices and provider/AI replies insert via tiny fades. A genuine machine actor uses the **same execution/approval motion grammar** as a human-run task rather than a special “thinking universe”; real streamed text is better than fabricated character-by-character typewriter effects.
- Toasts, short dialogs and badges settle briefly; destructive confirmation seriousness follows authority and language, not aggressive animation. Batches of completion events aggregate instead of producing many fly-ins.
- Empty states remain still; startup should show a useful shell when ready, then reveal available content without presenting a decorative fake loading sequence.

Charts have special risk: smooth series interpolation can imply an incorrect intermediate economic value or false continuity after unit/perimeter revision. Initial chart render need not animate; compare semantics must dominate visual polish.

## 6. Accessibility, performance and platform boundaries

The first-class **Reduced Motion** presentation profile substitutes:
- slide + fade with brief fade,
- connected spatial move with crossfade + destination highlight,
- press scale with color/fill,
- moving process sheen with static status,
- long smooth scroll with fast jump + highlight,
- blur/depth effects with no animated blur.

The source proposed `FULL/REDUCED/OFF-MINIMAL` internal motion modes with a possible user-facing “follow system / reduce animations”. That possibility must be reconciled with the later [Settings study](../application-state/settings-feature-admission-and-contextual-controls.md), which withholds an in-app motion toggle by default and prefers an actual OS accessibility signal. A missing/old Qt interface may need a platform adapter; the source's reference to `QAccessibilityHints::motionPreference` is a *version-sensitive candidate*, not proof it works in this frozen Windows build. Screen readers must not announce every ambient frame; focus and keyboard operation must work with instant animations. Status changes require labels/icons independent of movement. No flicker/flashing or perpetual pulsing error.

The source describes possible Qt tools—`QPropertyAnimation`, `QEasingCurve`, parallel/sequential animation groups, `QScroller`—as implementation candidates. Large `QGraphicsOpacityEffect` overlays, per-frame pane geometry updates, independent timer per Run and whole-table animations may cause repaint/layout overhead. A shared clock, batching, effect suppression while minimized and preference for paint/opacity over full relayout should be evaluated against actual Windows hardware.

The proposed performance envelope is: stable **60fps** on a reasonable standard PC, input feedback under **50–80ms**, typical structural transitions **≤240ms**, rare **≤320ms**, justified emphasis **≤480ms**, almost no motion overhead while idle, and no interruption of large log/table scrolling. These are proposed *acceptance targets*, not measured outcomes. In case of constrained hardware, reduce optional animation rather than preserve all effects at a janky frame rate.

## 7. Testing, rejected alternatives and reopening conditions

The original includes a 49+ name role catalog (§36), a detailed 27-item component/time matrix (§37), twenty useful microinteractions (§43), twelve rejected animation families (§44), code-review questions (§71), seven implementation phases (§55), five storyboards (§§57–61), UX/performance gates (§§52–54) and a 35-point conclusion (§74). These are candidates for **separate evidence-carrying registries**, never passed installed tests.

Tests named by the source include deterministic/virtual animation time, role completeness, existence of reduced-motion fallbacks, rapid click/reselection/reverse, scroll anchoring when messages are prepended, no auto-jump while reading, high-volume logs (100,000 lines), 20 simultaneous running cases, immediate completion after start, minimize during sheen, cancel during visual transition, reduced-motion toggle at runtime, accessibility labels, animation/CPU/frame budgets and native input physics on a real device.

Rejected effects include default bouncing/spring overshoot, animated large backgrounds, parallax/large zoom, constant glowing selection, pulsing red errors, rainbow color cycling, confetti after success, typewriter imitation, ornate startup branding, and animating every data/table row. Their rejection is part of the knowledge corpus: they are plausible familiar UI approaches whose visual cost and false state cues outweigh the benefit in long-session financial analysis.

A minimal end-to-end demonstrator should follow **Scenario selection → parameter disclosure → Run acceptance → truthful queued/running state → verified progress/steps → actual Artifact insertion → opening a result → reveal in Explorer**, with a separate failure and scroll-up-new-activity path. Test correctness without motion first; then measure the animated adapters. Reopen on changed native toolkit version, genuine multi-client renderer, measured accessibility/performance, current-state evidence or an explicit approved interface decision.

**Related Scientific Knowledge:** [visual token values](visual-token-values-contrast-and-layout-profiles.md), [semantic design roles](semantic-design-tokens-motion-and-accessibility.md), [Settings admission](../application-state/settings-feature-admission-and-contextual-controls.md), [Work/execution planning and recovery](../work/admission-planning-resource-scheduling-and-recovery.md), [authorized user streams](../collaboration/authorized-streams-read-cursors-and-private-work.md), [Artifact output lifecycle](../artifacts/output-identity-publication-and-availability.md).
