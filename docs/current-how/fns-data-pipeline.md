# FNS: standard commands and source-specific evidence

The static entry point is
[`domains/fns/domain.py`](../../src/stratbox/domains/fns/domain.py). It declares two
continuing source records: `fns.sme` and `fns.1yur`. Each record supplies narrow
settings and methods for standard commands. Operations, scenarios, scheduling,
provider selection and execution belong to the common layers.

## Owners

| Directory | Responsibility |
| --- | --- |
| `common/` | Official access rules, publication dates, source fields and reviewed historical mappings |
| `series/` | Explicit per-series `CommandSpec(method, settings, applicability)` maps |
| `methods/publications.py` | Pure request preparation, supplied-index interpretation, issue selection and qualified update assessment |
| `methods/sme.py` | JSON-record selection, reviewed SME counters and geographic identity |
| `methods/legal_entities.py`, `legal_rows.py`, `legal_numbers.py` | Selection and historical interpretation of retained Form 1-YUR workbook evidence |
| `methods/validation.py` | Observation grain, count semantics and source arithmetic |
| `calculations/` | Static numerical purposes using the common numerical commands |
| `products/` | Static selection and presentation purposes |

`DOMAIN.common` holds shared immutable access facts. The series refer directly
to ordinary shared settings and dictionaries. Source declarations neither build
operations nor import another executable registry.

## Publication and legal entrances

| Action | SME register | Form 1-YUR |
| --- | --- | --- |
| Prepare index request | GET of the official statistics page | GET of the declared official forms index |
| Prepare asset request | Read-only POST to `statistics-proc.json`, `statDate=DD.MM.YYYY` | GET of the actual dated official attachment |
| Physical decode | `command.json.decode`: `Material → JsonEvidence` | `command.workbook.decode`: `Material → WorkbookEvidence` |
| Select source tables | `command.table.extract`: `JsonEvidence → TableEvidenceSet` | The same command: one or several `WorkbookEvidence → TableEvidenceSet` |
| Interpret | `command.table.interpret`: tables and issue context → source dataset | The same command with reviewed historical Part I rules |
| Qualify | `command.observations.validate`: dataset → dataset and assessment | The same command with the applicable historical source semantics |
| Align | `command.observations.align`: source dataset → integrated dataset | Dated identity mappings of reviewed fields and legal kinds |

A `PublicationAsset` passed as `locator` retains its source and issue identity.
Preparing a request performs no network access. Scanning an explicitly supplied
index performs no fallback acquisition. Observed index membership establishes
its own scope; an unchanged page does not establish unchanged attachment bytes
or complete publication history.

## Offline use through the common facade

```python
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material

with StrategyBox() as box:
    result = box.invoke(
        "operation.series.extract_structured",
        target="fns.sme",
        inputs={"material": Material(response_bytes, "application/json", "fns.sme")},
        parameters={"format": "json", "as_of": "2026-11-10"},
    )
    if result.outcome != "succeeded":
        raise RuntimeError(result.diagnostics)
    source_dataset = result.output("dataset")
    aligned = box.invoke(
        "command.observations.align",
        target="fns.sme",
        inputs={"dataset": source_dataset},
    )
    dataset = aligned.output("dataset")
```

The explicit operation exposes decode, source-table selection, interpretation
and required validation as separate steps. A retained `JsonEvidence`,
`WorkbookEvidence` or source dataset is also a legal independent entrance to
its corresponding command. A request or update assessment is not an input to
a numerical command.

For a Form 1-YUR archive the standard recipe unpacks the original, selects
workbook members, decodes them with a bounded map and then calls source-table
selection once on the collection. This matters because Part I and Part II are
separate members of one publication. Part II retains physical evidence without
acquiring Part I meaning. The original archive and complete unpacked inventory
remain independently retainable.

## Scientific content

SME decoding preserves every JSON field, source type, order and exact numeric
lexeme. Interpretation covers the nine reviewed counters: total SME subjects,
legal entities, individual entrepreneurs and their micro/small/medium groups.
Missing counters remain absent. Unknown source fields remain in physical
evidence and produce interpretation-coverage findings. Source country,
federal-district and subject namespaces remain separate. `stat_date` establishes
the observation date; publication and capture dates have separate roles.

Form 1-YUR interpretation preserves printed indicators, legal-kind sheets,
source territories, member names and cell coordinates. Historical rules cover
five reviewed layout periods from January 2012 onward. The June 2019 exception
admits the reviewed complete all-entities sheet while retaining and qualifying
incomplete category sheets. Comparable sparsity at an unreviewed date fails
admission. Territory overlaps, national-versus-territorial differences and
orientation discrepancies remain explicit findings.

Alignment is identity-only. A historical LLC category excluding additional
liability companies does not become a later inclusive category by renaming.
`not_ceased` and `bankruptcy_proceedings` are qualified stocks. The accumulation
window of `ceased_bankruptcy_liquidation` remains unresolved; its reporting
date establishes neither a monthly event flow nor a stock.

## Numerical commands, retention and effects

`fns.stock_change` applies `command.calculate.change` to qualified matching
stocks. Its result is a net change over the two observation dates, not a count
of registrations, births, entries, exits or liquidations. `fns.stock_share`
applies `command.calculate.ratio` to explicitly selected numerator and
denominator observations with matching dates, geography, units and perimeter.
A zero denominator produces an undefined result. Unresolved event counts fail
stock-calculation admission.

The same numerical route can consume one queried time series or a selected
whole table. Source extraction is separate from time-series selection,
partitioning and calculation. Seasonal adjustment additionally requires an
explicit numerical provider and admitted temporal frequency.

`command.value.encode` / `command.value.decode` retain and restore physical
or semantic values, exact tokens, assessments and lineage. `command.dataset.ingest`
receives a logical dataset. `command.artifact.commit` receives encoded bytes.
Encoding implies neither operation. Storage and external delivery expose their
own receipts and outcomes.

Successfully recognized geometry and checked values produce typed `SourceUse`
records with source, issue, material and interpretation scope in one coordinate.
Layout and semantic identities are hashes of actual reviewed facts. Alignment,
calculation and replay preserve these records. This scientific qualification
does not claim that caller-supplied bytes were acquired from an official server.

All stages run through the common execution service. The journal records
command admission, execution and accepted outputs before notification delivery.
Domains neither save files nor send notifications inside interpretation methods.
Repository revision and factual content identities identify an implementation
and its evidence; source declarations and methods have no release counters.

## Evidence limits

Synthetic historical XLS/XLSX fixtures exercise reviewed layout rules, sparse
coverage, exact numbers and source invariants. They do not certify every
publication ever issued. A newly observed layout needs actual source material,
reviewed geometry and corresponding scientific assertions before expanding
semantic coverage. See the [binding reference](fns-capability-migration.md) and
the [common invocation lifecycle](capability-session.md).
