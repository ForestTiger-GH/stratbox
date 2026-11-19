# Rosstat official publication originals

Registered owner: `rosstat.publications`.

**Scope:** series → publisher issue → logical file asset → exact original
byte version. The four original formats are PDF, XLSX, ZIP and RAR. All
technical receive, stage, save, read, hash, compare, observe and notify
infrastructure is reused from `core` or `shared`.

There are three independent operations:

- `rosstat.publications.discover`: a publisher-acquired or explicitly supplied
  HTML page, converted into a bounded, evidence-qualified index.
- `rosstat.publications.acquire`: one explicit attachment downloaded with
  strict HTTPS admission and native envelope validation, returned as bytes.
- `rosstat.publications.acquire_to_store`: streaming native file acquisition
  and staged storage using the consumer's chosen `OriginalDestination`.

Pure helpers: `discovery.selection.select_assets`,
`discovery.selection.compare_publication_indices`, and
`discovery.coverage.qualified_inventory_from_index`.

The `discovery/families/` directory owns source-specific *publication*
identity, not economic table semantics. The file `discovery/links.py`
contains bounded literal anchor extraction. `discovery/approval.py` lets
a trusted owner explicitly attest to the complete set of files on ONE
concretely acquired HTML page, with an evidence reference and declared
sections. This is not a global certification of the site's present layout
or future releases.

**Current operational restriction:** automatic publisher HTML completeness
is unverified for all four landing pages. The source-specific patterns
are provisional. Recognized candidates may be chosen explicitly, but
`coverage` is `unknown` and automatic `latest_qualified` and absence
claims are refused until qualified evidence is available.

The publisher may change a URL or link label without revising an original.
The stable `SourceAssetIdentity` deliberately excludes locators and SHA.
`source.compare_original_versions` compares accepted original identities
against a durable previous transition or a fully qualified prior inventory.
`source.original_version_committed` is emitted only on an owner-verified
publication version, and `core.notifications` owns reliable delivery.
`first_seen` and historical backfill are not automatic fresh-release alerts.

The consumer owns exact original destination, release-commit proof,
version history/retention policy, durable monitored state, schedule, journal,
notification subscriptions, queues, channels and Git publication.
No Git/Telegram integrations or statistical parsers are bundled with this
owner. Readers, archive extractors, table parsers, period interpreters,
flake representations and economic calculations can be added as neighboring
source-family owners without modifying the original publication contract.

See [the complete how-to](../../../../../docs/current-how/rosstat-publications.md)
and [the offline example](../../../../../examples/rosstat_originals_offline.py).
