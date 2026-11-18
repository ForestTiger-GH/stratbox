# CBR industry lending statistics

This source family contains two independent operation owners: `debt_0105a`
for corporate credit outstanding (stock) and `issuance_0104` for monthly
corporate loan issuance (flow). Their operation IDs and publication periods
remain distinct. The `common` package owns shared physical source parsing
and evidence helpers; it declares no operations.

Both series use a published industry dimension, geographic layout and APK
calculation formula. The issuance adapter explicitly references the official
01_05_A source profile where the physical semantics are identical.

[Domain operation contracts](../../../../../../docs/current-how/universal-business-core.md)

[Issuance-series semantics](../../../../../../docs/current-how/cbr-industries-issuance.md)
