# Bounded thematic reconciliation: visual roles versus exposed user preferences

**Theme and consumer:** decide which *visual semantics* Strategy Box must own independent of native renderer, and which *end-user controls* are justified in a minimal Settings page. Consumer: future target product/UX decision and Science cross-topic coherence; this is **not** an accepted release UX contract.

**Primary exact sources:**
- `SB-SRC-0043` Visual System Research, frozen blob `c0c0c352d9383fc0771168713abd7becbb46ba87`, L1–L2503; notably `§§54–61` L1483–1647, `§§75–76` L1864–1914, `§§80–85` L1952–2083, `§§93–106` L2216–2392.
- `SB-SRC-0044` System Settings Research, frozen blob `bedb3628f3a58a27c9de10b7a19043549c281dca`, L1–L2752; notably `§§7–9` L362–506, `§§30–34` L1169–1324 and the non-settings register `§65` L2071–2097.
- Dated current Windows source: `stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`, `src/stratbox_windows/resources/styles/app.qss`, `presentation/qt_desktop/shell/mode_rail.py`, `runtime/config.py` and SettingsDialog.

## Concerns not actually in dispute

Both studies describe an application-owned visual language, theme and accent choice, semantic status colors independent from personal accent, accessibility constraints and native renderer adapters. Both reject provider-controlled shell skinning or arbitrary widget injection. Both separate UI colors from generated artifact/report style profiles. The present implementation already has a calm neutral Qt shell and hardcoded QSS constants, but no certified cross-client token pipeline.

An underlying **density token scale** and a **reduced-motion semantic mapping** can be important engineering responsibilities even when the user sees no density/motion toggle. Confusing “capability must exist” with “setting must appear” creates an artificial conflict. A later Android renderer must not inherit Qt geometry merely to claim semantic parity.

## Genuine target UI-scope tension

| Question | `0043` visual research | `0044` settings research | Qualified reconciliation |
| --- | --- | --- | --- |
| Density modes | Candidate Comfortable/Compact options, proposed metrics and visible Appearance choice; priority `P1`. | Exclude density from initial Settings: doubled conformance cost and unproven user demand; consider later after use evidence. | **OPEN PRODUCT CHOICE**: preserve token/model adaptability; default one tested comfortable density for initial UI unless authorized human UX decision changes it. Do not declare a control shipped. |
| Motion setting | Appearance preference proposed alongside system reduced-motion signaling. | Prefer OS reduced-motion setting; separate in-app override only for an actual unsupported system bridge or demonstrated need. | **OPEN UX INPUT**, but system accessibility takes priority for implementation correctness. |
| Neutral temperature | Early optional Cool/Neutral second-order customization idea. | Minimal Theme/Accent user-facing inventory; reject unnecessary technical style knobs. | **HISTORICAL OPTIONAL CANDIDATE**, not default feature. |
| Theme and accent | System/light/dark plus brand/system/custom; OKLCH derived ramp, contrast checks. | Same two choices; explicitly the only first-stage Appearance controls. | **CONVERGENT RESEARCH DIRECTION** but no approved implementation or passed high-contrast check. |
| Source numeric tokens | Several candidate hex colors, sizes, timing durations. | User should not control each component; visual design is app-owned. | **COMPATIBLE**: candidate design tokens are implementation/testing inputs, not user preference APIs. |
| Asset and typography | Visual study cites supplied logo and prefers platform fonts. | Extension styling of produced reports is separate; UI font not user/provider setting. | **COMPATIBLE**: visual logo depiction has separate provenance; never infer downloadable brand assets from text alone. |

## Additive source-specific challenge — the separately read Motion Research

The fully read `SB-SRC-0040` Motion Research at exact blob `199ebe15e1dae7e3003c1976d5ea9093dde9cbe9`, L1–L3414, adds a **third dated primary Research Result**, sharing its historical Windows/design input family with `0043` and `0044`. This is additional subject detail, **not independent tested user evidence**.

