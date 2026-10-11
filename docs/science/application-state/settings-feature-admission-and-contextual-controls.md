# Choosing what belongs in Settings: preferences, contextual controls and safe restoration

**Scientific scope:** recover the user-centered distinctions and counterexamples in the 2026-10-07 Strategy Box system-settings investigation (frozen source `SB-SRC-0044`, blob `bedb3628f3a58a27c9de10b7a19043549c281dca`, L1–L2752). The purpose is to determine **when a control deserves a persistent user preference**, rather than add more settings to an application that already remembers state. **Status:** primary Research, target-oriented, not an adopted UI schema, implemented migration or observed multi-device service. Direct-code descriptions refer to the pinned [Windows snapshot](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b).

## 1. A setting must earn its place

The source proposes eight cumulative tests for a visible setting. It represents an enduring personal preference, applies across sessions or work contexts, has an intelligible choice beforehand, changes infrequently, cannot be inferred reliably from the operating system or last meaningful UI state, is not an ordinary workflow action, is not a particular Run/Scenario input, and is not an administrator's policy masquerading as a user option. Several failures strongly indicate a different semantic owner.

In the dated Windows implementation, `SettingsDialog` used three tabs: **User**, **Workspace** and **System**. Only the first contained user-configurable startup behavior: open right inspector, initial left mode and inspector tab. Workspace displayed schema/root/Data and open/copy actions; System displayed run mode, launch origin, node, session, user, host, source revision and copy-diagnostics. These last two are primarily **information and operational actions**, not preferences. The then-current `AppUserConfig` mixed window size, pane widths, last Scenario, form values, selected participant, chat filter and other shell coordinates in one persisted object.

The research classifies those values into **five** core categories: `UserSettings`, automatic `SurfaceState`, continuation `RecentState/DraftState`, `ManagedPolicy`, and specific immutable `RunParameters`. A later independent [state-scope model](settings-policy-preferences-and-drafts.md) also calls out versioned Automation configuration as a sixth distinct concern; count differences describe scope evolution, not a reason to collapse it into personal Settings.

## 2. Remove the wrong knobs while retaining useful behavior

| Existing or tempting control | Intended destination | Why it is not a global user preference |
| --- | --- | --- |
| “Open inspector on startup”, startup left mode, default inspector tab | Automatic `SurfaceState` restoration | The user's last actual layout is more informative than a contradictory startup override. |
| Window dimensions and splitter widths | Local client `SurfaceState` | Changed frequently; a product or device default is sufficient at first launch. |
| Chat filter and selected participant | View/navigation continuation | Temporary context, not a durable shared behavior policy. |
| Last Scenario/workspace | `RecentState` and workspace navigation | A re-entry destination, not a global settings choice. |
| Values typed into a Scenario form | Versioned `ScenarioDraftStore` | Potentially sensitive, schema-dependent, not a previously accepted Run input. |
| Workspace path/Data root | Workspace Explorer/Node information and trusted environment binding | Physical path selection cannot silently override a managed storage authority. |
| Node/session/host/build identification | Node, About, Diagnostics | Read-only facts about this activation; no preference effect. |
| Background job enablement or retry policy | Automation/Run control plane | This is an operational command with real effects and authority, not presentation. |
| Log level, retention, telemetry endpoint, crash policy | Runtime/managed configuration and Diagnostics | Exposes sensitive support policy and risks misrepresenting the actual diagnostic owner. |
| Update channel, Python environment or package installation | External installation/deployment owner | A product UI may link to permitted platform action, never duplicate the package manager. |
| Proxy, TLS mode, private endpoint, credential source | Authorized environment capabilities/policy | Infrastructure scope and secret protection differ from user preference. |
| AI provider/model/token controls before a real AI capability exists | No public settings section yet | Empty configuration anticipates a nonexistent Product commitment and may bypass authority. |
| Locale/unit conversion of official banking figures | Analytical/data/result semantics | Display localization cannot silently change reported unit, series scope or evidence. |

A global output-directory switch is also discouraged: the product should produce managed artifacts, then materialize/export them to a chosen destination when appropriate. A particular operation may accept an explicit destination parameter. A global format-specific export selector is similarly inferior to a Scenario/Run parameter.

Historical preferences need not survive as API aliases; **real saved drafts, meaningful personal values and accepted analytical history** still need an explicit bounded migration/disposition. “No API backward compatibility” never means “delete useful user records”.

## 3. A three-section initial information architecture, with a real feature gate

The source's proposed first real user-settings surface has only:

1. **Appearance:** inherit system/light/dark theme (default **system**); choose Strategy Box/system/custom accent (default **Strategy Box**). A custom color is an input to a contrast-checked derived semantic token ramp, not a way to recolor warning/success or every panel.
2. **Artifacts and reports:** one effective default report style profile, plus a document creator label (default **“Strategy Box”**). Both must be resolved, versioned and captured for an actual output.
3. **Extensions:** a safe list of available neutral capabilities, compatibility, state, allowed activation, declarative configuration, readiness and linked platform installation management. Details are covered in [extension configuration and surfaces](../extensions/configuration-catalog-readiness-and-surface-boundaries.md).

