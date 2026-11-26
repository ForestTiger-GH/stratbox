# Dependency direction

Definitions and prepared plans depend on pure model and shared data contracts. The execution service consumes prepared plans and resolves the already bound methods. Source interpretation depends on shared values and neutral technical utilities. The SDK joins the preparation and execution boundaries.

No command definition imports a domain implementation. The explicit domain manifest loads root `DOMAIN` objects only. Each domain root links simple immutable mappings; there is no second builder or executable contribution registry.

`python scripts/check_internal_imports.py` rejects missing internal modules and imports through retired execution or registry owners. Metadata import checks run without optional dataframe, workbook or solver packages.
