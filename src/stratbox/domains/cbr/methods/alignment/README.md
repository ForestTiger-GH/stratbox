# Bank of Russia identity alignment

This package owns explicit mapping from source-native identifiers and geography
to the selected analytical addresses. Mappings preserve the evidence and
statistical perimeter of the interpreted source.

[Corporate-lending alignment](corporate_lending/) supplies its domain-specific
mapping contracts. The standard alignment entry point is bound through
[action methods](../actions/) and the [domain catalog](../../domain.py).

Source parsing belongs to [table methods](../tables/); aggregation and numerical
reconstruction belong to [calculations](../../calculations/).
