# Core 0.27: operating scope and verification

This article records the implemented core operating model and the local
qualification of version 0.27.0 on 27 November 2026. The scope is finite SDK
execution and an explicitly maintained, single-coordinator persistent profile.
Application packaging and platform-specific adapters require their own
qualification.

The common contract joins accepted outputs, exact historical evidence, physical
work generations, qualified effect receipts and durable recovery. Scientific
readiness remains attached to the selected domain binding and actual input.
The measurements below describe their stated fixtures and reference environment;
they establish no universal throughput or memory guarantee.

## Contents

1. Implemented contracts — the guarantees shared by direct and composed calls.
2. Verification boundaries — behavioral, interruption and release checks.
3. Sustained persistent operation — explicit retention across changing sources.
4. Large physical carriers — bounded streaming through the ZIP64 route.
5. Owned-value execution — isolation, descriptors and control progress.
6. Supported operation and remaining qualifications — host duties and scope.
7. Reproducing the checks — local commands and direct implementation evidence.

## 1. Implemented contracts

The five package owners remain `capabilities`, `core`, `domains`, `shared` and
`sdk`. Environment-specific storage and transports bind through provider
contracts. The public SDK uses the same preparation, admission and execution
semantics as nested standard compositions.

| Code | Contract | Observable behavior |
| --- | --- | --- |
| OC01 | Accepted output and selected obligations | Reported diagnostics preserve their producer outcome and origin. Collection counts eligible declared members and applies an explicit `all_selected`, `eligible_subset` or `diagnostic` policy. |
| OC02 | Exact historical candidates | Revision, publication occurrence, provenance and witness relations survive selection and portable persistence. A resolved view can be changed without reconstructing discarded evidence. |
| OC03 | Effect evidence and fulfillment | Provider replies pass one evidence-admission model. Destination identity, aliases, preconditions and outcome must agree before confirmation. Historical confirmation and current artifact availability remain separate facts. |
| OC04 | Physical work and graph admission | Live consumers attach to an exact physical generation. Retained completed results do not extend later deadlines. Recursive graph validation precedes root admission and dynamic expansion. |
| OC05 | Private owned values | Admission isolates supported mutable payloads, seals identity/accounting descriptors and creates private worker copies. Expensive payload traversal belongs outside coordinator transitions. |
| OC06 | Persistent operation | Bounded projection maintenance, durable receipt reservations, explicit backup cuts and exclusive recovery transfer support one local coordinator. Preflight reports the actual selected binding and provider limitations. |

No compatibility conversion invents historical candidates or scientific witness
authority. A persisted representation missing required evidence is rejected at
the owning boundary. A downstream derived value can preserve an existing
certificate dependency without creating new certificate authority.

## 2. Verification boundaries

Focused regression groups cover output laundering through wrappers and maps,
collection obligations, reversible history views, scoped effect evidence, actual
304 destination fulfillment, durable read-through, recursive graph rejection,
generation cancellation and mutable-value isolation. Cross-owner checks cover
source-state transactionality, archive visibility, explicit current-basis
retirement, receipt reservations and corruption rejection.

Interruption checks kill real child processes while holding storage locks and at
selected effect boundaries. They inspect actual provider mutation counts and
durable receipts after restart. These tests qualify process interruption within
the tested local provider model. They do not simulate a machine losing power.

Recovery verifies the package and original provider scopes before transferring
the journal writer. A valid older backup cannot authorize a duplicate writer or
reuse sequence numbers already present in a surviving authoritative suffix.
Restored historical effect namespaces remain closed to fresh claims, including
identities absent from the backup.

The final collected scope contains 1,623 test cases. The general sweep and final
affected reruns establish 1,616 passing current cases and seven explicit skips,
with overlapping test identities counted once. Every failure found in the
general sweep has a successful corresponding final rerun. This is reconciled
coverage across the local verification passes, rather than a claim that the
first exploratory sweep passed unchanged.

| Code | Verification | Recorded result |
| --- | --- | --- |
| VR01 | General sweep, excluding the separately developing recovery partition | 1,545 passed, seven skipped and ten integration failures identified in 884.35 seconds; all ten closed in affected reruns. |
| VR02 | Final affected capability, core, SDK, integration and selected scientific scope | 830 current cases covered; 829 passed directly and one encountered temporary-volume exhaustion during an overlapping large fixture. The entire 20-case boundary file then passed after the physical fixture moved to its qualified volume. |
| VR03 | Recovery/profile/export qualification | All 47 cases passed, including ten independent notification-recovery cases; these overlap VR02. |
| VR04 | Final current test identity reconciliation | 1,616 passing cases, seven skipped and zero unverified or still-failing current cases. |
| VR05 | Structural and distribution gate | Import ownership, release integrity, maintained navigation, source/wheel build, both archive inspections, local installation and isolated installed/zip SDK imports all passed. |

The seven skips cover the opt-in real SORS snapshot, multiscope and performance
fixtures. Their external data directory and performance opt-in were absent.
Synthetic and bounded strict-solver routes were exercised; the skipped real-data
gates remain a separate qualification requirement.

