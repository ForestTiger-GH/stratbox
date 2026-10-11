# Report formatting defaults, output metadata and reproducible style resolution

**Research lineage clarification (subsequent primary read):** the later full `SB-SRC-0042` customization original explicitly **revises** the earlier ReportProfile/default-overridable-tokens suggestion documented here. Its candidate concept is the independently versioned, compiled, provider-neutral [single effective ArtifactStyleSet](atomic-style-set-cross-format-resolution-and-conformance.md), with **only named approved variants**, no arbitrary runtime font/color merge and strict cross-format applicability by default. Read this article's `ReportProfile` and `overridable_tokens` as **historical earlier Research alternatives**, not concurrently accepted final public APIs. The source-specific choice has not been adopted as a Product Decision; the primary studies share a dated research lineage and are not independent production validations.

**Problem.** An analytical application produces data-derived files whose reporting style and document-core properties must remain explainable even after the user changes their interface theme, a provider disappears, or a calculation runs remotely. **Source:** the independently read 2026-10-07 settings investigation (`SB-SRC-0044`, source blob `bedb3628f3a58a27c9de10b7a19043549c281dca`, especially §§13–19, 35, 40–43, 60, 73, 77–79 and 83–87). **Status:** research-backed candidate conventions, not a shipped cross-format renderer or accepted enterprise reporting standard.

## 1. Shell appearance and analytical report presentation are separate

A theme and accent change **how the application interface appears**. A report profile changes **how an analytical result is rendered** in XLSX, DOCX, PPTX and, where supported, PDF. They may use conceptually related tokens but have different identities, version histories, consumers and provenance. A UI accent must never silently recolor a previously accepted financial report; a report provider must never replace desktop shell fonts, Qt widgets, navigation, or accessibility semantics.

The original settings proposal intentionally avoids twenty small switches for table borders, headline colors, number formats, font choices and chart palettes. It offers one coherent **Default reporting profile** selector. The selected profile is a preference that influences *new executions*, while the **resolved immutable effective profile** is part of an individual output's reproducibility evidence.

This proposal interacts with a separate [ArtifactStyleSet scientific model](output-identity-publication-and-availability.md): `ReportProfile` in the original study is a user-facing profile vocabulary, not automatically a new independent core ontology or an alternative truth owner. A maintained implementation should reconcile a profile selection with its resolved declarative cross-format style set.

## 2. Profile declarations and controlled overrides

The source proposed a generic `ReportProfile` carrying:

```text
profile_id, version, title, provider_id,
fonts, semantic_palette, number_formats,
table_roles, chart_roles, metadata_defaults,
overridable_tokens
```

A provider may contribute report color roles, acceptable fonts, number formatting, branded headers, chart themes and document templates through **declarative, validated reporting resources**, never arbitrary UI code. A profile's applicable artifact formats and renderer features require explicit capability checks; identical names do not imply identical physical rendering across office formats.

Default behavior is one selected profile. A “Font” or “Report accent” advanced control is conditional upon the **active profile explicitly declaring those tokens overridable**. This prevents a managed company report template from being accidentally compromised by ad hoc per-user font or color selections. Fonts need availability/embedding and fallback rules; colors need contrast and appropriate semantic roles. Separate independent XLSX/DOCX/PPTX profile pickers for the same Run would ordinarily undermine consistent reporting identity.

User-visible report-profile choices belong where business outputs are configured: **Artifacts and reports**, rather than buried under extension package details. Neutral extensions may contribute profiles, but their resource IDs must be namespaced and collisions are validation errors, not an implicit first-registered-wins policy. The source's example IDs (such as `strategy.standard`) illustrate a naming direction only and must not be interpreted as a published installed catalog.

## 3. Author is a human-readable document property, not execution authority

The proposed single global preference is:

```text
Document author label = "Strategy Box"
```

It maps through format adapters, **where actually supported**, to:
- XLSX: `workbook.properties.creator`.
- DOCX: `document.core_properties.author`.
- PPTX: `presentation.core_properties.author`.
- PDF: corresponding supported author metadata if the selected writer implements it.

This distinction matters to privacy, reproducibility and authorship. A user-editable Office creator is **presentation metadata**, while the actual authenticated initiator, execution actor, reviewing user, provenance chain and publication authority are separate audited facts. The UI value can equal “Strategy Box” for a report produced by a named operator; neither fact should erase the other. OS username/email must not be silently copied into public output metadata.

