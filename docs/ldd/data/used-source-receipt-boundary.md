# Candidate LDD — the source bytes actually consumed by a banking/macro operation

**Status:** `CANDIDATE / SOURCE-GROUNDED / NOT EXECUTED / PRODUCT DECISION OPEN`. **Consumer:** implementer and reviewer of the first **local Python-core, single-run** provenance pilot, without presuming a universal Source Catalog, long-term storage service, Windows UI, remote host or deployed AppDock API. **Product candidate:** truthful source provenance for *inputs actually used*; the specific capture requirement remains conditional on Product Authority. **Evidence baseline:** [Current HOW download/registry mechanisms](../../current-how/source-download-receipts-registry-choice-and-coverage-limits.md), [Science on source vintages](../../science/data-and-knowledge/source-observation-vintages-and-replay.md), frozen Research `SB-SRC-0562`. The 18 research-proposed fault vectors in Science remain **original research intentions**, not green implementation tests.

## 1. Engineering boundary and alternatives

**Smallest useful vertical slice:** one caller invokes a public domain collector; each successfully *consumed* raw file can be associated with a bounded observation time, its canonical/source label, the actual byte identity, declared validation outcome, and an optional durable reference; a derived result retains only significant input and method/registry references. The caller can inspect the Result from Python without any Windows-specific package. A content digest means equality of bytes, **not** official authenticity or validated economic truth.

| Variant | Mechanism and cost | Appropriate / rejected claims |
| --- | --- | --- |
| Timestamp and URL only | Lowest CPU/storage overhead | Answers *when/where claimed*, not whether source bytes changed at same URL; insufficient for a byte-identity claim |
| Receipt plus SHA-256 of actually consumed bytes | `O(N)` work and bounded chunk memory; minimal metadata | Proportionate candidate for byte-oriented used inputs; does not guarantee old raw replay |
| Bounded raw retention | `O(N)` additional retained storage per selected edition | Permits future comparison/replay if storage is actually recoverable; requires retention/access/receipt policy |
| Catalog of every official indicator or permanent data lake | Larger governance and source-reconciliation surface | No general need demonstrated for the first Strategy Box collector pilot; remains an opt-in separately justified profile |
| Core method and registry references | Minimal per-run pointer, more exact interpretation history | Specific frozen build and actually used registry bundle; no requirement to write a full essay for every formula |

No separate physical `SourceSnapshot` database table or `RunProvenance` service is required by the semantics. A dataclass/typed Result or a small in-memory record can satisfy the first consumer if verified against real core call sites.

## 2. Proposed transaction-free observation boundary for the *local* pilot

```text
actual source request / local supplied file
 -> outcome + observed_at_utc at the actual acquisition/reading boundary
 -> the exact original bytes used for parsing (do not hash another read)
 -> byte size + digest / explicit uncaptured reason
 -> format-level and domain-level validation, each separately classified
 -> corresponding source identity and reference period if actually known
 -> existing domain result + optional method/registry refs
 -> optional retained bytes and storage confirmation
 -> optional user Artifact publication under its separate authority
```

The low-level transport can observe request/result/byte identity; it cannot decide that a spreadsheet is an authoritative publication of a particular period. The domain validates format and economic scope, while the application (if present) links execution identity and permitted audience. **AppDock's installed package/activation identity is a different concern**. An analyst can use direct `stratbox` from Python or a notebook without a desktop session.

**Atomicity caveat:** an HTTP payload captured in memory or a downloaded file can be valid while persistent receipt write fails; a receipt can exist while raw payload has been removed; a domain result can be correct while the subsequent XLSX save fails. A single `ok` flag cannot collapse these outcomes. No claim of exactly-once remote storage is made for this local slice.

## 3. Proposed per-input states and their evidence

