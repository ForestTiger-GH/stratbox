# Atomic ArtifactStyleSet resolution and cross-format rendering conformance

**Scientific question:** how can independently supplied visual resources produce consistent, reproducible human-facing statistical reports across XLSX, DOCX, PPTX and PDF, without allowing package discovery, styling choices or environment differences to silently redefine the output? **Primary:** complete 2026-10-07 customization Research `SB-SRC-0042`, frozen blob `0ff9a0ac61be5d128cd16a411017040ae8b7e5`, L1–L2447. **Status:** detailed target architecture hypothesis, not current public API, authorized Product Decision, installed multi-format renderer or independently verified report output. Earlier [report-profile research](report-formatting-profiles-metadata-and-evidence.md) uses a looser vocabulary; the later original explicitly requests its refinement.

## 1. Distinguish four independent kinds of customization

The source's central model separates `Plugin` (a possible business-capability carrier), `ArtifactStyleSet` (a passive, versioned visual language), `InterfaceTheme` (client-owned shell presentation) and `ArtifactMetadataContext` (document information and provenance). A template is a **fifth distinct concept**: a document/slide/workbook structure, which can be bound to a style set but does not define its semantic visual language.

A resource may be built in, declared by a neutral extension, delivered in a standalone **data-only style package**, bound by a managed environment, or possibly imported by a user after permissioned validation. The resource continues to have its own stable identity after its contributing provider is disabled. No resource is authorized to inject Qt widgets, application QSS, shell fonts, arbitrary executable rendering hooks or navigation. A client theme can use a similar blue palette by **deliberate design agreement**; changing the client's preferred accent must not automatically recolor an accepted board report.

The original insists on exactly **one effective complete `ArtifactStyleSet` per execution context** for all its applicable human-facing artifacts. It rejects runtime mixing such as font from Set A, table background from Set B and PPTX chart palette from Set C. These independent, unversioned overlays create combinatorial appearance states, break cross-format identity and make provenance and conformance ambiguous. Data-only CSV/JSON/Parquet or a raw source may properly mark style `NOT_APPLICABLE`; a regulatory fixed template is an external presentation contract, not an excuse for silently combining several brands.

## 2. Stable identity, explicit compilation, no mutable released version

A candidate `ArtifactStyleSet` descriptor contains:
- **identity:** stable namespaced `style_set_id`, semantic `version`, schema version, title, provenance provider identity and immutable revision/content digest;
- **compatibility:** declared artifact kinds/formats, style API version, renderer capabilities, required/optional font resources;
- **foundation and roles:** typography, semantic colors, spacing/borders, document/table/chart roles, number/date display roles;
- **approved variants:** named choices for density, print mode or tone that are resolved under the *same* style identity and version;
- **format projections and bindings:** XLSX/DOCX/PPTX/PDF capabilities, compatible external templates, hashed licensed assets and allowed degradation;
- **strict validation:** aliases, cycles, completeness, safety, media/font availability, allowed execution scope.

The source permits **authoring-time inheritance**: a new candidate can extend a base and override tokens while it is being assembled. Before a Run, that inheritance and all aliases must compile to a fully resolved immutable resource with one digest. The renderer consumes `ResolvedArtifactStyleSet`, never a chain of live base/overlay packages. A published token/style/template change requires new version/digest; changing a display-only title may be metadata revision without altering the resolved visual identity. Historical artifacts require access to their original resolved set or sufficiently preserved rendering/evidence material.

A provider registry lists descriptors and availability, but **provider discovery order cannot select the business default**. The source's conceptual precedence is a managed forced choice, then applicable workspace/user defaults, then a built-in default, subject to explicit Run overrides and current authorization. These are not simple dictionaries merged left to right: forced policy and explicit request may conflict. Resolve a typed tuple containing *requested*, *effective identity and revision*, *source of decision*, *reason*, *provider readiness* and any failures.

A selected style set that disappears must be shown as **unavailable**, not secretly replaced in saved user preferences. A non-interactive authorized policy may provide an explicit fallback, but the fallback must be visible in the receipt; a strict brand requirement may instead block rendering or publication. **The default stance proposed by this source is strict**, especially if an operation produces several formats together.

## 3. Semantic styles preserve financial meaning across formats

Domain code declares document and data roles rather than format-specific fills/fonts:

