# OKVED2 classification

[Registry access](registry.py) reads verified classification, metadata and
structure assets. `read()` preserves published code and section order;
`read_meta()` and `read_structure()` expose their separate source contents.

Dataframe access requires pandas. The classification supplies an identifier
vocabulary; a domain's selected industries, aggregation and economic perimeter
remain separately declared.

See [reference loading and updates](../../../../../docs/current-how/reference-snapshots-and-update.md).
