# Packaged reference editions and maintenance

**Current implementation scope:** Bank, OKVED2 and geography references are distributed inside Stratbox for offline use. Edition selection is explicit and every read validates the declared SHA256 and byte size; the manifest itself is also part of the installed package. This procedure applies to these reference owners without requiring a running application.

## Navigation

1. Reference components — definition, edition, asset and snapshot.
2. Read and reproduction — choose a pinned edition and collect evidence.
3. Edition update — source acquisition, immutable role mapping and active selection.
4. Validation — exact bytes and installed wheel.
5. Evidence limits and failure handling — what hashes can and cannot prove.

## 1. Components

| Code | Component | Meaning |
| --- | --- | --- |
| REF-1 | Reference definition | An independently owned logical classifier or name policy. |
| REF-2 | Reference edition | A named, manifest-listed set of assets and optional publisher/source metadata. |
| REF-3 | Asset | A declared role, path, media type, SHA256, byte length and required flag. |
| REF-4 | Snapshot | Canonically hashed, ordered role/path/byte declarations. |
| REF-5 | Used input | Exact asset bytes actually read, with role and snapshot version. |

The active edition is specified by `active_edition`; a caller may specify `edition_id`. Readers use `importlib.resources.files`, not source-tree-relative paths. Resource manifests can include multiple named editions; each edition must be internally complete. Bank roles are `official_xlsx`, `aliases`, `default_selection`, `legacy_selection`; OKVED2 roles are `data`, `meta`, `structure`; geography initially has `aliases`.

## 2. Read and reproduction

```python
from stratbox.shared.reference.assets import load_reference

bundle = load_reference("stratbox.shared.reference.banks", edition_id="bundled-original-2026-11")
inputs = []
asset = bundle.read("aliases", inputs=inputs)
assert inputs[0].version == bundle.snapshot_identity
bundle.validate_all()
```

For domain usage, pass `inputs=...` to `banks.registry.read()` or `okved2.registry.read()`; the role of each actually consumed file is retained. An unchanged asset file can appear in two editions, but the editions have different snapshot identities when their role mapping or edition IDs differ.

## 3. Updating a reference edition

1. Obtain source material and preserve the original bytes. Record its publisher and retrieval evidence outside the manifest if that evidence exists.
2. Place newly obtained materials in the correct package `_resources/` subtree under new distinct names; do not overwrite an asset still referenced by an earlier edition.
3. Create a new `edition_id` entry in `manifest.json`. Declare each role and relative file path explicitly. Include all required assets for the owner. A role may point to unchanged previously packaged bytes.
4. Compute `sha256` on **the original bytes** and record the exact byte `size`; for CSV never hash a silently transcoded UTF-8 string. Preserve format encoding as the owner expects.
5. Record `publisher`, `source_url`, `published_at`, `effective_from` and `effective_to` only where verified. Use JSON `null` when those facts are unknown. The date encoded in a filename is merely a hint.
6. Change `active_edition` to the new exact edition identifier, without deleting an earlier valid edition needed for reproducibility.
7. Validate all roles and the parsed table/aliases against offline tests. Reject duplicate aliases with conflicting subjects or duplicate roles.
8. Build a distribution wheel, install it into a clean environment, and verify every declared file's SHA256 and size using `load_reference(...).validate_all()` before shipping.

A change to user-chosen bank selection or aliases is a new policy edition even if the official workbook stays unchanged. A territory-name change that asserts a new identity must have its own rule ID and review basis. An OKVED2 resource update does not automatically justify different industry aggregation methods.

## 4. Maintenance helper

The offline `scripts/reference_editions.py` tool verifies every declared
asset in every edition (including optional assets):

```bash
python -B scripts/reference_editions.py verify --reference all
```

For a newly reviewed edition, first place files under new names in the owner
package. Then stage the explicit role changes; every old edition is checked
before stage and a historical asset path cannot be overwritten:

```bash
python -B scripts/reference_editions.py stage --reference banks \\
  --edition-id reviewed-example-2 --asset aliases=aliases/new-aliases.csv --activate
```

The helper never fetches external source data, invents publication dates,
transcodes CSV bytes, or assigns new statistical meanings. Review its proposed
manifest and run the tests before committing; the command is an example, not a
request to stage a specific edition.

## 5. Validation commands

```bash
python -B scripts/check_release_integrity.py
python -B scripts/check_internal_imports.py
python -B -m pytest -q tests/unit/shared
python -B -m pytest -q
python -m pip wheel . -w dist --no-deps
# Substitute the actual produced wheel filename:
python -B scripts/inspect_reference_wheel.py dist/stratbox-VERSION-py3-none-any.whl
```

The wheel inspection reads the ZIP members directly, verifies every manifest
asset in every edition, and rejects obsolete paths. For wheels named with a
different Python/ABI tag, substitute the actual filename. Run the same resource
verification after installing the built wheel outside the checkout. An installed package may be missing assets even if imports succeed in editable mode; compare the manifest, package file paths and byte digests directly. Tests are local/offline and should not trigger remote workflows.

## 6. Limits and errors

A digest proves byte equality to a pinned manifest claim, not the origin or normative currentness of the underlying file. A statistical reference cannot infer the published perimeter of a concrete dataset. Absence of a required asset and hash mismatch fail explicitly; a structurally invalid CSV cannot be converted silently to an empty authoritative reference. Name ambiguities and out-of-scope historical labels remain unresolved until a reviewed rule and source context are provided.
