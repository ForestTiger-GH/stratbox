# Reconciliation of early reporting profiles with the later atomic style-set proposal

**Theme question:** What is one authoritative style-selection concept for generated bank/macroeconomic reports across formats, and which previously suggested configuration options remain legitimate after a later Research refinement? **State:** bounded source reconciliation of *proposals*, with Product authority and installed conformance OPEN.

## Exact primary evidence

| Research original | Source identity / frozen blob | Significant original locators and position |
| --- | --- | --- |
| Settings/Preferences | `SB-SRC-0044` / `bedb3628f3a58a27c9de10b7a19043549c281dca` | §§13–19 (L686–943), §§35–43 (L1325–1557), §§77–79 (L2310–2364): a selected versioned `ReportProfile`, provider-contributed fonts/palettes and optionally `overridable_tokens`, requested/resolved recorded |
| Artifact customization and styles | `SB-SRC-0042` / `0ff9a0ac61be5d128cd1669a411017040ae8b7e5` | §§0–7 (L11–430), §§12–19 (L627–901), §§25–29 (L1030–1193), §§56–68 (L1827–2191), §§71–72 (L2270–2346): single complete `ArtifactStyleSet`, compiled authoring-time inheritance, approved variants, strict format capability, independent metadata, no runtime mixing |
| Direct existing core implementation | `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580` | `src/stratbox/base/styles/excel/{models.py,registry.py,main.py}`: Excel-local `FontTheme`/`BlockStyle`/`StyleSpec`, built-in + order-applied external addon contributions, last writer of preset/default may win; not a general multi-format set |

Both Research studies are from **2026-10-07**, share the same project and Excel/Windows baseline, and their similarity is not independent evidence. The second study explicitly declares its own §§66–67 a *revision* of earlier generic extension and Settings conclusions. Reading order alone does not create Authority; the substance and explicit source statement support an identifiable lineage.

## Substantive differences and selected scientific interpretation

| Concern | Earlier settings study | Later customization study | Knowledge disposition |
| --- | --- | --- | --- |
| Name | `ReportProfile`, sometimes `report_profile_id` | `ArtifactStyleSet`, explicit style set reference/compiled resource | **Research revision**. Preferred candidate is one cross-format neutral identity; both original vocabularies stay in history. |
| Runtime composition | Profile can expose selected overridable font and accent tokens | Exactly **one** fully resolved set. Authoring-time extension permitted, runtime arbitrary mixing forbidden. | **Meaningful competing design**. Default scientific safety model keeps atomicity and bounded approved variants; exact implementation remains a Product/architecture choice. |
| Provider identity | Profile may be attached to an enabled extension | Set is passive, can come from built-in, standalone data package, managed owner or extension | **Refinement**. Package/container is not the visual style's semantic owner. |
| Unavailable provider/profile | Earlier source allowed visible fallback to a standard profile when safe | Later source defaults to strict unresolved/fail-closed behavior, except expressly authorized logged fallback | **Actual tension**. Preserve preference/actual effective split in either case; do not silently switch style identities. Release policy and caller authority must select strictness. |
| User author label | Independent preferred global author label | `ArtifactMetadataContext` separate from style, templates and actor provenance | **Convergence**, with stronger lifecycle separation; no accepted metadata writer behavior inferred. |
| Multiple output formats | Reporting profile can condition formatting of XLSX/PPTX/DOCX | Single set with explicit semantic roles, renderer capabilities and degradations | **Stronger candidate**; unsupported format is not a license to silently select second set. |
| Existing Excel layer | Current format-specific styles are useful source mechanism | Demote `StyleSpec` to adapter, remove order-dependent public addon merge | **Target proposal against directly observed dated code**, not implemented migration. |
| Provenance | Snapshot profile id/version and creator value | Style ref/version/digest, renderer, font/template/variants, fallback and degradation receipts | **Refinement**. Reproduction requires more than user profile ID. |
| Regulatory fixed-format | Mostly described as artifact/report styling default | Fixed externally prescribed presentation contract is distinct, with style limited or NOT_APPLICABLE | **Qualification** material to statistical/regulatory compliance. |

The maintained Science owner for strict core style semantics is `docs/science/artifacts/atomic-style-set-cross-format-resolution-and-conformance.md`. Earlier `docs/science/artifacts/report-formatting-profiles-metadata-and-evidence.md` now contains an explicit lineage note and keeps earlier candidate detail. Do not treat both papers as two concurrently authorized contracts. General extension configuration remains separately owned by `docs/science/extensions/configuration-catalog-readiness-and-surface-boundaries.md`.

## Dispositioned evidence roles and open questions

- **Current-code observed (bounded):** Excel presets/addons are format-first and can be assembled/order-applied at frozen baseline; no general, validated, immutable `ArtifactStyleSet` runtime was observed or tested.
- **Research-supported design concerns:** deterministic style identity, one accountable effective selection, cross-format semantic roles, user/system separation, secure passive resources, honest font fallback and actual provenance.
- **Research alternatives retained:** ad hoc profile tokens, permissive font/color overrides, cross-set font/palette mixing and strict-versus-permitted fallback. Earlier user controls are preserved as historical arguments, not shipped requirements.
- **Explicit UNKNOWN:** exact accepted style schema/API, whether one set must govern all artifacts of a multi-operation Work rather than one Run, approved regulatory exceptions, font licensing and physical renderer constraints, platform resource policy and scope of authorized noninteractive fallback.
- **External standards:** DTCG token and OOXML Theme references occur in the original study; they are not asserted here as independently verified for 2026 or as a specific production framework.
- **Required conformance evidence:** compile aliases/inheritance; no cycles; validate assets/license/font availability; render inspected XLSX/DOCX/PPTX/PDF with semantic roles, no invented style on CSV, no silent fallback; persist exact digest/version, renderer and resource receipts; prove that provider installation does not mutate past output/defaults.
- **Reopen:** real product admission of style identity and policy, consumer requirement for overrides, tested writer incompatibility, binding of brand/regulated templates, or direct installed current code change.

**Bounded verdict:** `RESEARCH_LINEAGE_IDENTIFIED_STRICT_ATOMICITY_CANDIDATE_PRODUCT_AUTHORITY_OPEN`. This is a source reconciliation, **not** independent knowledge verification or globally certified lossless preservation.