| Family | Candidate semantic roles | Responsibility |
| --- | --- | --- |
| Document | `document.title`, `heading_1`, `body`, `note`, `source`, `warning` | Hierarchy and source readability |
| Table | `table.header.primary`, `row.total`, `row.subtotal`, `row.forecast`, `column.label` | Consistent structure across reports |
| Chart | `chart.axis`, `series.N`, `actual`, `plan`, `forecast`, `benchmark` | Traceable and distinguishable series mappings |
| Numeric | `number.percent_1`, `integer`, `decimal_2`, `date.quarter`, `missing_value` | Formatting a **domain-declared** unit and precision intent |
| Color | `text.primary`, `surface.subtle`, `data.negative`, `table.total`, `brand.primary` | Semantic emphasis, not facts about a company |

**A style set does not decide** whether a value is RUB billions, a percent change, a forecast, an actual, unavailable, a zero or a restated series. Those are upstream source/analytical facts. A renderer maps explicit domain roles and units to a presentation treatment and records any rounding/degradation. Missingness and units must not be misrepresented by a style's pattern.

One semantic `document.heading_1` can become a named paragraph style in DOCX, a master/layout role in PPTX, a merged header/cell specification in XLSX or a PDF text style. Those are separate adapters **for the same meaning**, not independent user-selectable report styles. The original proposed:
- XLSX: font and color scheme, table/number/chart projections, optional freeze/gridline policies by *layout* role;
- DOCX: named paragraph/character/table styles and optional OOXML theme mechanisms;
- PPTX: text hierarchy, series palette and approved master/template binding;
- PDF: analogous typography/table/chart/metadata, with explicit serialization/feature degradation;
- CSV/JSON/Parquet/raw formats: normally no visual style.

Compatibility must be classified explicitly, e.g. `SUPPORTED`, `DEGRADED`, `NOT_APPLICABLE`, `UNSUPPORTED`. “This style set cannot render PPTX” does **not** authorize use of an unrelated PPTX style set inside the same report execution.

## 4. Templates, fonts, assets and approved variants are bounded resources

An `ArtifactTemplate` governs layout structure, placeholder locations, workbook sheet organization or slide master choice. The style set may declare vetted template bindings but the template identity/version remains separately addressable. Fonts have four separate predicates: **declared**, **available on the execution host**, **legally embeddable**, **actually embedded**. A missing required family can fail readiness; an approved fallback can be used if its exact selection is preserved. The source argues against shipping arbitrary font files just to implement the interface, and against assuming that a document renderer can embed every font.

Style packages can hold hashed assets (logos, theme parts, document assets and templates), with explicit permitted formats, sizes, licenses and traversal protections. A declarative style resource should be **data, not executable code**: no arbitrary Python scripts, template macros, shell hooks, unbounded remote fetches or post-render code. Any real executable renderer extension needs a separately authorized capability and trust boundary.

Approved variants are explicit, named and pinned within a style-set version: compact/standard table density, monochrome print, standard/executive presentation tone *if those do not alter the underlying brand identity*. A radically different font/brand/palette should create another style-set identity. A user-facing arbitrary font/palette picker would defeat the source's atomicity claim. The source therefore recommends replacing earlier ReportProfile-style `overridable_tokens` with **approved variants**, a material refinement of the preceding Settings/Reporting investigations.

## 5. Metadata and provenance remain independent

`ArtifactMetadataContext` carries creator label, document title/subject/keywords, document timestamps and actual artifact/Run/provenance references as appropriate. The editable Office `author` label may default to “Strategy Box”; it is **not** a reliable record of the authenticated initiating actor, execution agent or publication Authority. Immutable provenance should capture actual principal and operation evidence separately from presentation metadata.

Before exporting, the application resolves a sealed `ArtifactStyleContext` with:

```text
style_set_id + exact version + content digest
selected approved variants and format capability
renderer identity/version and relevant library version
resolved tokens, font selection, assets and template refs
requested/effective policy reason and any explicit degradation
separate metadata context/digest
```

The domain operation and export layer receive this context explicitly. A Windows or Android preferences file is not readable business authority. Remote execution resolves the *same identity/digest* on the actual worker and verifies fonts/assets and policy **there**; the client's locally installed catalog does not prove remote readiness. Result bytes then follow the separately owned Artifact staging/commit/publication lifecycle. Style membership alone does not make a file durable, accepted or available to another user.

The original favors a compact `ArtifactDescriptor` pointing to a provenance/manifest record rather than embedding every rendering decision in a broad mutable artifact object. For reproducibility, preserve style digest, renderer version, template identities, any font fallback and format degradations. The same style-set version with a changed writer implementation can produce different bytes; style reference alone is insufficient for byte-level reproduction.

## 6. Current Excel style model: useful base, inadequate general owner

