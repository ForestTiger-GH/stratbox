# Bank identity and display references

[Official registry access](registry.py) resolves CBR registration identifiers from
the packaged publisher workbook after content checks. Alias, display-selection
and sorting policies are separate reference inputs. `read_official_registry()` returns official
content; `read()` composes the curated display selection.

[Name normalization](names.py) supplies lexical comparison independently of
registry loading. Use `resolve_bank_entity()` for registration identity and
`resolve_registered_bank()` for traceable name-policy resolution.

Workbook and dataframe access require the corresponding optional dependencies.
See [reference loading and updates](../../../../../docs/current-how/reference-snapshots-and-update.md).
