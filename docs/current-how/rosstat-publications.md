# Rosstat: acquire official originals and qualify byte updates

This guide describes independent operations. No scheduler, Git client, data parser,
archive extractor, notification channel or destination path is installed by import.

## Source catalog

`stratbox.domains.rosstat.publications.catalog.list_rosstat_sources()` returns
four stable publication series with official landing pages:

| Series | Source URL | Original envelope |
| --- | --- | --- |
| `rosstat.socioeconomic_russia` | https://rosstat.gov.ru/compendium/document/50801 | PDF |
| `rosstat.socioeconomic_regions` | https://rosstat.gov.ru/folder/11109/document/13259 | ZIP / RAR |
| `rosstat.short_term_indicators` | https://rosstat.gov.ru/compendium/document/50802 | XLSX |
| `rosstat.population_municipalities` | https://rosstat.gov.ru/compendium/document/13282 | XLSX |

These are *landing pages*, not stable direct attachment URLs.
Actual page HTML, attachment routing, file MIME values and release-layout rules
still require live publisher verification. The current discovery profile is
`rosstat-provisional-links-1`; its HTML fixtures are synthetic.

## Independent Python calls

```python
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.operations.source.originals import OriginalDestination
from stratbox.core.operations.source.version_comparison import (
    OriginalVersion, CompareOriginalVersionsRequest, compare_original_versions,
)
from stratbox.domains.rosstat.publications.contracts import (
    DiscoverRosstatRequest, AcquireRosstatToStoreRequest,
)
from stratbox.domains.rosstat.publications.discovery.selection import select_assets
from stratbox.domains.rosstat.publications.operations import discover, acquire_to_store

# Requires a configured HTTPS transport (provider). In the absence of network,
# supply the exact publisher index as SourcePayload to DiscoverRosstatRequest.
series = "rosstat.short_term_indicators"
index_result = discover(DiscoverRosstatRequest(series), transport=transport)
assert index_result.outcome == "succeeded", index_result.diagnostics
index = index_result.value

# The caller explicitly chooses a confirmed release. A provisional index does
# not authorize asserting that missing releases are absent from the publisher.
assets = select_assets(index, issue_ids=("2026-08",))
for asset in assets:
    store_result = acquire_to_store(
        AcquireRosstatToStoreRequest(
            asset, OriginalDestination("2026-08.xlsx", mode="immutable"),
        ),
        transport=transport,
        store=LocalFileStore("/caller/owned/originals"),
    )
    assert store_result.outcome == "succeeded", store_result.diagnostics
    stored = store_result.value.source
    # The caller retrieves last confirmed original version from its own state.
    previous = None  # replace with a persisted OriginalVersion when known
    candidate = OriginalVersion(asset.key.source_id, stored.storage.identity)
    difference = compare_original_versions(
        CompareOriginalVersionsRequest(candidate, "confirmed_absent")
    )
    assert difference.outcome == "succeeded"
    print(difference.value.state, difference.value.transition_id)
```

The example above is illustrative: the repository owner must provide `transport`
and a real directory; `confirmed_absent` is a **claim backed by owner evidence**.
When prior state is unavailable, pass `baseline_state="unavailable"`.
For a new release proven absent from a prior complete inventory, also supply
`prior_inventory_identity`. Never treat an HTML 404 or failed download as
`unchanged`. An identical SHA across different URLs for the same asset remains
unchanged; across two different issue keys it identifies different publication
assets with possibly identical bytes.

## Publication confirmation and notifications

A verified local storage receipt is not automatically evidence of a remote Git
commit. A destination owner confirms its own publication using
`PublicationReceipt(owner_id, destination_id, release_id, transition_id,
identity, confirmation)` where `release_id` identifies the logical source
asset and all IDs and bytes match the comparison. Only an owner-confirmed
receipt is accepted by
`fact_from_original_version_commit(comparison, publication, ...)`.

This produces a typed domain fact `source.original_version_committed` that
can enter the existing observability journal. It is eligible for the
`source.original_version_committed` notification topic when its state is
`new_release` or `revised`. Baseline `first_seen` is recorded but silent.
Backfill needs explicit subscription opt-in. The older
`source.bytes_changed` topic describes `revised` transitions only; avoid
routing both to the same recipient unless two messages are desired.

The consumer owns persistent monitor checkpoints, transaction ordering,
provenance of the previous inventory, a durable notification outbox and
recipient admission. The existing `notifications.prepare`,
`notifications.deliver`, `notifications.qualify` and
`notifications.reconcile` operations supply the handoff protocol.
See `examples/rosstat_originals_offline.py` for in-memory end-to-end
composition without the network.

## Recovery and accuracy

- If page acquisition fails, leave the last confirmed inventory unchanged.
- If a file cannot be obtained or its envelope is wrong, leave the destination
  and previous confirmed baseline unchanged.
- If a storage effect is unknown, reconcile that exact storage operation before
  declaring a committed version.
- If publication effects are unknown, obtain confirmation from the destination
  owner and replay only the owner-confirmed transition.
- An updated HTML document is *not* an assertion that a published file changed.
- A different original SHA is *not* proof that any economic observation changed.
- Preserve the source publisher's PDF, ZIP, RAR or XLSX byte stream without
  extracting, rewriting or normalizing it. Future family-specific parsers use
  `SourcePayload` or `MaterialReference` as independent input.

## Local verification

```bash
python -m pytest tests/unit/base/test_original_versions.py \
  tests/unit/base/test_rosstat_publications.py \
  tests/unit/base/test_rosstat_acquisition.py \
  tests/unit/notifications/test_original_version_commits.py \
  tests/unit/notifications/test_rosstat_notification.py
python examples/rosstat_originals_offline.py
```

The online HTML profile/format verification must follow once the publisher's
official sources are available. Offline fake-HTTP tests prove the local
contracts only, not the present structure of the official website.
