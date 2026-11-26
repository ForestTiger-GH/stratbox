# FNS command bindings

The maintained route is [FNS data processing](fns-data-pipeline.md). Public calls
use standard command and operation IDs with `target="fns.sme"` or
`target="fns.1yur"`.

| Standard command | FNS contribution |
| --- | --- |
| `command.request.prepare` | Official GET/read-only POST rules, source/issue checks |
| `command.publication.scan` | Source-specific interpretation of supplied index evidence |
| `command.issue.select` | Explicit source/date selection and ambiguity handling |
| `command.source.assess` | Qualified comparison of candidate and baseline evidence |
| `command.table.extract` | JSON record selection or Part I selection from decoded workbook collection |
| `command.table.interpret` | Reviewed counter, geography and historical table semantics |
| `command.observations.validate` | Count, grain and arithmetic checks |
| `command.observations.align` | Explicit metric aliases and dated legal-kind identities |

Physical JSON/workbook decoding, archive work, numerical commands, retention,
formatting, execution and notifications use common owners. The immutable
[`DOMAIN`](../../src/stratbox/domains/fns/domain.py) is the only domain entry
point. Its `series`, `calculations`, `products` and `common` mappings are static.

`operation.series.extract_structured` selects the visible JSON route for SME.
`operation.series.extract_workbook` handles a single workbook;
`operation.series.extract_archive` handles a publication workbook collection.
`scenario.series.refresh` composes admitted source steps and explicitly requested
retention. A caller may instead invoke any command directly with its typed
input. A prepared source-table value does not imply completed interpretation.

The domain contains no compatibility operation API, operation generator,
profile registry or independently versioned source model. To extend source
coverage, add actual publication evidence and narrow source rules, then test the
corresponding standard command. Avoid adding a second workflow engine under a
domain directory.
