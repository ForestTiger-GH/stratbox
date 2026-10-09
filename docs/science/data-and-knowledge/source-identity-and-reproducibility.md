# Source identity, registry identity, and reproducible statistical inputs

**Scope:** bounded scientific and engineering explanation of a recurring provenance problem in financial-statistical data processing. **Evidence:** exact core implementation at `8459dc58922b7e8df853cf1d9e8131fa9e132580`, source semantics and formal examples. This article does **not** announce a deployed universal Source Catalog or registry manifest.

## Three objects that must not be conflated

A **reference entity** is what an external classification or institution defines: a bank, economic-activity code, or geographical entity. A **source definition** describes *how to retrieve* data: an endpoint, publication family, or collection rule. A **source snapshot** denotes *what was actually retrieved*: observed bytes, source context, time, validation and a content identity. They have different change conditions.

A bank can retain its registration identity while changing its displayed name. An official statistics URL can remain identical while the publisher replaces the XLSX bytes. A new downloaded filename can also represent the exact same bytes. These examples show why a display label, URL, local path or modification timestamp is insufficient by itself to express content revision.

**Reproducible result** means a consumer can identify the relevant inputs, transformations, assumptions and versions under a declared preservation boundary. It does not mean that a URL will always serve its former payload or that all past bytes remain available without a retention arrangement.

## Direct implementation: a selector whose identity is weaker than the data

The current registry resource loader provides `pick_latest_by_suffix()` and `pick_latest_by_prefix()`, both using `_resource_mtime()` to select the maximum filesystem `stat().st_mtime`. If stat fails, the helper substitutes `0.0`. [Direct code](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/_loader.py).

This reliably states how the *current selector* operates. It does not establish which specific file is chosen in every deployed environment. A copied tree or repackaged installed resource may acquire new filesystem times without a corresponding change to its substantive publication. Consequently, “latest by mtime” is not by itself proof of “most recently published by the authority.”

The current [bank registry implementation](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/cbr_banks.py) reads several resource families: official bank information, name-replacement policy, selected list and legacy list. These need distinct provenance roles even if one convenience reader joins them. The [classifier loader](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/rosstat_okved2.py) reads separate classifier resource forms. A mixed bundle cannot be assumed to represent one consistent source revision merely because its files share a directory.

## The content-identity argument

Let two source downloads have the same filename and URL but different byte strings, `b1` and `b2`. If only URL and filename are recorded, they are observationally indistinguishable to a later consumer. If cryptographic digests differ, that consumer at least has evidence that the bytes differed; a digest alone does not prove which publication was authoritative, correct, timely or permitted.

An identity/provenance record therefore has several independent dimensions:

| Dimension | Explains | Does not automatically establish |
| --- | --- | --- |
| Authority and source definition | Who/where the data purportedly came from | Actual content, official validity |
| Retrieved byte digest and size | Which bytes were observed | Semantic correctness, long-term retention |
| Publication/effective period | Which statistical period/meaning applies | Download date or file freshness |
| Registry/classifier version | Which mappings were used | That all transformations were sound |
| Transformation and code version | How a result was constructed | User acceptance of its conclusions |
| Validation state and assumptions | Which checks/qualifications hold | Absence of other unknown defects |

For composite resources, one bundle may contain several files representing different roles. They should be verified together against their declared source/profile rather than independently sorted by mtime and silently mixed.

## Alternatives, limitations, and negative results

- **Filesystem mtime as currentness:** simple and useful for ad hoc local files, but insufficient as an immutable authoritative revision selector.
- **Filename/URL:** useful stable source locators, but may be reused by publishers for changed content.
- **ETag or Last-Modified:** helpful hints when available; the transport server controls their presence and semantics, so they should not be silently equated with a universal byte digest.
- **Immutable manifest plus digest:** a plausible controlled package contract, but it is a **target design option**, not something the current loader implements. It requires explicit source, validation, package/update and failure rules.
- **Keep every snapshot forever:** helps historical replay, but increases storage and governance costs. A bounded retention/version-pinning policy is a separate product decision.

**Current unknowns:** latest authoritative external-bank and classifier publication revisions have not been rechecked in this article; actual installed-resource selection and historical retention are unmeasured; no package or user acceptance claim follows. Reopen when loader logic, source publisher behavior, resource packaging or required reproducibility changes.

This article supports a reader's understanding of source truth without depending on prior Research reports. It does not set an approved catalog schema, registry update workflow or runtime permission model.
