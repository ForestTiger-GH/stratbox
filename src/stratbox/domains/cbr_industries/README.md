# CBR industry series

The same typed industry selection is shared by corporate debt (01_05_A) and
monthly issuance (01_04_A). Use `IndustrySelection(("apk", "total"))` when
only APK and published TOTAL are required. All source values remain validated,
while unrelated observations are not materialized into the analytical stream.

`render_industries` generates several workbooks from one verified caller
snapshot. The independent `render_industry` remains available for individual
operation composition.

[Public operation contracts](../../../../docs/current-how/universal-business-core.md)

[Issuance-series semantics](../../../../docs/current-how/cbr-industries-issuance.md)
