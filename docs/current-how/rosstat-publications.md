# Rosstat originals: discovery, version comparison, publication, notification

The publication owner identifies official **series → publisher issue → file
asset → byte version**. It does not parse statistical tables, define
observation periods or choose an application's filenames. Parsing, archive
extraction, flakes, calculations and presentation are separate operations.

## Four official landing-page registrations

| Series ID | Publisher page | Currently expected original |
| --- | --- | --- |
| `rosstat.socioeconomic_russia` | https://rosstat.gov.ru/compendium/document/50801 | PDF |
| `rosstat.socioeconomic_regions` | https://rosstat.gov.ru/folder/11109/document/13259 | ZIP/RAR |
| `rosstat.short_term_indicators` | https://rosstat.gov.ru/compendium/document/50802 | XLSX |
| `rosstat.population_municipalities` | https://rosstat.gov.ru/compendium/document/13282 | XLSX |

These are *landing pages*, not immutable file URLs. Current official HTML,
redirects and attachment names remain unverified; direct official-page access
was unavailable during implementation. The four family-specific rules
under `discovery/families/` are deliberately **provisional**. They recognize
some conventional filename/label patterns but cannot claim that all files
are enumerated. The source has not passed a live deployment gate.

## Operable functions

```python
from stratbox.domains.rosstat.publications.catalog import list_rosstat_sources
from stratbox.domains.rosstat.publications.contracts import (
    DiscoverRosstatRequest, AcquireRosstatRequest, AcquireRosstatToStoreRequest,
)
from stratbox.domains.rosstat.publications.discovery.selection import (
    select_assets, compare_publication_indices,
)
from stratbox.domains.rosstat.publications.operations import discover, acquire, acquire_to_store
from stratbox.core.operations.source.originals import OriginalDestination
from stratbox.core.storage.filestore import LocalFileStore

series = "rosstat.short_term_indicators"
# The caller provides a configured HTTP transport. Alternatively, supply a
# SourcePayload with text/html or application/xhtml+xml to avoid the network.
result = discover(DiscoverRosstatRequest(series), transport=transport)
assert result.outcome == "succeeded", result.diagnostics
index = result.value
assert index.coverage == "unknown"   # current provisional profile

# Explicit selection is permitted; selecting "latest_qualified" is refused
# without a verified-complete index and a compatible publisher scope.
asset, = select_assets(index, issue_ids=("2026-08",))
store_result = acquire_to_store(
    AcquireRosstatToStoreRequest(
        asset, OriginalDestination("2026-08.xlsx", mode="immutable"),
    ),
    transport=transport, store=LocalFileStore("/caller/owned/originals"),
)
assert store_result.outcome == "succeeded", store_result.diagnostics
saved = store_result.value.source  # StoredOriginal, storage + material + acquisition
```

`acquire` returns the exact `AcquiredSource` in a domain wrapper without a
physical store. `acquire_to_store` streams to a caller-owned `StagedWriter`,
checks the outer file envelope (not complete XLSX/PDF/archive semantics),
commits and independently reads back exact bytes. Use `source.read_original`
and `source.reconcile_original` for future verified reads and uncertain
storage effects. Do not treat an HTTP 404 as an empty publication index.

The `DiscoveredAsset` carries the raw publisher href, displayed label,
filename, immutable index byte identity, profile and issue evidence. The
qualification guard replays family-specific interpretation before fetching
the file. An offline caller can construct candidates, but this is a typed
claim, not proof of a publisher-signed release.

## Three distinct levels of source evidence

1. **Candidate recognized:** one anchor looks like the requested source
   attachment. The profile has not necessarily enumerated the publication
   list; manual selection is possible. The whole index remains unverified.
2. **Index verified within declared scope:** a complete set of publisher
   attachments has been inspected for one explicit set of sections. The
   index must be publisher-acquired, unambiguous and tied to reviewed bytes.
   `ReviewedIndexScope` plus `approve_index` provides an **explicit owner
   review gate** for that particular HTML version, not an automated
   certification of all future HTML. Full automation requires future live
   calibration of the family profile.
3. **Original version published:** after the caller has verified the stored
   original and any remote publication requirement, an owner confirmation
   points to a concrete artifact version. Only this level can create a
   `source.original_version_committed` fact.

No status of a page alone proves that an original's bytes changed. No
original-byte change proves that statistical observations changed.

## Qualified absence and version chain

`SourceAssetIdentity(series_id, issue_id, asset_id)` is the portable key.
It excludes URLs, filenames, human-readable roles and SHA hashes. A filename
date can be a publisher issue hint; it is not automatically an economic
`observation_period`. Conflicting issue hints remain ambiguous.

