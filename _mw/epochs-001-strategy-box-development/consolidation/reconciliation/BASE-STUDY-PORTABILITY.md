# Portable analytical segments and reusable building blocks — bounded Research extraction

**Original:** `SB-SRC-0023`, fully read L1–L3343, pinned blob `176f9d644f401ad499de80a573318159393a4983`, original commit `8459dc58922b7e8df853cf1d9e8131fa9e132580`. This Work ledger includes 43 provisional source-positioned semantic units, with safe exclusions for publication-sensitive spans. **No original source is changed.**

## Main model and temporal qualifications

The research differentiates small public Python building blocks, generic technical services, domain services, canonical subject operations and client workflows. A stable callable may serve plain Python, notebooks and managed application adapters without reproducing its calculation in each client. **Uniform external contract does not imply uniform internal domain structure:** file collection, spreadsheet history construction and mathematical inference legitimately have different results and evidence requirements.

**Direct pinned code crosschecks:**
- `src/stratbox/base/ioapi/dbf.py` (blob `a08b3df392ba662d7d1e5b45dfed59d03bce0b93`) currently defines DataFrame `read_df` with an optional decoder and a `write_df` path. This is analysis-oriented convenience; it does not prove source-faithful lexical conversion.
- `src/stratbox/base/ioapi/rar.py` (blob `2660800655031f76d1ed452ca94f0d6527c4eb7b`) exposes archive listing/memory extraction options with an `auto_install` argument; dependency provisioning belongs to another boundary in the proposed model.
- `src/stratbox/macrobanks/escrow/operations.py` (blob `c8427310fa235146954ff3e24b63f8d24dcb1f0b`) exposes separate discover/build/views/export functions.
- `src/stratbox/macrobanks/cbr_forms/api.py` (blob `392cca41ce2124e7aef7101d6f7aa65fb56a248b`) exposes the aggregate workbook-export call; full internal source/parse/export architecture needs separate verification.

## Distinct semantic commitments still under Research

1. **Analytical DBF versus source-faithful DBF:** Coercing numeric values into Python types is appropriate for analysis but not necessarily for preserving original lexical values; deleted records, Memo sidecars, source encoding and record boundaries matter for reproducible transcription. A referenced notebook contains a richer prototype, but it has not been directly executed here. A new transcoder API is only a candidate.
2. **Notebook-as-consumer rather than canonical implementation:** direct code reuse avoids copy/paste divergence. A notebook may select inputs, display outputs and download local artifacts while referring to a separately released library. This is proposed policy, not proof all environments already work.
3. **Format registry versus operation registry:** codecs are about physical representations; a domain operation is a user/business use case. Making every helper a product operation would inflate the catalog.
4. **Python-native result versus serializable product result:** DataFrame in memory and artifact/content reference in managed clients are compatible, provided source and transformation identity remains explicit.
5. **Environment availability:** installed dependencies, input type, storage/network permissions and platform restrictions can yield distinct availability outcomes; an actual cross-platform capability checker is unimplemented.
6. **Safety and effect truth:** structured failure, cancellation, progress, retry/idempotency, safe archive extraction and staged artifact materialization are distinct candidate controls, not demonstrated release guarantees.
7. **No automatic physical rewrite:** proposed directory trees, public-operation IDs, DBF pilot order and release acceptance matrices are Research. No standalone package or new client is authorized by this extraction.

## Publication exclusion and evidence policy

Several original sections involve context outside the public implementation publication boundary. Their underlying facts remain only in the unchanged original and its access authority. Derived public notes retain only **generic boundary and testing requirements**; no closed implementation names, internals, configuration, paths or package identities are reproduced. Those spans carry explicit `SAFE_EXCLUSION_NO_IDENTIFIERS` ledger dispositions. This producer pass does **not** certify that the original publication location is safe or that the historical code boundary has been repaired.

**Reliance limit:** complete original read and provisional semantic capture, partial direct-code verification, dependent historical/notebook evidence and publication-safe exclusions. No tests, package installs, notebooks, managed-node launch or cloud execution were run; no original-to-final-owner conservation is independently verified. `CENSUS.csv` advances `read_state=full_read` for `SB-SRC-0023` but keeps `material_unit_state=unaccounted`.

**Next:** handle machine-interpretable operation/scheme Research as a separate bounded original source, with the same confidentiality and historical-product safeguards. Then reconcile portability, execution and source-format semantics without combining current code and proposed target into one claim.
