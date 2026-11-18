# Packaged reference data

Each reference family owns an edition manifest under its `_resources/` directory. A manifest selects one active edition and declares role, relative path, SHA256, exact byte size and whether the asset is required. Consumers use `load_reference()` with a package owner and an optional explicit edition identifier.

- `banks/`: Bank of Russia source workbook, name aliases and named selections.
- `okved2/`: Rosstat classification CSV materials.
- `geography/`: reviewed, conservative territory name rules and scope-aware resolution.

Reading a resource verifies its bytes before parsing and may append an input receipt carrying the edition snapshot identity. Reference material does not independently establish source authority, territorial boundaries or statistical comparability.

[Reference update procedure](../../../../docs/current-how/reference-snapshots-and-update.md)


Manifest admission, maintenance staging and wheel inspection now share one
`parse_reference_manifest()` and a per-family required-role contract.
Every edition is validated before the active one is selected. Reference
snapshots use schema 2 and include declared per-asset provenance metadata.
`qualified_reference_use()` checks the edition, role, media type, exact
bytes and snapshot of a generic used-input receipt.