```python
from stratbox.shared.source_publications import (
    SourceAssetIdentity, InventoryAbsenceEvidence,
)
from stratbox.core.operations.source.version_comparison import (
    OriginalVersion, CompareOriginalVersionsRequest, compare_original_versions,
)

key = asset.key.identity
candidate = OriginalVersion(key.source_id, saved.storage.identity)

# On initial onboarding, a baseline is an INITIAL observation, not a fresh
# publisher release; it is logged but silent to the default alert topic.
first = compare_original_versions(
    CompareOriginalVersionsRequest(candidate, "initial")
).value
assert first.state == "first_seen"

# On future checks, persist both original ByteIdentity AND last confirmed
# transition_id. A bare SHA is insufficient for A→B→A→B uniqueness.
confirmed = OriginalVersion(key.source_id, candidate.identity, first.transition_id)
same = compare_original_versions(
    CompareOriginalVersionsRequest(candidate, "available", confirmed)
).value
assert same.state == "unchanged"

# For a truly new issue or asset, the owner provides InventoryAbsenceEvidence
# built from a versioned, verified-complete inventory in the SAME series and
# declared issue scope. Passing any arbitrary SHA string is never sufficient.
# absence = InventoryAbsenceEvidence(key, previous_qualified_inventory)
# new = compare_original_versions(
#     CompareOriginalVersionsRequest(candidate, "absent_proven", absence=absence)
# ).value
```

`CompareOriginalVersionsRequest` has explicit states:
`initial`, `available`, `absent_proven` and `unavailable`.
Its results are `first_seen`, `unchanged`, `revised`, `new_release`,
`new_asset` and `indeterminate`. A proof about an existing issue's new
attachment produces `new_asset`. `new_release` requires absence of its
entire issue in the qualified previous scope.

## Publication and alerts

A caller stores or references the exact immutable version in its selected
storage system (Git history and content-addressed stores are both valid).
It retains a versioned baseline pointer; candidate staging does not change
the last confirmed pointer. The owner must preserve the previous confirmed
SHA, transition ID and artifact reference for reproducibility.

After confirming final publication and independently verifying its owner
effect, construct:

```python
from stratbox.shared.evidence import PublicationReceipt
from stratbox.shared.source_publications import (
    PublishedArtifactRef, ConfirmedOriginalPublication,
)
from stratbox.core.observability import fact_from_original_version_commit

artifact = PublishedArtifactRef(
    "originals", key.source_id, candidate.identity.sha256, candidate.identity,
    "owner-verified-readback-or-git-commit",
)
publication = ConfirmedOriginalPublication(
    PublicationReceipt(
        "owner", "originals", key.source_id, first.transition_id,
        candidate.identity, "confirmed",
    ),
    artifact,
)
fact = fact_from_original_version_commit(
    first, publication, asset=key, mode="live",
    occurred_at_utc=observation_time_utc,
)
```

The fact contains a safe, structured `artifact_ref` (scope, artifact ID,
version ID, hash, size), not a guessed Git URL or private filesystem path.
The owner must independently verify that its publication receipt is authentic;
constructing a dataclass with `confirmation="confirmed"` alone does not
verify an actual remote Git push.

The `source.original_version_committed` topic suppresses first-seen
onboarding and requires explicit opt-in to backfill. Use that topic as the
canonical user notification for new issues, new assets and revised originals.
The older `source.bytes_changed` helper only accepts live revisions and
should not be subscribed to alongside the canonical topic by default.
Core `notifications.prepare/deliver/qualify/reconcile` handle delivery,
deduplication and uncertain responses. The application owns its durable
journal/checkpoint/outbox and its actual Telegram credentials.

## Failure handling and source health

`core.operations.source.checks.assess_source_check` produces a neutral
health observation from an execution result, without claiming "unchanged".
A missing source, broken HTML profile, unsafe link or download timeout must
not replace the last confirmed version or turn into a source-update event.
Repeated health failures may be separately alerted by consumer policy.

Do not use `immutable` with the *same physical filename* for different
original byte revisions without a version-retention strategy. Choose
immutable version paths or versioned Git history with a pinned commit;
only update the latest-confirmed pointer after final owner publication.

## Local QA and live admission

```bash
python -m compileall -q src tests examples/rosstat_originals_offline.py
python -m pytest -q tests/unit/base/test_original_versions.py \
    tests/unit/base/test_rosstat_publications.py \
    tests/unit/base/test_rosstat_acquisition.py \
    tests/unit/base/test_source_check_assessment.py \
    tests/unit/notifications/test_original_version_commits.py \
    tests/unit/notifications/test_rosstat_notification.py
python examples/rosstat_originals_offline.py
```

The above shell commands are the acceptance procedure; their execution in
the actual project checkout has **not yet been verified** through the GitHub
connector. The live publisher gate is independent: record real HTML and
one native attachment per family, verified redirect/MIME/size and approved
profile section coverage. Until then leave automatic `latest` and absence
notifications disabled.