A fourth **Notifications** page is conditional upon an actually working OS/managed-background notification service. It can govern notification delivery about own long Runs, failures, assignments and node conditions; a preference must **not** hide important problems from the in-app Work or Diagnostics state. Ordinary successful background refreshes can default to quiet.

Avoid permanent empty categories such as General, Advanced, System, Network, Storage, Behavior, Updates, AI or Background. A separate settings search bar also adds little with three sections. “About” can be a neighboring information destination but remains distinct from preferences. Organize settings by **what the user chooses**, with control-level indication of personal/workspace/managed scope; do not create three top-level menus merely because there are three storage owners.

## 4. Restraint is part of the visual contract

A coherent product UI owns its theme, typography, iconography, status semantics, motion, density and accessibility. The initial user-facing appearance selection should have **only theme and accent**. Individual backgrounds, chat bubbles, radii, borders, font family, icon pack, arbitrary QSS/CSS, animations and sidebar width are either product-designed or restore automatically.

The 2026-10-07 Research explicitly advised against exposing density until actual usability demand and test coverage justify `Comfortable/Compact`. Reduced motion should preferentially follow a platform accessibility signal; an in-app override requires a demonstrated unsupported environment or request. High contrast and status token legibility are engineering conformance duties, not a promise fulfilled by a theme dropdown. Future Android must adapt rendering, not reuse Windows-specific geometry.

## 5. Drafts, first launch, resets and save semantics

The desired first launch needs almost no onboarding: system theme, Strategy Box accent, standard report profile, creator label “Strategy Box”, safe optional-notification defaults and platform-selected bindings. An extension requiring authorization gets **its own** readiness task rather than a global wizard.

One visible “Reset user settings” action should affect `UserSettings` only. A separate “Reset layout” may repair `SurfaceState`. Neither resets Work, saved artifacts, historical Runs, draft provenance, protected logs, extension configuration or managed policy. A corruption repair may fall back to safe defaults but must signal the repair and preserve independent durable evidence.

Immediate apply is suitable for theme, accent, notification choices and safe scalar defaults; scoped “Apply extension configuration” is appropriate when validation, permissions or restart/binding changes are transactional. A universal Save/Apply/Cancel mechanism would inaccurately impose one lifecycle upon all classes.

Settings service resolution is not equivalent to recursively merging dictionaries. A useful UI projection is:

```text
SettingState(
  effective_value, stored_user_value, source_scope,
  editable, allowed_values, reason, restart_required, revision
)
```

Forced managed values, allowed ranges, workspace defaults, user preferences and explicit effective Run parameters have different precedence rules. Show the reason for a policy lock; preserve both stored and effective values instead of silently overwriting the person's preference. An AI or scheduled execution may **use** an effective default but may **change** it only through separately authorized mutation.

## 6. Portable settings models, selective sync and scientific evidence

A candidate application-neutral model has typed `AppearanceSettings`, `ArtifactDefaults`, optional `NotificationSettings` and a versioned `UserSettings`. Separate `SurfaceStateService`, `ScenarioDraftService`, and namespace-aware extension configuration avoid one permissive arbitrary dictionary. The core analytics library should receive **resolved business/output context**, never read desktop `app.json` or own window preferences.

Candidate cross-device sync: theme mode, accent choice, creator label, default compatible reporting profile, meaningful notification semantics and explicitly user-scoped extension selection. Do not sync window geometry, scroll, selected tab, local file path, device notification permission or a private draft by default. Concurrent updates need a named revision/conflict policy; client timestamps do not establish server authority.

A simple verified, versioned JSON store can be proportionate for local personal preferences. Managed shared Work, automation schedules and policy decisions need stronger concurrency, authorization and recovery semantics. Validate before save and commit only with actual file/backend guarantees; do not describe an abstract `replace()` method as universally power-failure atomic. No raw secret values belong in settings. Significant changes to workspace business defaults or shared provider configuration may warrant audit, whereas changing a personal accent generally does not.

## 7. Negative tests, source checklist and reopening conditions

The original §§65 and 89 list many intentionally rejected switches and a state-destination matrix, while §§86–87 specify candidate tests and **17** acceptance criteria. Material probes include corrupt `app.json`, a personal setting reset that preserves Work, on-device layout restoration, immediate accent/theme change with contrast and system fallback, policy-forced reporting profile, provider readiness, schema-incompatible draft revalidation, sensitive value exclusion, extension contribution refusing arbitrary UI injection and an output with different user-provided creator label versus authenticated execution actor.

These are **proposed** checks; no installed Windows/Android build or migration acceptance is claimed. Reopen the minimal surface when a real OS notification backend, second language, proven density need, multi-device synchronization, new authoritative platform policy/identity contract, or a second implemented client changes the user need and scope.

**Related science:** [settings state separation](settings-policy-preferences-and-drafts.md), [artifact style and creator proof](../artifacts/report-formatting-profiles-metadata-and-evidence.md), [semantic tokens and accessibility](../surfaces/semantic-design-tokens-motion-and-accessibility.md), [Work/Run authority](../work/admission-planning-resource-scheduling-and-recovery.md).
