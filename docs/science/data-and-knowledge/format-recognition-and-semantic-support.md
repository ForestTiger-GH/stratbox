# File format recognition is not analytical format support

**Scope:** engineering-scientific distinction between bytes, file identification, technical decoding/encoding and correct domain interpretation in Strategy Box. **Baseline:** direct static source at `8459dc58922b7e8df853cf1d9e8131fa9e132580`. **Not a catalog of formats certified for production.**

## Five distinct capabilities

| Level | Meaning | A counterexample to overclaiming |
| --- | --- | --- |
| L0 — Opaque transport | Store, copy, stream or hash uninterpreted bytes | Copying an XBRL ZIP says nothing about understanding taxonomy |
| L1 — Identification | Recognize a likely extension, signature, media type or container | A server returns an HTML login page named `report.xlsx` |
| L2 — Technical decoding | Read a supported syntactic structure | Parsing XML does not resolve an XBRL reporting taxonomy |
| L3 — Technical encoding | Safely write a corresponding representation | Reading XLSB does not imply writing XLSB |
| L4 — Domain semantics | Validate and interpret the source's meaningful banking/statistical schema | A decoded spreadsheet may use unexpected units, period, region or revision |

These levels form an explanatory model rather than a single universally ascending feature flag: a domain operation may inspect bytes with a specialized parser, and one installation may lack an optional codec even when the source module declares it.

## Implementation-based counterexamples

The [XLSB module](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/ioapi/excel_xlsb.py) implements `read_df` through a lazily resolved optional engine and explicitly raises `NotImplementedError` for `write_df`. This provides positive evidence for a conditional read path and direct negative evidence against generic XLSB write support; it does not prove that the optional dependency is installed.

The [DOCX module](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/ioapi/docx.py) extracts text from paragraphs and creates simple documents from paragraph strings. It does not claim to preserve all tables, headers, footnotes, references, shapes or document semantics. A text-only read is therefore weaker than validated extraction of a financial report.

The [ZIP module](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/ioapi/zip.py) has `extract_to_memory` that reads the archive bytes into memory and returns member bytes. This is a real code path, not proof of bounded-memory streaming, constrained decompression or a general secure archive extraction service. A program that can list an archive's members is also not necessarily safe to extract every member onto a writable filesystem.

## Why detection cannot rely on the filename alone

A name such as `report.xlsx` is a user- or server-controlled claim. Independent clues include response headers, file signatures, container structure and internal manifests. Contradictions between clues should remain visible: HTML returned for an expected data file can represent an upstream failure, not a valid empty spreadsheet.

Similarly, a physical file encoding is separate from the domain-specific semantic schema. XML/JSON/ZIP are containers or syntactic representations; XBRL and SDMX introduce their own facts, dimensions, schema structures, taxonomies or dataflows. A generic XML parser is not a complete XBRL processor, and a CSV reader is not a complete SDMX-data interpretation.

## Errors, resource boundaries and safe interpretation

Typical distinct outcomes include `UnsupportedFormat`, `FormatMismatch`, `PasswordRequired`, `CorruptFile`, `MissingCodec`, `SchemaMismatch`, and `SourceUnavailable`. These names are **illustrative taxonomy**, not currently accepted or universally implemented exception types.

A robust specification must distinguish a readable but semantically invalid dataset from an unreadable file, missing optional codec, encrypted office document, extraction budget exceeded or potentially active embedded content. Decoder fallback that silently replaces unrecognized characters can alter bank names, numbers and classification labels; it requires a source-specific policy and observable qualification.

Large archives and spreadsheets may require file-backed streaming and explicit resource budgets. Current static bytes-in-memory implementations cannot justify an assurance claim for arbitrarily large files. Likewise, availability of an API entry point does not certify its operating-system dependencies or optional package installation.

## Valid alternatives and scope limits

**Broad read / narrow write** is one possible product policy: accept legacy/reporting formats as inputs while publishing in a smaller set of dependable representations. Its exact allowed set requires explicit demand, maintained codecs and tests. Full round-trip editing of macro-enabled spreadsheets, interpreted PDF tables, encrypted documents, and writing legacy binary formats carry different failure and security costs.

A central typed format catalog may reduce drift among core codecs, desktop file explorer, artifact metadata and future surfaces. Yet such a catalog is a **target proposal**; no installed universal FormatRegistry is asserted here. Platform-specific UI previews can retain local constraints even when a shared conceptual file identity exists.

**Reopen on:** source-code or dependency changes, verified installation tests, newly supported regulatory standard versions, cross-platform consumer needs, archive security evidence or an authorized product-format policy. Direct file evidence demonstrates only the named behavior; no `pytest` or end-to-end parser certification was performed.
