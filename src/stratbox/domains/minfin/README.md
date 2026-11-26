# Ministry of Finance statistics

The [domain catalog](domain.py) declares fiscal series and their standard action
bindings. [Common facts](common/) own publication rules and shared row semantics;
[methods](methods/) interpret supplied workbooks or explicitly reviewed document
fields.

Publication dates and economic periods remain separate. Workbook interpretation,
document field review, numerical treatments and presentation each have their own
scope in the [series](series/), [calculations](calculations/) and [products](products/)
declarations.

See [fiscal data interpretation](../../../../docs/current-how/minfin-data-route.md)
and [command bindings](../../../../docs/current-how/minfin-capability-migration.md).
