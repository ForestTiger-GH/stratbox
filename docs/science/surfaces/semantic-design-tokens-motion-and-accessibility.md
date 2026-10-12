# Semantic design tokens, state-driven motion and cross-device accessibility

**Problem domain:** how one Strategy Box can remain a calm, dense analytical workspace while Qt desktop, browser and prospective Android render distinct layouts without changing the meaning of banking results, user actions or execution states. **Status:** research-derived visual and accessibility criteria, not approved branding, a compiled shared design library, a passed WCAG audit or measured target-device performance.

## 1. Product-semantic fidelity outranks pixel fidelity

The minimum reusable contract is the **meaning of an action and a displayed fact**. A running Run, a stale data snapshot, a missing Artifact and a denied delete must have consistent subject IDs/outcomes across clients, although a desktop table row, browser responsive card and Android bottom-sheet look different.

Three levels must not collapse:
1. **Authoritative application/domain state** — accepted Work/Run/Artifact, evidence quality, permission and actual progress.
2. **Semantic presentation** — user-facing status, label roles, available actions, form fields, notifications and style tokens.
3. **Native rendering** — Qt Widgets/QSS, browser DOM/CSS and Android UI toolkit/window/OS controls.

The current Windows [Qt presentation and scenario projector](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation) are a usable prototype, but not a released language-neutral design contract or Android-compatible widget library. Core statistical calculations should not import `QColor`, stylesheet selectors, CSS classes, fonts or device geometry.

A shared design token source is logical; a separately released design repository is conditional on multiple independent consumers, lifecycle and conformance needs. Building an empty package or requiring full identical layout source reuse before Web/Android experiments would add overhead without proving a better experience.

## 2. Visual hierarchy suitable for financial analysis

The source study's proposed direction is a **calm, information-first operational product**: restrained saturation, readable hierarchy, compact tables that permit long sessions, visible source/period/unit context and technical detail on demand. It explicitly resists a decorative dashboard with dozens of alert-colored cards or an imitation messenger that conceals structured analytical Work.

| Design concern | Candidate rule | What remains unproven |
| --- | --- | --- |
| Brand/accent | Quiet blue as an action accent; subdued neutral canvas | Formal brand approval and actual contrast on each renderer |
| Data text | Strong information hierarchy, stable tabular numerals where appropriate | Exact cross-font glyph metrics and multilingual rendering |
| Density | Desktop compact/comfortable option only when useful; mobile remains touch-sized | Measured effectiveness on slow work PCs, phones and tablets |
| Warning/status | Dedicated semantic success, warning, error, running, unknown, unavailable | Real a11y labels and contrast checks |
| Panels | Main Work remains dominant; inspector and diagnostics are secondary | Optimal breakpoints and usage frequency |
| Accessibility | Keyboard, assistive tech, high-contrast, text scaling and reduced motion | Platform/device/browser conformance |

The original proposed `Strategy Blue` approximately `#316BE5` in light theme, ~13px Windows body type, a 4px spacing grid and 8/12/16/24/32px typical margins. These are **dated desktop design hypotheses**, not universal Android pixels, not a formal brand specification, and not proof that the combination passes actual contrast rules. Browser zoom and OS text scaling may require larger components and automatic reflow. A user-chosen accent must remain subordinate to the distinction between status danger, warning, selection and focus.

## 3. Four levels of tokens

```text
Brand primitives: palette ramps, numeric spacing/type scales, available font families
  ↓
Semantic roles: text.primary, text.muted, surface.canvas, status.unknown, focus.visible
  ↓
Component roles: form.error, run.progress, chat.card, table.selected, inspector.header
  ↓
Platform adapters: Qt palette/QSS, CSS custom properties, Android Material/native resources
```

Potential semantic groups:
- `surface`: canvas/primary/secondary/elevated/hover/selected;
- `text`: primary/secondary/muted/disabled/on-accent;
- `border`: subtle/default/strong/focus;
- `accent`: default/hover/pressed/soft;
- `status`: success/warning/error/info/running/unknown;
- `typography`: body/label/caption/heading/code/tabular-data;
- `space`: a bounded numerical spacing ladder;
- `motion`: instant/xfast/fast/normal/slow/emphasis.

