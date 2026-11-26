# Frank RG command specifications

The public entry point is the immutable `DOMAIN` in
[domain.py](../../src/stratbox/domains/frank_rg/domain.py). It is a static catalog
of source-specific command specifications. The common capabilities catalog
defines executable commands, operations, scenarios and cascades.

| Directory | Responsibility |
| --- | --- |
| `common/` | Shared naming vocabulary, fourteen recognition rules and the delivered-file publication declaration |
| `series/` | Explicit continuing-series records grouped by Express, RBM, regional and special reports |
| `methods/publications.py` | Inventory recognition, exact issue selection, source attribution and evidence comparison |
| `methods/tables.py` | Explicit coordinate rules, source interpretation, validation and native-semantic placement |

The source IDs are:

| Group | Continuing source IDs |
| --- | --- |
| Express | `frg.express.issuance`, `frg.express.portfolios`, `frg.express.passives`, `frg.express.issuance_cards`, `frg.express.issuance_weekly` |
| RBM | `frg.rbm.volumes_q`, `frg.rbm.portfolios_q`, `frg.rbm.volumes_cards_q` |
| Regional | `frg.regional.issuance`, `frg.regional.portfolios`, `frg.regional.issuance_mortgage`, `frg.regional.portfolios_mortgage`, `frg.regional.issuance_cards` |
| Special | `frg.special.mortgage_refinancing` |

Regional filename recognition is bounded to the inspected scope starting
April 2026. Weekly labels are numbered weeks within a month. Q is a supplier
recognition marker. These facts describe publication identity.

Shared publication commands are `command.publication.scan`,
`command.issue.select` and `command.source.assess`. Each series supplies those
same narrow methods with its own source constraint, plus
`command.material.identify`, `command.table.extract`,
`command.table.interpret`, `command.observations.validate` and
`command.observations.align`. Filesystem listing/reading, workbook decoding,
calculation, retention, rendering, archiving and maintenance come from core.

The exact method protocol is `method(inputs, settings, context) -> named outputs`.
Settings contain source facts and explicit semantic rules. Runtime locations,
provider instances, output destinations and credentials are caller inputs.
No domain operation builder or alternative executor participates.

Every declaration has explicit applicability. Immutable maps prevent runtime
mutation of shared source specifications. The repository has one release
identity; publications carry factual issue IDs and exact content identities.

Use [the data route](frank-rg-data-route.md) for SDK calls. Scientific completion
still requires inspected publisher workbooks and reviewed business layouts for
all fourteen sources. Supplying a complete execution graph does not establish
those missing source facts.
