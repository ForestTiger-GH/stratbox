# Bank of Russia table interpretation

This package owns source-specific table geometry, row and column meaning,
measurement semantics and scientific evidence. Methods consume physical values
from common decoders and preserve source-local identities and qualifications.

[Action methods](../actions/) expose these mechanisms through standard extraction
and interpretation ports. The [domain catalog](../../domain.py) supplies the exact
series settings. Explicit identifier mappings belong to [alignment](../alignment/);
numerical models belong to [calculations](../../calculations/).

See [statistical workbook semantics](../../../../../../docs/current-how/cbr-statistical-workbooks.md).
