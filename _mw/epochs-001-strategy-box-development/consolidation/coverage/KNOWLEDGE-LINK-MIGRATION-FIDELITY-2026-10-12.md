# Exact Git-to-Git source-link migration fidelity

**Scope:** evaluate whether two completed 2026-10-12 detachment batches preserved the *already published Knowledge text* while removing navigational dependence on Research and Work. This is not an original Research semantic audit.

The [automatic history checker](../tools/test_knowledge_link_migration_fidelity.py) compares exact frozen public Git transitions: `7deed98376092c1002090a5b5361de7ae6290f9f` → `9008b1388da2317dc69537bbcacd7ac9f93ed043` (1,962 historical links removed from 52 Markdown documents) and `f238e38879121edc28de9541aaa46c821952c032` → `ae02bbeb2895dcba94bb99dec607e5fe89759572` (non-hyperlinked source-position formatting normalized in 41 documents). The check applies each exact transformation to each prior Git blob and byte-compares against the committed successor blob. It neither needs the historical Research originals nor silently assumes all prior content was correct.

**Supported verdict if green:** the two bulk migrations changed only the intended link/formatted-marker syntax. It does **not** establish original→Science conservation, correct interpretation, an independent reviewer, live host behavior or Product approval. The separate docs-only isolation test measures removal readiness; the permanent URL-lint test forbids reintroducing Research backlinks. The original DOCX is owner-declared LOST and remains excluded from verifiable-original claims.

Research Amputation and genuinely independent reverse source/claim verification of all accessible Research **remain OPEN**.
