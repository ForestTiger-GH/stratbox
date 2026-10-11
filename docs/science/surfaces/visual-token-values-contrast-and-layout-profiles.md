# Visual token values, contrast models and adaptive desktop layout profiles

**Problem and provenance.** The 2026-10-07 Strategy Box visual-system investigation (`SB-SRC-0043`, frozen Git blob `c0c0c352d9383fc0771168713abd7becbb46ba87`, L1–L2503) proposed a calm, compact and consistent user-interface visual language, with precise candidate palette and component metrics. This article preserves its **detailed design hypotheses** and the later settings-research disagreement without treating those numbers as approved, deployed or accessibility-certified. Actual desktop evidence is pinned to [Windows `959e9c4`](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b).

## 1. A restrained analytic workspace has four contrast levels

The original terms its direction **“Calm Operational Premium”**: a serious Windows-like data workspace that shares some conversation-feed ergonomics with messaging applications yet retains professional information density. The visually dominant area is neutral and carries content, not decoration.

Four levels organize salience:

1. **Workspace/canvas:** a muted base that provides continuity and comfortable long-session reading.
2. **Functional surfaces:** panes, explorer, composer, dialog, table or bounded case surfaces separated by subtle tone or borders.
3. **Interaction:** primary Run action, selected object, focus, link or progress receives localized brand accent.
4. **Exceptional semantic condition:** warning, error, success and destructive effect receive independent state colors and explicit labels/icons.

As a rule of thumb, the **larger a surface, the less saturated its default color**. High-energy logo gradients are appropriate on the app icon, splash/About, a small brand mark or tightly scoped live progress. They should not fill every sidebar, chat bubble or artifact table. Avoid cyberpunk/neon styling, all-glass panels, decorative dashboard cards, giant rounded pill controls and mobile-sized desktop text.

The original branding discussion drew the working accent from a blue cube logo. It suggested a quieter **Strategy Blue** for operational controls, rather than sampling the brightest electric gradient pixel into each UI element. The visual assets referenced in the original study remain historical inputs; this paper does not assert access to, alter or redistribute the logo files.

## 2. Three-layer token resolution plus native rendering

```text
Primitive values (e.g. blue.500 / gray.950 / space.3)
  → semantic roles (surface.canvas, text.primary, status.error.text)
  → component roles (run.primary.background, explorer.selection, bubble.running.edge)
  → native adapter: Qt QPalette/QSS/component metrics, later platform-native clients
```

The source recommends a 4px spacing base, selectively admitting 2/6/20/40/48px steps where compact widgets or large groups need them. Common conceptual roles include `surface.canvas/primary/secondary/elevated/hover/selected`, `text.primary/secondary/muted/disabled`, `border.subtle/default/strong/control`, `accent.default/hover/pressed/soft/text/focus` and `status.success/warning/error/info`.

The direct [dated QSS file](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/resources/styles/app.qss) still contains many literal values such as `#F4F7FA`, `#111827`, `#6B7280`, `#3D777B` and `#C7A27A`. It uses Segoe UI/Inter and 13px base text. The [mode rail code](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/shell/mode_rail.py) sets 96px width and 96×84px tile dimensions. These specific current observations **do not prove** the proposed semantic token engine or dark theme already exists.

Qt rendering could compile a resolved semantic-token bundle into QPalette, templated QSS and runtime widget metrics, then repolish safely on theme change. The source's package/directories are **illustrative physical candidates**, not an approved shared design repository.

## 3. Exact example palettes—candidates, not a brand authority

The original provides a detailed, internally consistent starting palette:

