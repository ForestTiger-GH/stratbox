# Bank of Russia data operations

One CBR registration aggregates independent operation segments. Twelve root
`REGISTRY_*.yaml` files declare logical publication families; source access,
table layouts, semantic integration, calculations and products have separate
functional owners.

- [Publications](publications/): logical series, source discovery, acquisition and collections.
- [Tables](tables/): source layouts, exact extraction and source flakes.
- [Integration](integration/): versioned mappings, observations and source histories.
- [Analytics](analytics/): calculations and complete model inputs.
- [Products](products/): prepared views and file rendering.
- [Operations](operations/): typed entry points, composition and catalog bindings.

`cbr.describe_source` and `cbr.describe_family` describe exact source scope,
table editions, operation versions, handoffs and explicit coverage limits.

[Publication and processing routes](../../../../docs/current-how/cbr-data-pipeline.md)