Direct dated code evidence from [Excel style models](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/styles/excel/models.py) includes `FontTheme`, `BlockStyle` and `StyleSpec`, whose optional blocks overlay cell formatting. The [registry](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/styles/excel/registry.py) combines built-in fonts/presets with contributions in sequence: later entries can overwrite keys and supply an alternative default, which can make package discovery change report appearance. The public [adapter](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/styles/excel/main.py) applies a chosen preset to a worksheet; it is a format-specific mechanism.

These are **specific frozen current code observations**, not a declaration that general `ArtifactStyleSet` already exists. The Research proposes retaining the good ideas—style-as-data, reusable immutable pieces, centralized XLSX application and domain/rendering separation—while demoting Excel `StyleSpec` to a format adapter or compiled projection. A future public top-level style registry must not use order-dependent addon overwrites as its selection model.

The absence of a backward compatibility requirement allows a clean semantic API change, while artifact reproducibility, historical output records and safe migration deserve explicit preservation. Neither this paper nor the source authorize immediate code mutation.

## 7. Selection UI, deployment boundaries and future surfaces

A minimal Settings UI would expose only a **single Style set** choice and independent **Author of files** label, alongside Appearance and neutral provider controls. Catalog details may show title, version, source class, supported formats, font and preview, plus a policy reason for managed lock. A deterministic sample-document preview is helpful; it must not use sensitive live bank data or become an arbitrary interactive styling editor.

A style package can be data-only and suitable for a managed deployment. Installing/updating package assets, provisioning fonts or distributing managed policy belongs to the external environment owner. Strategy Box owns style semantics, validation, resolution, renderer and provenance. A provider carrying a resource may be managed in an extension inventory, but the user chooses its **output effect** under Artifacts/Reports. A generic extension can have an optional resource contribution; this does not create automatic priority or arbitrary shell control.

Windows, a future Android client, authorized automation and AI/machine initiators should consume a uniform style reference and current grant, not duplicate the rendering implementation on each device. An AI actor may select from authorized, validated styles but does not receive authority to import an arbitrary style resource or change persistent defaults merely by asking.

An external prescribed regulatory format may require an operation-level `external_fixed` presentation contract. In that situation style is constrained to permitted zones or marked not applicable; regulator-mandated table structure and units are not user brand preferences.

## 8. Validation, negative cases and adoption gates

The 2026-10-07 research defines a 22-condition proposed acceptance checklist (§72) and detailed resolver/compile/cross-format/strictness/provenance tests (§71). Candidate checks cover identity/version/digest, complete alias resolution and no cycles, template/font/asset read permissions, path traversal, legal embedding, color/text contrast, chart-series distinguishability, renderer capabilities and deterministic degradation.

Meaningful adversarial cases:
- Two style providers declare a colliding ID; reject ambiguity instead of picking a discovery winner.
- The selected style is missing on the remote host; do not produce an unbranded output and report it as the selected profile.
- An XLSX writer supports a token that PPTX cannot; return a typed degradation or preflight failure under the same style identity.
- An alias cycle, mutable base package, missing hashed template or unlicensed font blocks compilation/readiness.
- A new provider package is installed; existing selected defaults and completed artifact presentation cannot silently change.
- Managed policy prohibits a fallback; a style mismatch must fail before publishing an incorrectly branded artifact.
- Human-readable Office creator differs from actual authenticated Run executor; provenance remains truthful.
- A PDF/CSV adapter cannot express an expected style role; the output declares degradation/not-applicability rather than inventing a second style.
- A new domain exporter hardcodes its own company color, defeating uniform output; the renderer/domain boundary test fails.
- A custom presentation resource contains an executable macro, external command or unbounded remote dependency; the trusted validator denies it.

A future conformance suite should render and inspect bounded sample XLSX/DOCX/PPTX/PDF outputs, validate named table/chart/document roles and fonts, record renderer/library versions, assert stable source digests and check that no undeclared fallback occurs. Golden artifacts can be examined structurally where pixel equivalence is not a valid cross-platform guarantee. **No such installed cross-format suite has been run in this study.**

**Reopen on:** an accepted artifact style schema, actual writer capability, a supplied asset/license policy, multi-format renderer output, new style-provider constraints, explicit managed brand commitments, real Android/host consumers, or contradictory evidence from financial regulatory templates.

**Related scientific owners:** [report-profile and creator reasoning](report-formatting-profiles-metadata-and-evidence.md), [artifact publication and identity](output-identity-publication-and-availability.md), [Settings default semantics](../application-state/settings-policy-preferences-and-drafts.md), [declarative provider configuration](../extensions/configuration-catalog-readiness-and-surface-boundaries.md), [data unit and missingness truth](../data-and-knowledge/observation-semantics-comparability-and-claims.md).

