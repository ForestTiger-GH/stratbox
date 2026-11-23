# Minfin

The domain owns four publisher families and thirteen logical series: ten budget
and NWF workbook series, plus three historical NWF document series. Root
`REGISTRY_*.yaml` files declare logical sources; typed profiles own source
recognition, table interpretation and reviewed calculations.

| Owner | Responsibility |
| --- | --- |
| [publications](publications/) | Publisher indexes, acquisition, release evidence and checkpoints |
| [documents](documents/) | Ordered PDF/DOCX blocks, publication context and durable replay |
| [tables](tables/) | Exact source cells, source-local flakes, validation and codecs |
| [integration](integration/) | Explicit row semantics and common qualified observations |
| [analytics](analytics/) | Reviewed headlines and independently retained calculation results |
| [products](products/) | Prepared selections, replay and portable rendering |
| [operations](operations/) | Runtime admission, evidence, source cards and one operation owner |

Monthly and quarterly budget values retain cumulative YTD periods. NWF units and
basis are row-specific. Publication dates remain release evidence. Integration
uses reviewed headline bindings or explicit caller-supplied row bindings;
headline admission verifies the monetary unit and scale. Source, integrated,
calculated and prepared values have independent persistence/replay boundaries.

- [Complete data route and contracts](../../../../docs/current-how/minfin-data-route.md)
- [Executable offline route](../../../../examples/minfin_portable_route.py)
- [Source and operation metadata](operations/source_catalog.py)
- [Publication and table profiles](operations/bindings.py)

Storage, scheduling, provider selection and delivery are consumer-owned. The
same typed snapshots work with any admitted logical dataset store. Legacy DOC
assets remain retainable originals; ordered document extraction supports
PDF/DOCX with explicit coverage qualifications.
