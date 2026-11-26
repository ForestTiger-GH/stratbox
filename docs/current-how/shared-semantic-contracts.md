# Semantic values and source evidence

`shared.data.values` defines the current value contracts. `Material` holds original bytes; decoded evidence preserves the original material, physical cells or native JSON tokens; `SourceDataset` contains source observations; `IntegratedDataset` and `DerivedDataset` describe subsequent semantic work. `TimeSeries` describes one explicit grain across periods. A product or storage reference provides a different guarantee from a dataset.

Coordinates, units, scale, period kind, perimeter, value status and source issue remain explicit. A stock, interval flow, year-to-date value and unresolved event count have different meanings. Domain interpretation produces these meanings from declared source settings; the executor checks the required input and output contracts.

Byte identities and fingerprints describe actual content. Source claims distinguish asserted and identified attribution. Exact input receipts record the material, reference content and archive member used. Coverage names the actual accepted scope; complete subject and metric lists alone do not prove a complete cube.

Portable encoding uses a fixed type vocabulary. Data cannot import a Python class. Unknown scientific types require an explicit domain codec. See [processing stages](standard-data-stages.md) and [execution](capability-session.md).
