# 01_05_A corporate lending debt

This owner implements the official Bank of Russia 01_05_A outstanding
corporate loan statistics by published industry and region: discovery,
acquisition, workbook parsing, selective streams, APK calculations, pivots,
and verified spreadsheet representations.

Source-specific physical profiles and publication rules remain local to this
owner. Common cell parsing and operation evidence utilities are implemented
under the sibling `common` package. The independent flow publication is
`../issuance_0104/`.

[Public operation contracts](../../../../../../../docs/current-how/universal-business-core.md)

The industry, region, validation, APK and pivot structural contracts used by
this publication are defined once in the sibling `../common/contracts.py`.
The debt owner retains its six-sheet source profile, stock time semantics and
separate request and output operations.
