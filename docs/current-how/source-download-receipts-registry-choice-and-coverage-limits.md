# Current HOW — source downloads, registry selection and evidence limits

**Observed implementation:** direct static code reading at `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`; no HTTP request, published archive, live registration comparison, installed wheel or fault-injection suite was run in this investigation. This is a **current implementation evidence sheet**, not a future API requirement, scientific claim of true source contents or certification of every URL/release.

## 1. Byte download currently has a transport-result contract

[`base/net/http.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/net/http.py) implements `download_bytes` with a `DownloadResult` holding `ok`, HTTP `status_code`, downloaded `content`, error, a resolved `final_url` field and headers. The implementation retries on failed HTTP/status/content-size conditions, and returns success when it obtains a response with status 200 and `len(content) >= min_bytes_ok`. The result records the URL passed to the HTTP call after URL-resolution logic; **that field is not itself a validated canonical primary-publication identity or a proof of source authority**.

The current return contract lacks a universal observed-at timestamp, byte digest, source publication/vintage ID, durable raw retention receipt, metadata about parser/registry revisions, or guaranteed reproduction token. At [HTTP L51–L60](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/net/http.py#L51-L60), failure during URL normalization is caught and the original requested URL is used for the subsequent HTTP call. This is a **directly observed fallback branch**: whether it is safe depends on whether normalization is optional convenience or a mandatory policy transformation in the actual deployment. The transport contract alone does not enforce a fail-closed route on normalization error. Any future mandatory egress policy would need an explicit denial/diagnostic choice, not an accidental silent alternative path. No deployment-specific routing behavior is inferred here. Server `ETag`/`Last-Modified` (when present in returned headers) and conditional requests are not established by this generic API as complete source-version semantics.

A full `DownloadResult.ok=True` means a bounded transport validation succeeded. It says nothing about whether the downloaded XLSX/DBF contains valid economic quantities, represents the intended reference date, reports a bank versus group, matches the official publisher's currently announced methodology, or can later be replayed. An HTML response can pass the generic byte length test; downstream domain-specific consumers must enforce file-type/content checks.

## 2. Collector adds source-attempt records and an explicit partial-outcome family

[`macrobanks/cbr_file_collector/downloader.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/downloader.py) wraps the generic downloader and retains `source_id`, requested source URL, used URL variant, final URL, attempted count and (for failures) error/status. It rejects obvious HTML responses, then creates `CbrDownloadedFileSource` with byte `content`, `file_name` and `size_bytes`. The scan at [downloader L98–L153](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/downloader.py#L98-L153) makes each attempt/error explicit.

[`contracts.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/contracts.py) defines `CbrFileCollectFailure` and `CbrFileCollectResult` with `requested_count`, `success_count`, `failure_count`, `failures` and `collected_files`. Its `ok` property means **no failures were recorded for that collection attempt**; it is not a statistical completeness or provenance certificate. The `continue_on_error` request option can intentionally yield a partial collection; consumers must evaluate all counts rather than inferring full coverage from the existence of a target ZIP.

[`operations.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/operations.py) calls `ensure_unique_download_file_names` after retrieval and before save. The function in [`file_names.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/file_names.py) normalizes names, detects collisions case-insensitively and appends numeric suffixes to duplicate names. **An apparent dictionary-key collision in the later ZIP save helper does not by itself prove loss for the normal public `collect_cbr_files` path**: that path explicitly disambiguates names first. The lower-level `save_downloaded_sources` helper itself expects well-formed distinct input names, which a standalone caller must ensure.

## 3. File output does not establish immutable historical source bytes

[`save.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/save.py) supports ZIP and separate-file output through an injected `FileStore`. With `overwrite=False`, an existing ZIP or conflicting member file is rejected. With `overwrite=True`, the destination may be replaced by a later collection under the same path. There is no universal collector-level rule to preserve every historic raw revision under a content digest, and the returned `CbrCollectedFile` contains identifiers, file name, URLs and size rather than a content SHA-256 or source-observed timestamp.

ZIP integrity is not equivalent to independent identity of each downloaded publisher file. Computing the digest of a ZIP written today would not establish the identity of the original members unless their bytes or individual digests are also retained. The producer of an analytical Result would need to connect the exact originally downloaded file/version and applicable parser/model/registry semantics to that result if future replay or historical audit is material.

The distinction is especially important when `overwrite=True` is used for routine source refresh: a successful new run may be useful operationally while the bytes used by a historic report are no longer locally available.

## 4. The packaged registry “latest” selection is based on filesystem mtime

[`registries/_loader.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/_loader.py) exposes `pick_latest_by_suffix` and `pick_latest_by_prefix`. Both enumerate matching files in package resources and select `max(matches, key=_resource_mtime)`. The helper calls a resource `stat().st_mtime` and returns **`0.0`** when stat is unavailable. The candidate file name, selected path and kind are returned; there is no assertion that mtime represents an official publisher release version.

Consequences bounded by the actual code:
- wheel packaging/copying can change filesystem mtime without changing the underlying official source revision;
- multiple candidates may tie at `0.0`; the resulting first maximum follows enumeration order and lacks a semantic release-order guarantee;
- a file with newer local mtime can still contain older official registry content;
- selecting the same resource name across installations does not alone establish byte equality.

The correct current-state wording is therefore **“latest by local resource mtime”**, not “latest official publication”. A future versioned registry can store publisher edition, effective date, digest and exact chosen file set separately, but those are target proposals requiring product admission.

[`registries/rosstat_okved2.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/rosstat_okved2.py) obtains component resources for code tables, metadata and structure separately. When material, one calculation must qualify whether the chosen `data/meta/structure` combination is truly a coherent release; successful reading of all three pieces is not a guarantee they were published as one edition. This is a **potential semantic coherence requirement**, not an established observed mismatch in current resources.

## 5. Bank forms have a different, concrete missing-period behavior

The current direct banking-form runner [`cbr_forms/common/runner.py` L91–L124](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/common/runner.py#L91-L124) loops requested periods and fetches a RAR archive. For `not res.ok or not res.content`, lines 105–106 execute `continue`: no row is appended for that date, and only the final number of processed DBF dates is printed. Its `run_all_forms_to_xlsx` caller in [`cbr_forms/api.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_forms/api.py) has no generic documented receipt guaranteeing that every expected scheduled reporting period either succeeded or is classified with a typed reason.

This runner differs from the source collector above: the collector holds per-source failures, while the forms runner **does not return a date-specific download-failure record through this list-returning function**. Thus it would be wrong to infer uniform source coverage guarantees from a common HTTP helper or from a well-formed Excel export.

## 6. Direct test evidence: which behavior is checked, which is not

The pinned repository includes unit tests for domain-specific bank-form behavior:
- [`test_form802.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/tests/unit/macrobanks/cbr_forms/test_form802.py) checks 86 source-model rows, numeric code normalization, blank versus zero, an official-snapshot fixture and duplicate physical source keys;
- [`test_excel_profiles.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/tests/unit/macrobanks/cbr_forms/test_excel_profiles.py) checks quarterly form-802 scheduling, 3-sheet hierarchy, canonical keys and a written XLSX;
- [`test_models.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/tests/unit/macrobanks/cbr_forms/test_models.py) checks model schema, unique IDs/order, required direct/formula/passthrough fields and existing indicator sets;
- [`test_optional_dbf_fields.py`](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/tests/unit/macrobanks/cbr_forms/test_optional_dbf_fields.py) checks optional `KORR_GR`/other correction-field handling and provides fakes for DBF/runner input.

This is **static inspection of assertions**, not proof of a successful contemporary pytest run. These cases do **not** constitute a negative-case system test that fetches three expected dates, fails on the middle date and verifies an explicit user-visible missing-period receipt. No such full end-to-end test was established in the directly reviewed form-test subset.

## 7. Concrete falsifying cases and scope of future correction

| Case | Observed code contract / missing guarantee | Future measurable requirement, only if admitted |
| --- | --- | --- |
| Same URL publishes changed XLSX bytes | Source URL is not content identity; generic result has no digest | Save observed-at, exact digest, source identity and optional raw bytes for material UsedSources |
| New wheel repacks historical registry files | mtime may pick a different “latest” | Pin coherent official `RegistrySnapshot` identity rather than package copy time |
| Source A/B yield same filename | Public collector runs case-insensitive uniquification first | Preserve disambiguation and source-to-member correspondence under all save modes |
| Download succeeds but response is HTML | Collector rejects obvious HTML; generic HTTP only checks transport/size | Domain content/schema validation with typed status and redacted diagnostics |
| One required banking form period cannot download | Forms runner silently skips date in returned list | Distinct `not_due`, `unavailable`, `failed`, `no_rows`, `zero` and `complete` coverage outcomes |
| ZIP overwritten after producing prior report | Saved path alone cannot replay original bytes | Source-byte manifest and selective durable retention where needed for historical reliance |
| Registry data/meta/structure version mismatch | Reading components does not certify one release | Explicit version compatibility and reprocessing impact test |
| Network/transport ok but economic content wrong | Transport receipt is not domain validity evidence | Independent semantic model/source reconciliation by accountable domain owner |

A very large global registry of every published statistical value is not implied. The bounded research direction prioritizes a **lightweight receipt for actually used files**, user-visible fact of observed download time, honest raw-retention/replay level and optional existing methodology pointer. This is a user-goal hypothesis preserved from the dated source study [09](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/09_Источники_данных_версии_и_воспроизводимость_Strategy_Box_2026-10-10.md), not an assertion that the API has been implemented.

**Current evidence boundary:** all implementation facts above are from direct pinned code. The test descriptions are from source tests without execution. “Need receipt”, “should preserve byte hash” and “formal registry edition” remain target proposals. Reopen on changed source bytes, regulator publication corrections, installed-wheel package behavior, a verified live fault case or authorized product-scoped data provenance requirements.