| Role | Suggested light | Suggested dark |
| --- | --- | --- |
| Canvas | `#F5F7FA` | `#111318` |
| Primary surface | `#FFFFFF` | `#181B21` |
| Secondary surface | `#F8FAFC` | `#1E222A` |
| Hover surface | `#F3F6FA` | `#272D36` |
| Selected surface | `#EEF4FF` | `#1B2A46` |
| Primary text | `#20242B` | `#F2F4F7` |
| Secondary text | `#5E6673` | `#B7BEC8` |
| Muted text | `#667085` | `#8D96A3` |
| Subtle border | `#E4E8EE` | `#2D333D` |
| Default border | `#D4DAE3` | `#3A424E` |
| Required control border | `#8A94A3` | `#667281` |
| Action accent | `#316BE5` | `#7EA8FF` |
| Soft accent background | `#E5EDFF` (light scale) | `#1B2A46` |
| Accent text | darker blue where needed | `#B9CFFF` |

The source's light blue ramp is `#F2F6FF`, `#E5EDFF`, `#C9D9FF`, `#A6C0FF`, `#79A0F7`, `#316BE5`, `#2B62D5`, `#2456BC`, `#1D469B`, `#173879` for 050–900. Dark accent roles explicitly differ: default `#7EA8FF`, hover `#91B5FF`, pressed `#6D98F4`, soft `#1B2A46`, text `#B9CFFF`; the suitable primary-button foreground may be dark `#0E2148`, not white.

Status colors must remain independent from the configurable accent. Examples from the source: light success background/text `#EAF7F0 / #176B4A`; warning `#FFF4D6 / #8A5A00`; error `#FFF1F0 / #B42318`; information `#EEF4FF / #245BBE`. Dark equivalents: success `#163629 / #8ED7B5`, warning `#3A2C12 / #F5CA6B`, error `#3A1D1D / #FFAAA3`, info `#1B2A46 / #AFC8FF`. **Every mapping still needs measured contrast/accessibility review under actual font size and renderer.**

A fully black `#000000` dark canvas is rejected by the study in favor of a layered graphite spectrum. Avoid relying solely on a colored pill for a status: use **icon + readable label + color**. A disabled grey must not stand in for important secondary data.

## 4. Typography, geometry and responsive desktop profiles

The original recommends platform font fallback **Segoe UI Variable → Segoe UI → Inter → system sans**, with no need to distribute a proprietary font file. Its compact desktop base is **13px** with about **19px** line-height; examples: 11px technical chip/meta, 12px hint, 14px item title, 15px case title, 16px panel title, 18–20px page header and rare 22–24px hero dialog heading. Weight 500–600 generally replaces excessive 700 bold. Mono font (e.g. Cascadia Mono/Consolas) belongs to technical IDs, paths, logs and code, not body prose.

| Component | Original suggested size/role |
| --- | --- |
| Brand header / top bar | 52–56px / 48–52px |
| Mode rail | 88–96px; current 96px |
| Left context panel | 240–300px |
| Right inspector | 360–420px |
| Useful central canvas | approximately 560px minimum |
| Main window | ~1120×700 minimum; 1360×820 comfortable; larger at 1600×900+ |
| Typical control | 32–36px high; primary Run 44–46px |
| Explorer row/header | 34–36px / 32–34px, with 16–18px icons |
| Functional button/input radius | usually 6–8px; cards 10–12px; conversation case ~14px |
| Scenario case | width ~300–760px, pad ~14×12px, restrained accent tint |
| Notice | width ~220–620px, pad ~12×9px, smaller radius |
| Spacing | usually 8px micro, 12px gap, 16px padding, 24px section break |
| Borders/elevation | selective 1px subtle lines, almost no permanent shadows |

These are **research examples**, not mandatory fixed pixel dimensions for all platforms. A large rail remains native desktop geometry; Android should reuse typography *roles* and presentation intent, never QSS or 96px navigation.

For wide windows (~more than 1450px), both context panel and inspector may remain visible. In the mid-range (~1150–1450px), adaptive sizing preserves the central task. On narrower desktop windows, the source suggests collapsing context and switching inspector to overlay rather than squeezing the work canvas. These are layout hypotheses requiring actual responsive and low-resolution tests.

## 5. Component-specific meaning and restrained progress motion

