# Rosstat publication evidence

The shared declarations are in
[common/publications.py](../../src/stratbox/domains/rosstat/common/publications.py).
Each publication directly specializes `command.request.prepare`,
`command.publication.scan`, `command.issue.select` and
`command.source.assess`, plus native `command.material.identify`.

| Publication ID | Official landing page | Main material |
| --- | --- | --- |
| `rosstat.socioeconomic_russia` | https://rosstat.gov.ru/compendium/document/50801 | PDF |
| `rosstat.socioeconomic_regions` | https://rosstat.gov.ru/folder/11109/document/13259 | ZIP/RAR |
| `rosstat.short_term_indicators.publications` | https://rosstat.gov.ru/compendium/document/50802 | XLSX |
| `rosstat.population_municipalities.publications` | https://rosstat.gov.ru/compendium/document/13282 | XLSX |

These are landing pages. The immutable source fact is the publication identity;
a concrete attachment additionally has a factual issue ID and asset ID.
The fetched bytes have an exact content identity. URLs, filenames and displayed
labels remain source evidence rather than permanent dataset addresses.

## Supplied index example

```python
from stratbox.capabilities.model.targets import FeedTarget
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material

target = FeedTarget("rosstat.short_term_indicators.publications")
page = Material(html_bytes, "text/html",
                source_id="rosstat.short_term_indicators.publications.index")
with StrategyBox() as box:
    scan = box.invoke("command.publication.scan",
                      inputs={"index": page}, target=target)
    selection = box.invoke(
        "command.issue.select",
        inputs={"listing": scan.output("listing"),
                "query": {"issue_id": "2026-08", "asset_id": "main_workbook"}},
        target=target,
    ).output("selection")
```

Scanning recognizes only bounded filename/label patterns. Its assessment says
that publisher inventory is uncertified. A requested issue can be selected
from observed evidence. Explicit `IssueQuery(mode="latest")` selects the latest
observed issue and carries that qualification; it establishes no globally newest publisher release.
Multiple locators for the same requested asset remain ambiguous.

The request method checks official HTTPS hosts and replays asset identity from
the selected filename/label before acquisition. Native identification checks
the outer PDF/XLSX/archive envelope. Numerical meaning is established later by
a table-specific interpretation command.

## Evidence comparison

A page observation cannot prove unchanged attachment bytes, disappearance from
the publisher's complete archive, or a new numerical release. Index assessment
therefore remains indeterminate about those claims. Reordering links or changing
an address is an index observation.

Comparing exact acquired materials establishes unchanged or changed bytes.
A first observation is `first_seen`; it does not prove a newly published issue.
Statistical revisions require comparison of accepted observations with matching
economic semantics.

The last confirmed stored/publication state advances after the intended
storage or publication effect is confirmed. Unknown effects remain in the
effect ledger for reconciliation. Notifications are generated from journaled
facts and durable notification state through the common notification commands.
A source failure, incomplete index or timeout creates a qualified failure fact,
rather than a fabricated unchanged/new-release conclusion.

The retained regression corpus includes real source-cell excerpts for reviewed
population and industrial editions, plus explicitly synthetic parser cases.
Those tests establish bounded interpretation behavior. They provide no live
certification of the current official HTML or complete publisher history.

See [the table route](rosstat-data-route.md).
