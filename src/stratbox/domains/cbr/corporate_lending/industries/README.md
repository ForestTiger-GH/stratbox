# CBR industry lending statistics

This source family contains two independent operation owners: `debt_0105a`
for corporate credit outstanding (stock) and `issuance_0104` for monthly
corporate loan issuance (flow). Their operation IDs and publication periods
remain distinct. The `common` package owns shared source parsing, evidence, structural
industry/geography/validation contracts, pivot result contracts and rendering;
it declares no operations. Stock and issuance retain independent request types,
physical sheet profiles, release identities and time semantics.

Both series use a published industry dimension, geographic layout and APK
calculation formula. The issuance adapter references the official 01_05_A source profile only
where the physical semantics are explicitly verified as identical. If layouts
diverge, define independent publication profiles rather than inheriting them.

[Domain operation contracts](../../../../../../docs/current-how/universal-business-core.md)

[Issuance-series semantics](../../../../../../docs/current-how/cbr-industries-issuance.md)
