# Publisher and scientific domains

Each domain exports one immutable `DOMAIN`. Continuing series, calculations and
products bind standard command IDs to methods, settings and applicability.
Shared source facts and vocabularies are authored once within that domain.

Choose [CBR](cbr/) for Bank of Russia statistics, [FNS](fns/) for tax-service
publications, [Minfin](minfin/) for fiscal data, [Frank RG](frank_rg/) for delivered
reports, or [Rosstat](rosstat/) for official statistical publications.

The [domain catalog](../capabilities/catalog/domains.py) loads these declarations.
[Capabilities](../capabilities/) own reusable graphs, while [core](../core/)
executes them. Methods consume supplied physical or numerical evidence and return
qualified values.

See [domain routes and scientific coverage](../../../docs/current-how/independent-domain-data-routes.md).