| Concern | Motion source `0040` | Visual/source `0043` or Settings `0044` | Disposition |
| --- | --- | --- | --- |
| Everyday timing | Reusable tokens 0, 80, 160, 240, 320, rare 480 ms; more than 600ms rejected for normal navigation. | Visual `0043` presented 83, 120, 167, 200, 250ms component-scale suggestions. | **Distinct candidate numerical profiles.** Preserve both. Contract and actual installed widget benchmarks must settle exact timings. |
| Ongoing gradient loop | Single low-opacity process rail travelling 1.4–1.8 seconds. | Visual `0043` indicated approximately 1.8–2.4 seconds for a thin working-case gradient. | **Concrete Research-level mismatch.** A 1.8-second boundary overlaps, but there is no authoritative adopted interval. Compare on device with simultaneous tasks. |
| Reduced Motion | Strong first-class FULL/REDUCED/OFF policy; `§31.3` proposes optional user override when helpful; version-sensitive Qt accessibility provider. | Later Settings `0044` suggests OS-first behavior and no visible separate preference unless user/platform need is proven. | **Compatible internal necessity; visible override OPEN.** Never conflate lack of UI toggle with lack of reduced-motion support. |
| Work/Scenario navigation and timeline | Four top-level destinations and Scenario-centric Run card animation are inherited dated target models. | Later whole-system and Work object Science distinguishes Work, Run, Job, Attempt and Artifact independent identity. | **Terminology needs semantic re-projection.** Reuse presentation causality without turning old Scenario visual vocabulary into Product ontology. |
| Progress and remote receipt | Rich queue/running/cancel storyboard, 57 named roles and a state-motion matrix. | Later execution/recovery Science draws stronger distinctions between accepted local intent, remote receipt, actual running and published result. | **Later correction expands validity envelope.** Ambient motion may show only current confirmed execution, never invent a backend state. |
| Direct scrolling and log tail | OS-native physical scroll; user-position-aware auto-follow; exact 160/240/320ms app scroll candidates, no per-line log animation. | Visual study emphasizes short comfortable scroll and settings study excludes scroll state from preferences. | **Substantively compatible**; retain important scroll anchoring and large-stream constraints in independently readable Science. |
| Qt perf/device tests | Targets 60fps, 50–80ms input feedback, virtual motion clock, 20 simultaneous tasks and 100k log lines. | Visual token study proposes accessibility/contrast work; neither provides installed measurements. | **OPEN assurance**, do not upgrade source recommendations to passed tests. |

The scientific owner for this new source is `docs/science/surfaces/state-driven-motion-scrolling-and-execution-feedback.md`. Its source-addressed producer ledger is `units/BASE-STUDY-MOTION-0040.jsonl` (**257 provisional entries**); source `0040` remains `material_unit_state=unaccounted`. Existing `0043` and `0044` source ledgers are not automatically independently verified by this comparison. Product scope and exact motion tokens, reduced-motion preference exposure, semantic status mapping and performance acceptance remain awaiting design authority and direct runtime evidence.

## Evidence dependence and no false convergence

All three originate in the same dated design sequence, quote overlapping Windows implementation baselines and use similar platform guidance. Their agreement is **not two independent empirical accessibility or user-preference studies**. The later `0044` study expressly says it simplifies the Appearance user surface relative to the visual work. That supports the *direction of a narrowed proposal*, not its automatic status as an authorized Product Decision. Specific pixel palette proposals remain research/test inputs until design ownership and actual device/conformance evidence accept them.

The early visual source's contrast ratios are standards references **as reported by its author**, not measured validity of the listed palette; reproduce verified ratios only after direct standards and actual rendered color/focus tests. No named user test or actual Android experiment is established by these three source documents.

## Coverage dispositions and downstream implications

- **Covered in maintained Science:** visual semantics/palette/examples in `docs/science/surfaces/visual-token-values-contrast-and-layout-profiles.md`; restrained Settings/conditional exposure in `docs/science/application-state/settings-feature-admission-and-contextual-controls.md`; generic visual/accessibility baseline in `docs/science/surfaces/semantic-design-tokens-motion-and-accessibility.md`.
- **Open:** user research on density control, platform reduced-motion detection, eventual second renderer, high-contrast mapping, contrast measured at 13px text, responsive geometry on slow machines, actual design token code ownership and report style independence.
- **Historically retained:** early optional per-user density/motion/neutral-temperature settings, exact spacing and color candidate values, including reasons the later Settings study withheld controls.
- **No claim made:** no accepted global design tokens, layout modernization, brand-palette adoption, cross-platform theme or installed accessibility conformance.
- **Reopen:** direct current implementation change, real Accessibility/UX test, formal brand decision, first Android renderer, system platform feature limitations or an authorized Product Decision.

**Verdict of this thematic Work:** `RECONCILED_AT_SCOPE_LEVEL_WITH_EXPLICIT_PRODUCT_CHOICE_OPEN`, not complete Science assurance or global Research Amputation.
