# Bank of Russia command routes

The CBR root `DOMAIN` links continuing series, shared access/publication rules, calculation specifications and products. Sources specialize standard request, publication scan, issue selection, source assessment, material identification, table extraction, interpretation, validation and alignment commands. Standard operations and scenarios live outside the domain.

Use `StrategyBox.sources.list(domain_id='cbr')` to discover records. Invoke `scenario.series.refresh` with a series target and a supplied original, physical evidence or explicit source query. An `issue` identifies the publisher release; it does not substitute for observation dates parsed from source headers.

Statistical workbooks, reporting forms, service networks, corporate lending and escrow retain their own physical and semantic admission rules. The source-neutral flow does not impose a universal workbook geometry. Calculations consume validated observations; views and products use separate targets.

See [statistics](cbr-statistical-workbooks.md), [forms](cbr-reporting-forms.md), [service networks](cbr-service-network.md), [corporate lending](cbr-corporate-lending.md), [escrow](cbr-escrow.md), and the generic [offline route example](../../examples/source_route.py).