The local release check built the source archive and wheel, verified 524 archive
members and 22 packaged reference resources, then exercised SDK discovery from
an installed directory and directly from the wheel. These checks use local
execution; no remote workflow is part of this qualification.

## 3. Sustained persistent operation

The reference environment was CPython 3.12.14, SQLite 3.53.1 and Linux
6.18.57 x86-64 with glibc 2.41. The probe used ordinary SDK acquisition commands
through a controlled offline provider, 4,096-byte publications and bounded
maintenance pages. Sixty cycles retained unchanged source content and sixty
changed the publication. The host explicitly selected obsolete accepted IDs for
retirement.

| Code | Observed quantity | Result |
| --- | --- | --- |
| PO01 | Completed acquisition cycles | 120; 61 responses with status 200 and 59 with status 304. |
| PO02 | Maintenance and cursor verification | 121 bounded calls/checks; page limit 32 and at most 16 pages per call. |
| PO03 | Deliberate retirement | 61 current bases retired; 190 projection records archived and 238 discarded. |
| PO04 | Journal horizon | 13 pruning requests; final journal tail and projection watermark both 1,261; retained journal floor 1,248. |
| PO05 | Maximum logical hot projection | Six records and 11,122 bytes. |
| PO06 | Maximum logical cold projection | Thirteen records and 22,335 bytes. |
| PO07 | Final projection | Three hot records, 5,491 hot bytes and zero cold records. |
| PO08 | Effect receipt lifetime | At most one hot receipt; 61 confirmed receipts retained in cold storage. |
| PO09 | Physical profile footprint | Maximum observed profile directory 5,102,105 bytes; source-state files 4,435,880 bytes. |
| PO10 | Recovery package | 131 files, 1,043,386 bytes and 62 exact dependency bindings sharing 249,856 physical content bytes. |
| PO11 | Restart and restore | One cold profile reopen; all eleven integrity/recovery checks passed. |
| PO12 | Elapsed probe time | 6.0893 seconds; export/verification 0.1329 seconds and restore/verification 0.3231 seconds. |

The small logical hot/cold maxima result from explicit host retirement and page
maintenance. They are not an automatic retention policy for every analytical
workload. Cold effect receipts and retained artifact bytes still occupy storage.
Physical database, WAL and filesystem sizes differ from logical record-accounting
sizes and must be monitored separately.

The probe verified exact restored projection and limits, original artifact
availability, a confirmed receipt, closed prior occurrence authority and the old
journal writer fence. Scientific interpretation, arbitrary notification
transports and remote storage remain outside this fixture's scope.

## 4. Large physical carriers

The physical probe streamed a generated source through `material.read`,
`archive.pack`, `artifact.commit`, `release.assemble` and
`artifact.reconcile`. Every stage succeeded for both 1 GiB and 5 GiB inputs.
The archive used stored members; the 5 GiB exercise used ZIP64 representation.

| Code | Quantity | 1 GiB input | 5 GiB input |
| --- | --- | --- | --- |
| PC01 | Source bytes | 1,073,741,824 | 5,368,709,120 |
| PC02 | Retained archive bytes | 1,073,741,962 | 5,368,709,354 |
| PC03 | Total elapsed seconds | 10.5626 | 47.0953 |
| PC04 | Peak process RSS bytes | 36,020,224 | 35,749,888 |
| PC05 | Peak RSS increase bytes | 14,528,512 | 14,258,176 |
| PC06 | Largest provider read/write chunk | 1,048,576 bytes | 1,048,576 bytes |
| PC07 | Cumulative provider bytes read | 5,368,709,672 | 26,843,546,536 |
| PC08 | Configured retained RAM budget | 2,097,152 bytes | 2,097,152 bytes |

The retained RAM budget accounts for managed retained resources; it is not a
process-wide memory ceiling. The interpreter, libraries and transient buffers
contribute to process RSS. Reverification at several boundaries explains why
cumulative bytes read exceed the original input. Those reads are bounded streams,
not simultaneous in-memory copies of the full carrier.

These results qualify the measured physical route and archive mode. They make no
claim that an arbitrary multi-gigabyte spreadsheet decoder, table conversion,
scientific calculation or compressed archive fits the same envelope.

## 5. Owned-value execution

The owned-value registry binds private storage to exact identity, normalized
processing identity, retained resident accounting and reachable resource claims.
Logical outputs can reuse those descriptors without a full payload scan during
status inspection or result attachment. Result closure releases the relevant
ownership; a downstream admitted consumer retains its own required ownership.

Mutable dictionaries, mapping keys, supported arrays, sequences and native table
payloads require isolation at their actual ingress and worker boundary.
Unsupported mutable native shapes fail explicitly. A caller-supplied digest or
descriptor does not certify an unowned mutable object. Regression cases mutate
the caller's and worker's values and inspect the independently retained result.

The matched execution probe used the same offline `debt_0105a` fixture and
`operation.series.extract_workbook` route against the earlier 0.26 implementation
and the 0.27 implementation. Its six-sheet workbook contained 15,720 physical
cells and produced 14,976 observations. The baseline came from an isolated copy
of the earlier source; neither measurement invoked a publisher network endpoint.