These are **role candidates**, not accepted API keys or a promise to serialize every Qt property to JSON. The shared layer defines *what a token conveys*; each renderer must test concrete colors, focus, density, touch targets, platform contrast and accessible text. A success color alone is never proof of domain success.

**ArtifactStyleSet and InterfaceTheme differ.** One styles the produced XLSX/PDF/DOCX/PPTX/plot by versioned output semantics; the other styles the UI. `ArtifactMetadata` such as the displayed creator is an output field, distinct from the verified initiating principal, producing Run, actual renderer and source provenance. Changing a theme must not mutate a historic workbook or its scientific evidence.

A neutral report-style extension can contribute validated declarative palette/font/template data. It does **not** gain permission to inject arbitrary Qt widgets/QSS, change shell navigation, run scripts after report generation or modify banking formulas. Fonts may be referenced subject to license and installed availability; no typography exactness claim is possible without target renderer/font verification.

## 4. System/light/dark/high-contrast settings and focus semantics

The smallest useful Appearance preference could expose `System`, `Light` and `Dark`, with a restrained approved accent choice. High contrast, OS accessibility and required focus visibility outrank cosmetic overrides. A low-contrast muted text token that looks elegant in one desktop screenshot may be illegible against selected rows or browser zoom in another.

A faithful renderer tests:
- real contrast for body, selection, disabled and error states;
- keyboard focus visibility inside overlays, sticky bars and inspectors;
- non-color distinction for success/warning/error/unknown;
- text scaling and truncation for long Russian banking source names;
- logical reading/tab/focus order independent of widget construction;
- zoom/reflow without losing a draft or requiring horizontal page scrolling for normal tasks.