| State/projection | What can actually be asserted | Counterexample |
| --- | --- | --- |
| `ATTEMPTED` | A specific acquisition attempt occurred; time/target and result may be recorded | URL list is not a completed fetch |
| `RESPONSE_RECEIVED` | Bytes/status actually observed; server-owned validator is a hint | HTTP 200 with HTML is not an XLSX |
| `BYTE_FINGERPRINTED` | Digest + size correspond to the bytes handed to the decoder | Stat-before-read hash can race with a replacement |
| `FORMAT_CHECKED` | Declared parser/container conditions satisfied or failed | ZIP bytes valid but bank columns invalid |
| `DOMAIN_VALIDATED` | A *specified* domain check succeeded with named scope | A syntactically valid file may encode wrong figures |
| `RETAINED_CONFIRMED` | Storage backend acknowledged addressable raw bytes under a known retention policy | Lost ACK or later manual deletion can invalidate current replay readiness |
| `RESULT_LINKED` | One computation records its actual used inputs and method context | Source downloaded but not consumed must not be falsely attributed |
| `OUTCOME_UNKNOWN` | Effect may have occurred without adequate receipt | Timeout after remote commit cannot prove non-persistence |

These are **illustrative evidence predicates, not a mandatory one-dimensional persisted enum**. A returned result should preserve independent flags for transport, domain validation, raw availability and replay capability. A missing optional capture must be reported as missing rather than fabricate a source digest.

## 4. Domain realization points — observed versus proposed

| Existing pinned mechanism | Current directly observed behavior | Minimal conditional seam |
| --- | --- | --- |
| `base/net/http.py` | HTTP 200 and minimum bytes yield `DownloadResult` containing content, status, final URL and headers | Attach actual `observed_at` and byte identity where capture policy applies; preserve failures distinctly |
| `cbr_file_collector/downloader.py` | Obvious HTML rejection and source-level failures; downloaded bytes held for save | Join the captured bytes to source ID, actual used URL and original input digest before output packaging |
| `cbr_file_collector/operations.py` | Ensures unique output file names before save | Preserve source→member correspondence; do not claim normal public flow silently drops same-name files |
| `escrow/sources.py` | Source ID suffix is SHA-1 **of URL string** | Distinguish discovered link identity from a later **response-byte** digest |
| `cbr_industries/sources.py` | Recognized filename encodes report-date hint | Capture actual bytes/vintage separately; filename date is not a verified official edition |
| `registries/rosstat_okved2.py` | Default `read()` uses `data` resource alone; `meta`/`structure` separately callable | Pin the resources **actually consumed**; cross-component bundle validation only when that use case requires it |
| `cbr_forms` period runner | Failed download periods can be omitted from result loop | Report expected/received/skipped period evidence before completeness claims |
| Specialized SORS evidence | Typed domain assumption/rounding/model qualifications | Keep existing evidence tiers; no byte digest can elevate weak inferential assumptions |

## 5. Negative and conformance vectors (candidate, zero executed)

| ID | Injection/condition | Required observation for a *future* admitted profile |
| --- | --- | --- |
| PR-01 | Same URL, two distinct byte payloads | Two distinct digests and observed times; no assertion of economic correction |
| PR-02 | Two URLs produce byte-identical payload | Same digest, different locators; no fabricated content revision |
| PR-03 | Same ETag, changed bytes | Client digest detects difference and preserves provider-validator discrepancy |
| PR-04 | Conditional HTTP 304 but cached bytes absent | `INPUT_UNAVAILABLE`, not a fabricated fresh successful payload |
| PR-05 | 200 returns an HTML error page | Failure of source-domain format validation; record observed transport separately |
| PR-06 | A user deletes previously retained raw input | Historical receipt survives; replay currently unavailable |
| PR-07 | File replaced between stat and parser read | Digest corresponds to actual consumed bytes or operation fails consistently |
| PR-08 | Input XLSX unchanged but method/registry edition changes | Distinct compute lineage, no mistaken publisher-byte revision |
| PR-09 | Optional OKVED metadata/structure missing during **data-only** `read()` | Current read path works as its contract allows; full bundle precondition must not be introduced implicitly |
| PR-10 | Multi-resource use combines incompatible editions | Explicit compatibility/uncertainty check under a profile that actually consumes all resources |
| PR-11 | Operation called directly from notebook with no Qt/AppDock | Same provenance semantics available in memory, optional explicit export |
| PR-12 | Source URL contains credential/token | Shared provenance sanitizes public locator; restricted technical traces remain separately governed |
| PR-13 | Storage write ACK lost | `OUTCOME_UNKNOWN` until controlled reconciliation; no invented retained guarantee |
| PR-14 | Two Runs use same acquisition timestamp | Distinct Run and input identity; timestamp not a primary key |
| PR-15 | Output Artifact write fails after successful source processing | Core source receipt and domain result remain distinct from failed file publication |
| PR-16 | Re-evaluate identical SORS bytes under weaker assumption | Same input fingerprint, weaker domain inference evidence preserved |
| PR-17 | Installed wheel changes bundled registry assets without changing semantic operation label | Used registry/build identity explicitly distinguishes revisions |
| PR-18 | A Source is fetched but never passed to computation | Result-level input list excludes unused source; attempted acquisition can remain separate diagnostic |

