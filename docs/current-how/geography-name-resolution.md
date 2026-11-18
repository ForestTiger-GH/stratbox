# Territory name normalization and scope-aware identity matching

**Current implementation scope:** Stratbox offers a pure text key normalizer and a reviewed, manifest-pinned reference resolver. The starter edition is deliberately partial; source-specific geographic structure and statistical boundaries stay with individual domain parsers.

## Navigation

1. Two semantic layers — lexical name versus reviewed subject.
2. Context and statuses — admission of a candidate identity.
3. Reference rules — exact identity assertions and source scope.
4. Negative boundaries — impossible or unjustified implicit merges.
5. Domain pilots — observing names while preserving data meaning.

## 1. Lexical key and identity

```python
from stratbox.shared.reference.geography import (
    RegionNameResolver, RegionNameContext, normalize_region_label,
)

key = normalize_region_label("  г. Москва  ")
match = RegionNameResolver().resolve("город Москва")
assert match.subject.id == "RU-MOW"
```

`normalize_region_label` Unicode-normalizes case, spacing and dash spelling, optionally folds `ё` to `е`, and leaves qualifiers such as `без данных по ...` intact. It does not guess a territory or remove its administrative category. `RegionNameResolver` only considers explicitly declared name rules from a selected edition.

## 2. Context and statuses

| Code | Status | Interpretation |
| --- | --- | --- |
| GEO-EX | `exact` | A verified label equals the displayed canonical name under the admitted context. |
| GEO-AL | `alias` | A verified alternative name identifies the same admitted subject. |
| GEO-UN | `unmatched` | There is no declared admissible label identity. |
| GEO-AM | `ambiguous` | Multiple distinguishable identities match; no identity is chosen. |
| GEO-OS | `out_of_scope` | The label exists but is excluded by code, time, source, kind or perimeter context. |

The result preserves the caller's original name, normalized key, status, explicit namespace and subject ID only when proven, optional statistical perimeter, edition identifier, matching rule ID and ambiguity candidates. A `RegionNameContext` may specify `source_family`, date, `observed_kind`, and a verified `source_code` + `code_namespace` pair. A name and code that disagree are rejected, not silently reconciled.

## 3. Reviewed reference assertions

`_resources/aliases.csv` declares a stable rule ID, alias text, displayed canonical name, namespaced subject identity, kind, optional perimeter and source scope, optional validity dates and review basis. ISO-3166 and published territorial identifiers can be used only for confirmed mappings. Unknown code crosswalks remain unknown. The edition identity is a deterministic version of the declared reference assets; there is no fuzzy last-resort assignment.

## 4. Negative boundaries

The name `Москва` is not interchangeable with `Московская область`; `Республика Алтай` is distinct from `Алтайский край`. `Алтай` alone remains unmatched rather than selecting an arbitrary one. A named autonomous district and its parent region are distinct entities, even if a statistical publication uses inclusive totals. The phrases `Тюменская область` and `Тюменская область без данных по автономным округам` are not the same key. An inclusion/exclusion claim requires an additional published, domain-specific perimeter contract; the name matcher cannot create that fact.

## 5. Domain pilots

The FNS SME parser offers `inspect_region_names(rows)`; it preserves FNS `ssrf` identifiers and produces read-only `RegionNameMatch` diagnostics. Escrow provides `inspect_escrow_region_names(rows)`, retaining row objects and their hierarchy. CBR 01_05_A source names reuse the shared Unicode normalization key, while preserving 96 independent row IDs and its own accepted aliases. The FNS 1-YUR and CBR regional offices parsers expose read-only `inspect_fns_1yur_region_names(names)` and `inspect_offices_reg_region_names(names)`. All source-specific sorting, aggregates, literal CSV representations, period rules and economic facts remain unchanged.


## 6. Qualified rulesets and fail-closed context

A source-specific alias requires a matching `RegionNameContext.source_family`.
A perimeter-specific rule requires the matching `perimeter_hint`. A
date-bound rule requires an `as_of` date within its declared validity; a
verified code requires an explicitly declared code namespace. Missing context
does not broaden a restricted rule into a universal one.

Both packaged and explicitly supplied `RegionNameRule` sequences pass the
same validator, including `review_basis`, stable rule IDs, supported kinds
and valid dates. Supplied rules cannot claim a packaged edition name. They
receive a deterministic content-derived ID independent of input sequence
ordering.

A `RegionNameMatch` exposes `ruleset_identity`, `provenance`
(`packaged` or `supplied`), and—only when bundled—a logical reference ID
and the edition snapshot identity. This is an identity claim for the used
rule set, not proof that its assertions are substantively correct.

Name lookup is indexed by the lexical key; contextual admission still
happens against every candidate. The deliberately small starter corpus
contains 15 reviewed rows. Domain-local statistical perimeters and
territorial inclusion/exclusion remain separate from this general resolver.