## 9. Original twenty-two proposed cross-format style admission checks

The frozen [2026-10-07 ArtifactStyleSet Research, §72](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2318-L2343) lists **twenty-two acceptance candidates**. They are retained below as individual English source-row interpretations with stable original identifiers, **not** as accepted requirements, validated style packages, installed writer support or executed tests. The original research argues for a compiled **single effective style-set identity** for cross-format meaning; runtime merging of independently versioned sets creates ambiguous provenance and difficult testability. Standalone bundles and neutral extension contribution are possibilities, not descriptions of any private implementation.

| Original item | English research candidate and limitation | Frozen source row |
| --- | --- | --- |
| `SB-SRC-0042/A01` | Keep the contributing extension, immutable ArtifactStyleSet and independent InterfaceTheme as different concepts. | [L2322](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2322) |
| `SB-SRC-0042/A02` | Permit a valid ArtifactStyleSet to be installed, chosen and used without an extension package. | [L2323](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2323) |
| `SB-SRC-0042/A03` | Allow an authorized extension to offer a StyleSet through a neutral shared provider/validation contract. | [L2324](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2324) |
| `SB-SRC-0042/A04` | Use one effective, explicitly selected and resolved ArtifactStyleSet for one execution context. | [L2325](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2325) |
| `SB-SRC-0042/A05` | Do not merge typography/colors from unrelated StyleSets dynamically during rendering. | [L2326](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2326) |
| `SB-SRC-0042/A06` | Allow authoring-time inheritance only after compilation to a complete closed semantic specification. | [L2327](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2327) |
| `SB-SRC-0042/A07` | Carry stable StyleSet ID, version and digest, separate from renderer version. | [L2328](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2328) |
| `SB-SRC-0042/A08` | Apply one specified primary font across supported output formats when actually available. | [L2329](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2329) |
| `SB-SRC-0042/A09` | Map the same semantic color roles across formats without assuming identical pixel rendering. | [L2330](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2330) |
| `SB-SRC-0042/A10` | Treat XLSX, DOCX, PPTX and PDF as format adapters consuming a shared semantic style model. | [L2331](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2331) |
| `SB-SRC-0042/A11` | Enumerate, version and test approved variants rather than allowing arbitrary runtime overrides. | [L2332](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2332) |
| `SB-SRC-0042/A12` | Keep arbitrary font and color override outside the default user flow; advanced controlled design may be separate. | [L2333](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2333) |
| `SB-SRC-0042/A13` | Treat ArtifactTemplate as a separately versioned asset which can be explicitly bound to a StyleSet. | [L2334](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2334) |
| `SB-SRC-0042/A14` | Keep file metadata (author, creation identity and source evidence) conceptually distinct from visual styling. | [L2335](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2335) |
| `SB-SRC-0042/A15` | Do not infer an artifact report StyleSet from the application's current light/dark InterfaceTheme. | [L2336](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2336) |
| `SB-SRC-0042/A16` | Do not let a contributed style package silently mutate the application shell's visual system. | [L2337](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2337) |
| `SB-SRC-0042/A17` | Treat the absence of the selected StyleSet as an explicit unavailable/problem outcome, not silent substitution. | [L2338](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2338) |
| `SB-SRC-0042/A18` | If an output format is unsupported, report that limitation instead of fetching another StyleSet's adapter. | [L2339](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2339) |
| `SB-SRC-0042/A19` | Record the resolved StyleSet identity/digest in artifact provenance if the feature is implemented. | [L2340](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2340) |
| `SB-SRC-0042/A20` | Do not treat the current Excel-only presets as a proven universal cross-format style API. | [L2341](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2341) |
| `SB-SRC-0042/A21` | Subject-matter exporters should avoid hard-coded fonts/colors when a declared format/style contract is in use. | [L2342](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2342) |
| `SB-SRC-0042/A22` | Portable clients and machine consumers should exchange one declared semantic style reference, with native rendering separate. | [L2343](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md#L2343) |

**Challenge:** a small CSV-only export does not require the complete multi-format authoring infrastructure, fonts may be unavailable on Android/headless host, and metadata author labels are not provenance principals. A sound formatter must declare unsupported formats and degraded font fallback when it occurs rather than claim full output consistency. No Product Authority decision about mandatory StyleSet, renderer or writer registry is inferred from this historical research list. **Twenty-two discrete rows were preserved; the remainder of the 2,447-line source has not been independently certified lossless.**