Other properties—title, subject, category, keywords, timestamps, source/Run/artifact IDs—should generally follow the actual operation and output, rather than global reusable settings. A uniform author field is more coherent than three unrelated “Excel author / Word author / PowerPoint author” preferences.

A candidate author-label validator performs trimming, rejects control characters and uses a bounded maximum appropriate for the writer; a blank label should resolve safely to the approved default, with no automatic replacement by a personal login identifier.

## 4. Resolve exact input, render, publish and record a receipt

The source distinguishes `requested_profile`, `resolved_profile`, `resolution_reason`, `provider`, profile version and final creator label. A minimal stable sequence:

```text
product or workspace profile default
  → personal default, if permitted
  → explicit Scenario/Run output choice
  → managed policy + allowed format + provider readiness
  → EffectiveReportProfile(profile_id, revision, tokens, reason)
  → export adapter(s) + metadata adapter(s)
  → produced bytes, actual content hash/manifest
  → ArtifactRef, Run/Attempt, output revision and provenance receipt
```

This is **conceptual**. The exact precedence between an approved forced workspace profile and explicit Run override is a Product/Policy decision; applying each as a blind dictionary merge is unsafe. The actual backend still must prove staging, physical byte integrity, durable publication and supported export behavior. Merely selecting a profile in Settings does not prove that an XLSX/PPTX conforms.

If a saved external profile is missing, the original investigation proposed **visible, recorded fallback**: preserve the requested unavailable preference, display its unresolved state, use a known built-in profile for permitted new runs and record the **actual** profile used. This is preferable to silently replacing the stored user choice or pretending branded output was produced. Whether a strict corporate profile allows fallback at all is a managed policy/security decision: a required template may need fail-closed publication.

A remote worker must resolve its own actual report capability and permitted resources. Local client installation says nothing about remote host readiness. Historical committed artifacts retain the effective profile ID/version, relevant export options and creator value even if the user's defaults or providers later change.

## 5. Reporting style resources versus evidence about banking facts

An aesthetically consistent table remains dependent on correct units, perimeters, dates, revisions, source bytes and calculations. A report profile does not strengthen a scientific claim. Number formatting is particularly sensitive: choosing a display scale or precision must preserve explicit meaning and avoid silently converting a missing or qualified value to authoritative “zero”.

A record adequate to reproduce an analytical artifact needs both **subject computation** and **rendering** provenance, which must stay independently distinguishable. Content identity, authority to publish, user acceptance, editable document metadata and the current availability of an optional external style provider are separate predicates.

The proper core boundary is a typed `ArtifactFormattingContext`/`DocumentMetadataDefaults`, compiled declarative profile resources, and export adapters. The application retains the user's preference, resolves the plan and captures historical effective input. Domain core does not query a Windows preferences file.

## 6. Specific unperformed verification probes

- Default “Strategy Box” creator is written and can be read back in every actually supported document format; unsupported writers report their limitation.
- A formatting profile is resolved by stable ID and version, compatible format and permitted provider; equivalent remote execution records the same requested/resolved semantics, not necessarily byte-identical fonts.
- A profile allowing no font override cannot be changed through a stray UI field or provider payload.
- Requested provider disappears: both requested and resolved identity remain visible; no silent brand switch or false success.
- A mandatory managed style has no valid provider: the publication gate behaves according to explicit policy, potentially failing closed.
- Theme/accent changes while a report is running do not change analytical values or a sealed style snapshot.
- Editor-modified Office author metadata never rewrites the actual product provenance principal.
- XLSX, DOCX and PPTX adapters preserve a common conceptual author field without losing format-specific validation/limitations.
- Changing the preferred default does not retroactively mutate the old Run's format configuration or committed bytes.
- Template resource licensing, embedding, accessibility and PDF metadata behavior remain separately verified rather than presumed supported.

**All are future tests.** The original Research and this article do not prove the current Windows app has integrated full cross-format generation. Reopen on an exact format writer implementation, a registered style provider, a real policy profile, a documented format-specific failure or approved cross-device preset sync.

**Related science:** [artifact identity/publication](output-identity-publication-and-availability.md), [settings-state authority](../application-state/settings-policy-preferences-and-drafts.md), [minimal Settings UI](../application-state/settings-feature-admission-and-contextual-controls.md), [generic configured contributions](../extensions/configuration-catalog-readiness-and-surface-boundaries.md), [economic evidence validity](../data-and-knowledge/observation-semantics-comparability-and-claims.md).
