# Rosstat command specifications

The single [domain.py](../../src/stratbox/domains/rosstat/domain.py) exposes
immutable `common`, `series`, `calculations` and `products` maps.

| Directory | Actual owner |
| --- | --- |
| `common/publications.py` | Four publication declarations, official landing URLs and shared issue/asset rules |
| `common/kep2.py` | Eleven-indicator dictionary |
| `series/` | Three continuing numerical source declarations with direct standard-command bindings |
| `methods/publications.py` | Official request preparation, bounded index recognition, issue/asset selection, evidence assessment |
| `methods/materials.py` | Native outer-envelope qualification |
| `methods/tables.py` | Existing physical evidence selection, scientific method dispatch, validation, native-semantic placement |
| `methods/kep2.py` and `methods/editions.py` | Reviewed numerical rules and source-specific evidence |
| `methods/documents.py` | Exact-original explicit document-region semantics for caller-reviewed material |
| `methods/products.py` | Monthly KEP2 view and XLSX rendering |

A `CommandSpec` gives the method reference, frozen settings and explicit
applicability. Methods implement `(inputs, settings, context) -> named outputs`.
Common operations own composition; core owns execution, physical decoding,
effects, budgets, observation, notifications and provider interaction.

The publication family `rosstat.socioeconomic_regions` supplies acquisition
facts. Its reviewed numerical series
`rosstat.socioeconomic_regions.industrial_production` supplies table semantics.
This explicit relationship avoids treating an entire heterogeneous archive as
one numerical table. The national PDF is likewise a publication channel until
its actual table inventory and reviewed numerical geometry are supplied.

Calculations operate on accepted rows or time series. The
`rosstat.index_growth` record selects the generic percent-index calculation.
The `rosstat.kep2.monthly` and `rosstat.kep2.monthly.xlsx` records select
monthly presentation methods. Each can be called independently of acquisition.

Source facts are not duplicated in operations or scenarios. Provider instances,
filesystem roots and output destinations stay outside the catalog. Factual
issues and content identities support reproducibility; component release
counters are absent.

Scientific obligations are explicit in `DOMAIN.common["scientific_obligations"]`:
real national PDF table mappings, the remaining regional archive table census,
reviewed cross-edition geography, and additional historical layouts.
The available reviewed population editions are 2022/2023/2024; reviewed regional
industrial layouts cover June/August 2026.

Use [publication evidence](rosstat-publications.md) for discovery and
[the data route](rosstat-data-route.md) for extraction and products.
