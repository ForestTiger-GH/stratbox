# Publication integrity recheck — 2026-10-09

**Fixed target:** `stratbox@f2e2a5fb6ec2fdcc372ff104e5e95eb38145f351`; exact inspected tree `5be8eeed08abd7bc8f4d0147af21ae917d9b3586`. **Checks performed by:** assembling actor (no independent review). Read-only verification: no code/test execution.

| Check | Method and observed result | Verdict / limits |
| --- | --- | --- |
| Published docs tree | Recursive tracked Git tree, `docs/**/*.md` | **27 Markdown files**; six maintained semantic role groups plus manifest/navigation |
| Markdown local links | Inspected all 27 doc contents in two batches; parsed `[text](url)` links; normalized relative paths against tracked tree | **54** detected Markdown links; **38** local links; **0** missing local blob paths; regex check, not semantic anchor/URL liveness test |
| Method-specific and restricted tokens in `docs/` | Case-insensitive scan for project-specific method names and selected restricted-package, infrastructure, hostname markers across all 27 docs | **0** matches; these keywords are a limited pattern set, not semantic penetration/security review |
| Legacy documentation text | Read all **19** `docs_old/*.md` historical files; scan targeted restricted implementation/infrastructure tokens | **0** selected-token matches; older files retained byte-identically and not fully semantically/security-reviewed |
| Change scope | Git compare original starting core `5cff9157460c2035aa42758b505cce65b7c53f47` vs inspected HEAD | **8 commits, 39 changed paths (29 added, 10 modified, 0 removed)**, **0** files outside `README.md`, `docs/` and consolidation Work area |
| Runtime/test changes | Same diff tree path inspection | **0** `src/`, `tests/`, `scripts/`, `docs_old/` changes |
| Source registry stability | Original 553 census pinned and unchanged; exact Git tree SHA matching checked separately | **553 stable records**, file-level PASS; complete material-unit accounting remains OPEN |
| Original research fidelity | No changes to `_mw/.../research/` in examined diff | PASS for unchanged tracked research paths; no re-serialization performed |
| Role/status labelling | Read README, manifest, Target WHAT/HOW, architecture, LDD sample | Partial/conditional/observed status visible; no blanket admission or global lossless claim |
| Public release safety | Pattern scan + selected text review, no second reviewer, no whole-repo secret scanner or historic git audit | **CONDITIONAL only**; no full public safety certification |

## Producer-only cold reading

From the bounded Science module, a cold competent reader can derive why a reported `6` has a latent rounding interval and find direct implementation evidence. From bounded Current HOW, a reader can locate the manifest-v4 vs smoke-v3 difference and the absence of scheduler logic in a particular background status store. Full Strategy Box source-to-knowledge research elimination **fails**: most of the 553 original source records still lack material-unit disposition.

## Reopen and closure implications

Publication/navigation/in-scope-change checks provide a narrow **producer PASS** on the fixed revision, subject to repeating link scan if filenames change. Product-content independent assurance is blocked; full Knowledge Product closure fails on semantic conservation and authorization. New security evidence, repository history findings, Research material, Product Decisions, implementation changes, or source revisions reopen only affected checks.

**No claims made:** successful pytest/GUI runs, real external API access, full Git-history scan, exhaustive restricted-data review, cross-role independent verification, full semantic extraction or lossless completion.
