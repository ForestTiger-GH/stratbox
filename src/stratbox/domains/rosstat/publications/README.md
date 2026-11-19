# Rosstat: exact source publications

## Scope

This package distinguishes series, issue, attachment and original byte version.
The series catalog fixes four officially supplied Rosstat landing pages.
An asset key consists of (series_id, issue_id, asset_id); a change in attachment
URL or filename without changed bytes is not a raw-source revision.

Use independent operations:

- rosstat.publications.discover: supplied HTML (offline) or HTTPS landing
  page (online), returning an index with qualified/ambiguous candidates.
- rosstat.publications.acquire: native bytes with a SHA acquisition receipt.
- rosstat.publications.acquire_to_store: stage, verify envelope, and commit to
  caller-provided filestore without modifying publisher bytes.
- source.compare_original_versions: first_seen, new_release (requires
  trustworthy previous inventory), revised, unchanged or indeterminate.
- source.read_original and source.reconcile_original: existing neutral replay
  and verification operations.
- source.original_version_committed event plus core.notifications delivery.

Index comparison and asset selection are pure functions in discovery.selection.
The caller chooses the original file destination (including any Git directory),
monitoring schedule, durable baseline keyed by each asset, release inventory,
publication authority, notification subscription, route and retry policy.
Storage confirmation is not remote Git publication confirmation.

The application that controls definitive publication issues a
PublicationReceipt with confirmation=confirmed, a matching source_id as
release_id, the same transition_id and the saved ByteIdentity. The independent
helper fact_from_original_version_commit then creates the qualified journal
fact eligible for the notification topic source.original_version_committed. The topic suppresses
FIRST_SEEN onboarding facts by default, and requires explicit opt-in to backfill.
The helper fact_from_original_bytes_changed is available for revisions only.
Do not subscribe to both change topics in the same user channel by default.

First-time backfills must not be reported as fresh publisher releases. The
notification topic requires explicit opt-in to mode=backfill. A failed check
must not overwrite an earlier confirmed baseline.

## Format and security limits

The initial HTML profiles are deliberately narrow and provisional. They match
only a compatible file format, a publisher-hosted permitted path, and a
recognizable publisher issue label or filename. Duplicate logical asset keys
with distinct URLs remain ambiguous, while unfamiliar indexes fail closed.
Downloads currently accept only the Rosstat central storage/mediabank and
upload paths. Other official paths/hosts require explicit live evidence.

PDF signature and EOF, ZIP central directory, OOXML required parts, and RAR
signature are checked without interpreting statistics. ZIP member CRC and RAR
archive integrity are not verified in this layer; use later archive readers
for those checks. Per-file limits are 100 MiB for XLSX/PDF, 256 MiB for
ZIP/RAR. Streaming stores use staged writes with readback verification.
Temporary network 404/403/5xx failures preserve existing saved originals.

Each operation can be called on its own. A consumer may also compose:
discover -> select_assets -> acquire/acquire_to_store -> compare original
identities -> owner confirmation -> event -> notifications.prepare/deliver.
This is a useful workflow, not a mandatory pipeline for every source.

## Next stages

Source-family owners can consume MaterialReference or SourcePayload directly,
then implement archive inspection, table extraction, period/classification
provenance, series-local representations (flakes), semantic comparisons and
calculations. They must never replace raw-byte change notifications with an
unsupported assertion that statistical observations changed.
