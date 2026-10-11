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

## Original format research: twenty proposed technical and security decisions

The [2026-10-07 original Format/FileStore study, §54](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2542-L2563), blob `b54bfcefd0784a5c45366cd8382364193223577d`, proposes twenty specific format actions. All entries below are **source-line-addressed English research interpretations**, not accepted codec guarantees, installed library capabilities or approved release commitments.

| Source item | Proposed meaning and falsifiable boundary | Original source |
| --- | --- | --- |
| `SB-SRC-0028/FORMAT-01` | FileStore remains format-agnostic bytes/path/stream infrastructure | [L2544](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2544) |
| `SB-SRC-0028/FORMAT-02` | One shared FormatRegistry may describe technical format capability across clients | [L2545](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2545) |
| `SB-SRC-0028/FORMAT-03` | Desktop and future Android should avoid divergent proprietary extension maps | [L2546](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2546) |
| `SB-SRC-0028/FORMAT-04` | Unknown format is an ordinary qualified state, not always an error | [L2547](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2547) |
| `SB-SRC-0028/FORMAT-05` | Each domain Operation declares accepted content/format semantics | [L2548](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2548) |
| `SB-SRC-0028/FORMAT-06` | Unrecognized Excel-like extension must not silently be parsed as XLSX | [L2549](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2549) |
| `SB-SRC-0028/FORMAT-07` | Remove claims of generic XLS/XLSM/DBF writing where no reliable backend exists | [L2550](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2550) |
| `SB-SRC-0028/FORMAT-08` | Prefer ZIP as initially supported canonical multi-file output, subject to consumer demand | [L2551](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2551) |
| `SB-SRC-0028/FORMAT-09` | Archive extraction must plan, validate entries and stream with resource limits | [L2552](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2552) |
| `SB-SRC-0028/FORMAT-10` | XBRL and SDMX are semantic domain/standard families, not merely file suffixes | [L2553](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2553) |
| `SB-SRC-0028/FORMAT-11` | Consider Arelle for XBRL backend after scope/performance/security qualification | [L2554](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2554) |
| `SB-SRC-0028/FORMAT-12` | Consider ODS due to potential Linux and alternative office suite users | [L2555](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2555) |
| `SB-SRC-0028/FORMAT-13` | Consider Parquet as reusable machine-oriented columnar format | [L2556](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2556) |
| `SB-SRC-0028/FORMAT-14` | Make CSV/DBF character encodings explicit and reconstructible | [L2557](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2557) |
| `SB-SRC-0028/FORMAT-15` | Do not execute dynamic pip installation as a routine product runtime behavior | [L2558](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2558) |
| `SB-SRC-0028/FORMAT-16` | Never execute embedded macros as a side effect of document inspection | [L2559](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2559) |
| `SB-SRC-0028/FORMAT-17` | Distinguish protected input with a PASSWORD_REQUIRED outcome | [L2560](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2560) |
| `SB-SRC-0028/FORMAT-18` | Check content type, extension and byte signatures before parser admission | [L2561](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2561) |
| `SB-SRC-0028/FORMAT-19` | Preserve original used source bytes/identity separately from transformed canonical data when material | [L2562](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2562) |
| `SB-SRC-0028/FORMAT-20` | Carry qualified format detection and codec/semantic version into material provenance/artifact evidence | [L2563](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md#L2563) |

**Competing priorities and limits:** a single FormatRegistry can centralize detection without requiring every individual file parser to be moved out of domain owners. XLS, XLSM, ODS, Parquet, XBRL and SDMX support entail distinct read/write maturity, dependencies and sandbox/security costs. A user request for future Linux/R7 compatibility supports investigating ODS but not claiming ODS is already writable. Macros and password-protected content are separate threat/failure classes; a parser's ability to inspect bytes is not proof safe execution or correct banking meaning. 'ZIP only' and 'Arelle preferred' are research-origin technical choices that still require real consumer profiles and performance/security trials.

**User proportionality:** a file may simply be unavailable after manual movement or deletion, and the domain core must remain reusable directly in Python. Heavy global format services or background codec installation cannot be presumed required for this scoped goal. Source byte retention and provenance depend on actual material reliance and permitted storage lifecycle, not on format suffix alone. This twenty-point register is a subset of the 2,700-line original and remains under independent semantic challenge.