| Code | Observed quantity | 0.26 baseline | 0.27 measured run |
| --- | --- | --- | --- |
| VE01 | Preparation | 0.4123 seconds | 0.4966 seconds |
| VE02 | Execution including admission | 43.6713 seconds | 34.1214 seconds |
| VE03 | Private result-reader copy | 4.1961 seconds | 3.9408 seconds |
| VE04 | Eight independent command samples during extraction | 5.6 milliseconds to 12.7907 seconds | 7.2 to 40.2 milliseconds |
| VE05 | Scientific identity traversals on coordinator | Ten dataset, six table-evidence and six workbook-evidence traversals | Zero |
| VE06 | Scientific payload copies on coordinator | Two dataset, one table-evidence and one workbook-evidence copy | Zero |
| VE07 | Scientific identity traversals on workers | One observed dataset traversal | Two dataset, one table-evidence and two workbook-evidence traversals |
| VE08 | Additional payload traversals from 100 status polls | Zero | Zero |

The measured extraction time decreased by about 21.9% in this pair. More
significantly for control progress, every instrumented scientific identity and
copy operation moved off the coordinator, and the eight independent requests
completed promptly during the extraction. These are finite samples from a shared
Linux environment, not latency percentiles or a portable service-level promise.

The after run observed 31,988,369 managed resident bytes and 9,188,998 working-copy
bytes at sampled peaks. These registry counters are separate from process RSS.
The earlier implementation exposed no equivalent counters, so the probe's absent
baseline measurement cannot be interpreted as zero memory use. The after run
recorded 73 actual exact-identity computations for 130 newly sealed registry
entries; structural bundle entries reuse constituent descriptors. The
result-reader copy remains a real, separately measured cost of providing a
private mutable value to the caller.

A different complete retained/replayed multistage debt route passed in 111.99
seconds. It covers a larger sequence of stage, persistence and restoration
operations and is not the baseline for the single-extraction comparison above.

## 6. Supported operation and remaining qualifications

An application can use finite `StrategyBox` sessions or the built-in
`LocalProfile` for one explicitly maintained local owner. The host chooses the
source set, polling cadence, result lifetime, archive horizon, protected
obligations and reaction to unresolved effects. The core starts no hidden polling
loop and selects no business retention preference on the host's behalf.

| Code | Boundary | Current qualification |
| --- | --- | --- |
| QB01 | Scientific meaning | Each selected method must admit its actual publication, period, perimeter, unit and required operands. Declared missing models block execution even if their method locator resolves. |
| QB02 | Local ownership | Cooperative OS-held anchors and the single journal writer are tested. Separate selected providers can support their advertised atomic shared access. |
| QB03 | Restoration | Original journal exclusion, exact surviving evidence and original artifact scopes are required. A lost host or arbitrary provider relocation needs a separately qualified procedure. |
| QB04 | Storage failure | Explicit capacity, unknown effects and interruption recovery are covered by their tests. Power loss, hostile external writers and network filesystems require additional evidence. |
| QB05 | Capacity planning | Configure reservations for actual concurrency and receipt sizes, monitor physical bytes, and run bounded maintenance before admission headroom is exhausted. |
| QB06 | Application platforms | Desktop and future mobile adaptation, packaging and lifecycle belong to their application owners. This core release establishes their common contracts. |

## 7. Reproducing the checks

Run the contract suite and structural gates locally from the repository root:

```sh
python scripts/check_release_integrity.py
python scripts/check_internal_imports.py
python scripts/check_readme_links.py
python -m pytest -q -ra
python scripts/local_release_check.py --skip-pytest --report /tmp/stratbox-release.json
```

The physical probe and sustained-profile probe expose their workload parameters
through `--help`. They create finite temporary workloads and report measurements
separately from the ordinary correctness suite. Preserve environment, selected
limits and fixture dimensions when comparing measurements.

```sh
python scripts/probe_physical_streaming.py --size-mib 5120 --root .
python scripts/probe_persistent_profile.py --cycles 120
python scripts/probe_owned_values.py --fixture /tmp/stratbox-owned-fixture.xlsx --output /tmp/stratbox-owned-current.json
```

The owned-value probe accepts `--repo` for an independently checked-out source
snapshot. Supply the same `--fixture` file to each comparison run so workbook
bytes and geometry are identical. Its instrumentation counts the three stated
scientific carrier types, rather than every scalar identity operation.

Choose an existing physical-probe root with room for simultaneously live source,
stage and retained copies. The 5 GiB exercise used the local 20 GiB workspace
volume and required more than 10 GiB of free working storage. A small system
temporary filesystem is insufficient for that fixture even though the measured
process RSS is small.

Direct verification owners are the current `tests/core_target`,
`tests/sdk_target`, `tests/integration/standard_routes` and probe scripts in
`scripts`. Their assertions and measured scope determine what a green result
establishes; a catalog entry alone establishes no scientific qualification.

See [persistent operation and recovery](persistent-operating-profile.md),
[effect evidence and recovery](effect-recovery-and-stage-events.md),
[selective processing and histories](selective-processing-and-restart.md) and
[domain scientific coverage](independent-domain-data-routes.md).
