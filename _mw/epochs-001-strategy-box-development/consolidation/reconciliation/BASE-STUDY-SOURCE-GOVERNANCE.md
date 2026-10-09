# Source catalog, reference registries and snapshot governance — Research extraction

**Full original:** `SB-SRC-0035` / `stratbox_registry_source_governance_research_2026-10-07.md`, L1–L2353, pinned blob `0d2a15a8b3630805a65b00dbba2e324cd2e7accf`. **Extracted:** 46 qualified, individually located, provisional material units. **Source identity:** the existing census entry remains stable; only `read_state=full_read`, with `material_unit_state=unaccounted` until verified owner-based conservation.

## Reconciled scientific and implementation concerns

1. **Entity Registry vs Source Catalog vs Source Snapshot:** one gives canonical identity, another an acquisition/discovery expectation, and the third actual fetched bytes/metadata. Domain rule registries and UI operation catalogs are distinct again. A single oversized registry manager is not required by common governance.
2. **Observed implementation weakness:** `src/stratbox/registries/_loader.py`, blob `b5d4ae9adda60808df84da20ecd648fcd595ec7e`, directly uses `stat().st_mtime` when selecting resource candidates. Filesystem mtime is not an immutable source revision. The proposed manifest+digest alternative is research, not current code.
3. **Observed divided source owners:** `cbr_banks.py` directly has different official-bank, alias, default-set and historical-set resource roots; `rosstat_okved2.py` loads classifier resources. `cbr_file_collector/registry.py` (blob `b7af2c380a028984ec4b465250ac44a0f05efab6`) declares a fixed external statistical source list and output defaults. Current code was read statically, not executed.
4. **Temporal freshness:** the original researcher compared bundled resources with upstream publisher files on 2026-10-07. These dates are *historical observations*, **not** current checks in this continuation. Do not claim all affected values wrong or that updates have been performed.
5. **Registry geography:** named Russian regions, statistical publication nodes, administrative aggregates and conditional exclusions have different identities. A global canonical entity registry should not erase source-specific geographic relations and evidence topology.
6. **Provenance:** source filename, URL, ETag and download time are each insufficient immutable identities. A byte digest, versioned registry bundle, transform schema and assumptions can be necessary to reproduce a derived report.
7. **Read-only runtime vs Git authoring:** proposal favors controlled validated source/registry updates through Git and immutable packages. Direct user editing, credentials, multiuser registry server and separate data-package lifecycle are alternatives or negative current recommendations, not accepted release scope.
8. **Quality conditions:** missing resource, invalid manifest, hash mismatch, stale publisher data and a failed source request must remain distinguishable; deterministic validation, package-install checks and live availability have different evidence scopes.
9. **Source shape:** fixed file, discovered publication index, parameterized form and reference upstream differ. Their common schema must not absorb a specific execution's retry count, output directory or parser implementation.
10. **Dependent conclusion:** the closing proposed migration matrix, sequence and schema examples restate previous analyses and do **not** multiply independent evidence or authorize a new package/directory.

## Assurance status

**PASS (producer source-read and provisional extraction only)** for the entire original Research Result and its 46 declared meaning units. **OPEN** for independent exhaustive unit conservation, line-to-direct-primary-evidence proof on all claims, live-source validity, cross-theme merge, Science admission, target Product authorization and Research Amputation. A saved example JSON is not a deployed `RegistrySnapshot`. Test plans were not executed.

**Next permitted work:** source/file/artifact research at `SB-SRC-0027` and `SB-SRC-0028`, then update source-unit lineage before proposing Science owner changes.
