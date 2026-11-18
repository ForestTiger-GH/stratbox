# Shared identity, evidence, statistical data and calendar contracts

**Current implementation scope:** `stratbox.shared` exposes independent foundational contracts usable offline and without installing dataframe libraries. Source validation and business interpretation remain in the calling domain.

## Navigation

1. Canonical byte and evidence types — stable input identity.
2. Statistical and computation types — observation and release semantics.
3. Reference access — explicit package editions.
4. Calendar grids — date-only anchors.
5. Failure and reproducibility limits — meaningful distinctions.

## 1. Canonical byte and evidence types

```python
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt

payload = SourcePayload(b"example", media_type="text/plain", source_id="example.data")
receipt = UsedInputReceipt.for_payload(payload, role="source")
assert receipt.identity == ByteIdentity.of(payload.data)
assert canonical_manifest_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
```

The source payload's digest describes exact material. An acquisition receipt and a storage receipt each add separate observable claims; digest equality alone cannot verify publisher origin or durable storage effects. A `UsedInputReceipt.version` may bind an input to a reference edition's semantic snapshot.

## 2. Statistical and computation types

`shared.data.observations` defines `SubjectRef`, `MetricRef`, `PeriodRef`, `Observation` and `ObservationBatch`. Value statuses distinguish reported, derived, reconstructed, withheld and missing observations. A missing observation and an observed zero are different facts.

`shared.data.datasets` owns `DatasetVersion`, `build_dataset_version`, `computation_identity` and `ComputationReceipt`. The dataset manifest includes method, inputs and resources; the computation manifest additionally binds operation contract, source identity and optional representation choices. Table serialization in `shared.data.tables` preserves schema, dtype, ordered rows and typed scalar values. `shared.data.releases` builds literal/qualified release representations, while `shared.data.comparison` distinguishes source, fact and method differences.

## 3. Reference access

```python
from stratbox.shared.reference.assets import load_reference

edition = load_reference("stratbox.shared.reference.okved2")
inputs = []
bytes_data = edition.read("data", inputs=inputs)
assert inputs[0].version == edition.snapshot_identity
```

Access is offline and constrained to the manifest's declared paths. Invalid digest, missing required file, unknown edition or malformed manifest fails explicitly. An official publication date is nullable and cannot be deduced from the filename. All reference asset roles have distinct identifiers even if two assets have matching content.

## 4. Calendar grids

```python
from stratbox.shared.time.periods import period_points

month_end = period_points("M", "2024-01-01", "2024-03-31", anchor="end")
```

`PeriodSpec`, `period_points` and `period_spec_points` use standard Python calendar dates. Year, quarter, month, ISO week and daily anchors can be selected, with an explicit positive step. The interval filters anchor dates, rather than treating every overlapping period as part of the result. For reproducibility, callers pass `date_to` rather than relying on the local current date.

## 5. Failure and reproducibility limits

Importing these fundamental contracts does not acquire network data or read the bank workbook. The existence of an identity is distinct from a content qualification; a dataset calculation result is distinct from the representation bytes; and a source-specific code is distinct from a shared territorial ID. Rewriting Python imports alone should not change `operation_id`, numerical results or effect states. The public library does not retain old shared import aliases.