The source refers to [WCAG 2.2, Focus Not Obscured (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum) and [Animation from Interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions) as relevant requirements for Web. Using these sources does **not** establish actual WCAG conformance. Desktop assistive technology and Android TalkBack have their own practical test needs; a single Web score cannot certify Qt or Android.

## 5. Motion is a representation of state, not a state machine

```text
Authoritative lifecycle transition observed
  → updated semantic Run/Work/Artifact projection
  → allowed MotionRole and user reduced-motion preference
  → platform-native visual transition (or immediate static update)
```

An animation can explain selection, navigation continuity, a card's arrival or that an output is now available. It cannot admit a Job, cancel an Attempt, prove artifact publication, establish source currentness or generate a fake progress percentage. A timed spinner is not worker heartbeat evidence; the presentation must fall back to `indeterminate` or an explicitly known stage/counter when a legitimate denominator does not exist.

Candidate motion roles include `feedback.press`, `navigation.context_change`, `inspector.open`, `work.new_item`, `run.progress`, `artifact.available`, `error.attention` and bounded `list.reorder`. The dated research suggested a duration ladder **0/80/160/240/320/480 ms** with small shifts around 4–12px. These are research starting points only; UI speed and reduced-motion preference must be measured on actual hardware and adapted per renderer.

When many Jobs are running, each card should not pulse endlessly. Surface attention is a scarce resource: group repeated progress, make unread/approval/error evidence distinct, and reserve persistent motion for genuinely ongoing activity where it aids comprehension. A failure state after a brief transition remains a readable static message, not a perpetual red flash.

**Reduced Motion** should suppress decorative movement/shimmer and substitute a static or restrained opacity change while preserving all meaningful state labels and accessible notifications. Keyboard/screen-reader updates must not announce a high-frequency progress tick on every polling cycle.

## 6. Form and navigation accessibility are semantic contracts

`InputFormSpec` might describe stable field ID, type, economic unit, required/default/preset distinctions, validation code, dependencies, sensitivity and the real effect scope of submission. Qt/Web/Android can render different controls: a desktop multi-column form, browser responsive fieldset or sequential mobile wizard.

Necessary properties:
- errors associated with the exact field and an overall submit summary;
- valid action via keyboard/touch/screen reader without hover-only controls;
- descriptive names for icon-only Run, file and approval actions;
- explicit units, reporting periods, bounds and blank-vs-zero behavior;
- safe handling of sensitive inputs, independent of remembered drafts;
- visible effect summary and a usable confirm/reject flow on the available display;
- resilience when resizing/reflowing during an unfinished form.

A narrow widget that cannot display a critical destructive-plan explanation must open a full trusted confirmation view instead of reducing security context to one swipe. Surface capabilities can omit an action entirely while product permissions still exist; **absence of a button does not imply denied rights**. Conversely an enabled-looking button cannot confer permission.

The ordinary desktop's keyboard productivity features (command palette, focus, search, virtualized data grids) and Android's adaptive window/back-stack/share intents are different renderers over the same Action ID and permission contract. [Android window-size class guidance](https://developer.android.com/develop/adaptive-apps/guides/use-window-size-classes) supports adapting to actual window geometry rather than “mobile = one column.”

## 7. Localization and financial data meaning

Russian is the primary current interface language, but object IDs and machine/action schemas cannot be translated into display labels. Message catalogs can localize warning/explanation text, units and formats; source-identifying official names, bank REGNs, classifier codes, numeric periods and dataset identifiers require controlled semantic preservation.

Locale affects rendering, not the underlying statistical claim. Comma decimal formatting, currency symbol placement, localized dates and report style may depend on consumer/export policy. An IFRS balance and RAS balance cannot become economically equivalent because both client UIs display “Corporate loans, ₽bn.” Reporting perimeter, time, source classification and qualified evidence remain domain truth.

## 8. Product attention: alerts, presence, diagnostics and status

One app may receive four different signals: external Node health, provider readiness, a Run's causal error and a domain validation warning. The UI can aggregate/sort for user attention while preserving **each source owner and original cause**. A red badge on every route turns the information architecture into alarm noise.

A safe display hierarchy: short user-facing status/action; inspector with step/effect detail; explicitly permissioned technical logs and trace. Presence is TTL-based from actual sessions, not proof a person is at the keyboard. Per-user unread counters must follow read receipts/cursors, not one shared Boolean on an Event. A source with a warning may still produce an allowed partial result; an external effect in doubt needs `UNKNOWN` and reconciliation, not a misleading success animation.

## 9. Acceptance evidence, risks and unresolved choices

The primary Product Surface Architecture study lists **18 competing/superseded UI claims (C07-01–18)**, 12 explicitly new open questions, and an unperformed checklist covering semantic parity, offline/reconnect, authorization, keyboard/touch/a11y, themes and large list performance. The physical design-token location, per-client toolkit, mobile-first scope, artifact preview, CSS/Qt mapping, contrast and font requirements remain Product/Design decisions.

High-value future probes:
| Probe | Falsifying result |
| --- | --- |
| Current Run shown in desktop, browser and Android | Contradictory outcome/available actions |
| Browser text zoom, long Russian legal-entity label | Control inaccessible or critical unit clipped |
| Keyboard-only approval from Inspector | Focus lost, scope hidden or hover dependency |
| OS Reduced Motion enabled | Decorative animation continues or status omitted |
| UI switches Light→Dark while workbook exists | Scientific data/artifact bytes change |
| Ten thousand Run events in list | UI freeze or unbounded memory |
| Eighteen simultaneous Jobs | Motion/notifications overwhelm user |
| Loss of connection during publication | Success from progress animation, not receipt |
| Widget with insufficient effect context | Destructive one-tap approval instead of safe deferral |
| Android phone/tablet rotation | Unsubmitted draft or selection disappears |
| Error summary for invalid numeric form | Wrong field association or absent screen-reader name |
| Color-only warning in high contrast | Error/unknown becomes indistinguishable |

No actual Qt a11y regression, Web WCAG pass, Android screen-reader/device comparison, font-license audit, color measurements or slow-PC performance benchmark has been performed by this study. A desktop prototype can preserve useful existing elements while better separating its Qt bootstrap from the application authority.

**Scientific conclusion:** shared semantics and role-based tokens can yield consistent user trust across distinct native renderers; the tests must confirm that *financial meaning, permission, execution outcome and accessibility survive adaptation*. The research does not mandate identical code/widgets, a new design repository or a production-ready Web/Android release.

## 10. Frozen motion-source tokens and sixteen state-driven behavior candidates

The dated desktop motion Research (`#L519-L717`) proposed an eight-token duration vocabulary and sixteen state-specific animation profiles. The exact **numbers are Research candidate tokens, not calibrated values, approved settings or code already in Windows**. The more durable insight is **motion follows the authoritative state and its meaning**; a spinner cannot establish an actually admitted Job, a file publication or an external source download.

### Eight original temporal tokens (candidates)

| Original research item | Proposed time | English intention and limitation | Original source line |
| --- | ---: | --- | --- |
| `SB-SRC-0040/DURATION-01` — `motion.instant` | 0 ms | Reduced-motion/disabled/structural snap; keep state meaning visible without transition. | L527 (`#L527`) |
| `SB-SRC-0040/DURATION-02` — `motion.xfast` | 80 ms | Immediate press, focus, tiny opacity feedback. | L528 (`#L528`) |
| `SB-SRC-0040/DURATION-03` — `motion.fast` | 160 ms | Hover settle, insertion or closing a small item. | L529 (`#L529`) |
| `SB-SRC-0040/DURATION-04` — `motion.normal` | 240 ms | A panel/content replacement transition. | L530 (`#L530`) |
| `SB-SRC-0040/DURATION-05` — `motion.slow` | 320 ms | Larger but still restrained structural transition. | L531 (`#L531`) |
| `SB-SRC-0040/DURATION-06` — `motion.emphasis` | 480 ms | Rare connected transition demanding visual continuity, not default navigation. | L532 (`#L532`) |
| `SB-SRC-0040/DURATION-07` — `motion.ambient.fast` | 1400 ms | Compact periodic indicator for genuinely ongoing work, subject to attention budget. | L533 (`#L533`) |
| `SB-SRC-0040/DURATION-08` — `motion.ambient.normal` | 1800 ms | Subtle low-attention process animation, not proof of actual computation. | L534 (`#L534`) |

### Sixteen original state/projection motion candidates

| Research item | Original state | English user-facing effect and budget | Source line |
| --- | --- | --- | --- |
| `SB-SRC-0040/STATE-01` | `idle` | Static; No continuous motion. | L702 (`#L702`) |
| `SB-SRC-0040/STATE-02` | `hover` | Fast fill/color change; Transient only. | L703 (`#L703`) |
| `SB-SRC-0040/STATE-03` | `pressed` | Tiny scale/shade; Transient only. | L704 (`#L704`) |
| `SB-SRC-0040/STATE-04` | `selected` | Border/fill settle; Transient only. | L705 (`#L705`) |
| `SB-SRC-0040/STATE-05` | `prepared` | Item entry or insertion; No continuous motion. | L706 (`#L706`) |
| `SB-SRC-0040/STATE-06` | `queued` | Static queue marker, optional tiny flow indicator; At most minimal ongoing indication. | L707 (`#L707`) |
| `SB-SRC-0040/STATE-07` | `running unknown` | Soft indeterminate process indication; May animate while authoritative state says running. | L708 (`#L708`) |
| `SB-SRC-0040/STATE-08` | `running known` | Determinate progress fill; Animate only on actual observed progress update. | L709 (`#L709`) |
| `SB-SRC-0040/STATE-09` | `waiting user` | One-time attention transition, then static; No continuous distraction. | L710 (`#L710`) |
| `SB-SRC-0040/STATE-10` | `waiting external` | Very subtle waiting indication; Limited ongoing motion, factual external-wait state needed. | L711 (`#L711`) |
| `SB-SRC-0040/STATE-11` | `success` | One-time status settle; No continuous success animation. | L712 (`#L712`) |
| `SB-SRC-0040/STATE-12` | `warning` | One-time accent transition; No perpetual warning pulse. | L713 (`#L713`) |
| `SB-SRC-0040/STATE-13` | `error` | One-time accent transition; No perpetual error pulse. | L714 (`#L714`) |
| `SB-SRC-0040/STATE-14` | `cancelled` | Short fade toward neutral; No continuous motion. | L715 (`#L715`) |
| `SB-SRC-0040/STATE-15` | `disabled` | Static disabled state; No continuous motion. | L716 (`#L716`) |
| `SB-SRC-0040/STATE-16` | `offline` | Static offline indicator; reconnect activity only; No animation except actual reconnect attempt. | L717 (`#L717`) |

**Challenges and limits:** reduced-motion settings must provide a static accessible equivalent; a loop should never imply progress without actual observation; animation must cease or be throttled when offscreen or idle; desktop and Android implementations may differ physically while carrying the same semantic role. Token values require actual device, accessibility and UX tests before Product admission. No native Qt/Android code or test result is claimed by preserving this table. It covers **24 exact-source locations** of a much larger motion original; complete source meaning remains unverified.