Scenario conversation was intentionally treated as a strong existing interaction pattern: separate inbound/outbound case bubbles, status/action/artifact summary, new-messages affordance and no forced auto-scroll while a person is reading history. This is **dated UI evidence**, not proof that Scenario remains the long-term central Work ontology.

A running case can express liveness with a *small* animated gradient edge or bounded status cue, not a glowing full-card backdrop. On completion, the animation stops. A spinner is better reserved for very short indeterminate tasks; long analytical Runs need stage progress and reliable status regardless of client animation.

Original duration candidates: about **83ms** for micro fade, **120ms** for short transition, **167ms** for standard fast feedback, **200ms** for drawer/panel movement and **250ms** for major transitions. Hover 80–120ms, selection 120–167ms, drawer 180–220ms, dialog 180–250ms and scroll 160–180ms are examples. Running progress edge had a slower, non-disruptive ~1.8–2.4s cycle.

Reduced-motion mode should eliminate decorative movement and turn running gradients into static indicators. Hover states, pointer affordances, glass/Mica/Acrylic surfaces and dense rail gestures are adapters, not universal UI semantics. The platform's reduced-motion/high-contrast accessibility controls must take priority over personal brand accent where required.

## 6. Contrast, one custom accent and system protection

The source cites accessibility targets of **4.5:1** for normal text, **3:1** for large text and **3:1** for required non-text UI indicators/focus. These are the standards relationships reported by the source, **not independent measurement** of every sample palette or implementation. Check the official current standard and the exact visual context before release.

A custom accent is a single user color input. The study proposes perceptual **OKLCH** derived roles rather than naive RGB lightening/darkening, followed by contrast-aware adjustment per actual text/control role. Important status semantics do not change. A Windows high-contrast/Contrast Theme can override the custom accent with accessibility colors; hardcoded QSS risks blocking such behavior.

The later, fully read `SB-SRC-0044` Settings study agrees on theme and accent but **narrows initial user controls** to those two only. The present visual study proposed optional `Comfortable/Compact` density and motion preference UI, while later settings reasoning treats density as product-controlled until user need is demonstrated and reduced motion as system-controlled by default. This is a **dated research revision/partial conflict**, not evidence either choice was officially admitted. The underlying design **must still define density and motion semantics** even if their end-user toggles are withheld.

## 7. Explicit non-goals, candidate acceptance and untested release checks

The source rejects rainbow categories, persistent heavy shadows, all-white card canvas, full glass sidebars, strong second tan “Details” accent, excessive bubble rounding, purple/cyan glow across work, arbitrary separate component colors and oversized web/mobile typography on desktop. It proposes retaining the current three-zone information density, mode rail, message width logic, inspector and quick Run focus while replacing scattered constants with semantic tokens.

The original proposed separate **light, dark, custom-accent and motion** acceptance lists plus priority P0 tokenization/light cleanup; P1 dark, appearance and accent; P2 contrast/high-contrast and motion refinement. Useful unperformed probes include text/input contrast at real scales; no status confusion with custom accent; reversible theme switching without restarting; keyboard focus readability; a dark-table/worklog long-session review; OS reduced-motion replacement of decorative animations; resizing while an inspector is open; compact-density height/readability; and Android semantic parity without copying desktop geometry.

A visually polished screenshot cannot certify those behaviors. Reopen on real client rendering benchmarks, measured color contrast, current Fluent/WCAG revisions, a changed logo/brand decision, user tests on slow PCs, implemented dark/high-contrast providers or formal Product approval of optional density/motion controls.

**Related scientific owners:** [semantic design tokens, motion and accessibility](semantic-design-tokens-motion-and-accessibility.md), [settings eligibility and user controls](../application-state/settings-feature-admission-and-contextual-controls.md), [client semantic portability](semantic-portability-and-client-authority.md), [product-owned extension surfaces](../extensions/configuration-catalog-readiness-and-surface-boundaries.md).