**Test classification:** PR-01..08, PR-11..12 and PR-14 can be Python-level deterministic fakes without external network; PR-09..10 require fixture resource bundling; PR-13/15 require injected storage faults; PR-16 calls existing specialized domain evidence; PR-17 requires a pinned wheel/build variant. A real official-site integration and expert economic validation remain separate. Every executed record must bind code SHA, test data, Python environment, captured observations and scope.

## 6. Product decisions, audit and implementation stop

This file cannot set compulsory recording on *every* source, raw retention period, public/private provenance visibility, checksum cost budget, source classification policy, R3/R4 replay promise or application owner/host topology. They remain **Product/operational decisions**. The only present Current HOW claims are the exact cited code witnesses; code changes and external provider updates require separate engineering authority. Before a release can claim replay, test what survives process interruption, raw deletion and actual restoration; immutable hash without bytes is not replay.

The relevant [scientific provenance model](../../science/data-and-knowledge/source-observation-vintages-and-replay.md) remains the analytical explanation and record of negative alternatives; this LDD is merely a bounded proposed technical seam for a first core-only consumer. **Author self-check ≠ independent verification.**


## 7. Source-coverage and retry-accounting conformance vectors

[The current core behavior](../../current-how/source-download-receipts-registry-choice-and-coverage-limits.md) is supported by four **executed offline characterization tests**, [CI 38187947796](https://github.com/ForestTiger-GH/stratbox/actions/runs/38187947796). Tests `PR-19..26` below are **different, unexecuted target verification proposals**; they do not certify a redesigned receipt or a real host.

| ID | Injected case | Future admitted consumer requirement |
| --- | --- | --- |
| PR-19 | Empty registry produces current `ok=True`, no saved result | UI does not claim complete official dataset or published output solely from `ok` |
| PR-20 | Three selected sources; first fails, fail-fast | Explicitly show one attempted failure and **two unattempted** identities |
| PR-21 | Two retry rounds generate 16 case-variant network calls | Preserve rounds and physical calls as distinct dimensions where quotas/audit apply |
| PR-22 | Sufficiently long JSON returned HTTP 200 under `.xlsx` name | Format/domain validation independently flags unsupported content |
| PR-23 | Partial downloaded set saved, later source failed | Report selected/attempted/saved/failed/unattempted categories without treating partial as full |
| PR-24 | Cancellation during retries/case variants | Keep authentic Attempt/effect evidence and unknowns, no synthetic full coverage |
| PR-25 | Embedded 41-entry registry changes between runs | Pin actual selected registry/build and actually consumed source IDs per analytical Result |
| PR-26 | Save step fails after valid downloads | Acquisition and Artifact publication retain separate terminal/uncertain statuses |

**No PR-19..26 acceptance tests have been executed.** Source tests deliberately mock external HTTP and saving, and cannot establish current publisher data validity, retention or release security.
