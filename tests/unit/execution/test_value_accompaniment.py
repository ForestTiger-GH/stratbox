"""One accounting contract applies to inline, retained and collection values."""
from dataclasses import dataclass, replace
from datetime import date, timezone
from decimal import Decimal
from types import SimpleNamespace
import pytest

from stratbox.core.execution import values
from stratbox.core.limits import BudgetMeter, ExecutionBudget
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.evidence import SourcePayload


def batch(number=1):
    item = Observation(SubjectRef("fixture", "one"), MetricRef("count", "count"),
        PeriodRef("as_of", date(2026, 11, 23)), (), "fixture", Decimal(number), "reported", "proof")
    return ObservationBatch("fixture.batch", 1, "capture", (item,), ())


class Invocation:
    def __init__(self):
        self.budget = BudgetMeter(ExecutionBudget())
        self.receipts = []
        self.recorded = None

    def check_cancelled(self):
        self.budget.checkpoint()

    def use(self, receipt):
        self.receipts.append(receipt)

    def account_output(self, identity, *, key="returned"):
        self.budget.account_output(key, identity)

    def record(self, identity, **options):
        self.recorded = (identity, options)
        return self.recorded


def test_collection_evidence_preserves_each_position_and_resource_obligation():
    payload = SourcePayload(b"same bytes", "text/plain", "fixture")
    invocation = Invocation()
    values.use_value((payload, payload), invocation, "sources")
    assert [item.role for item in invocation.receipts] == ["sources.0", "sources.1"]
    assert invocation.budget.used("input_bytes") == 2 * payload.identity.size
    assert values.value_identity((payload,)) != values.value_identity((payload, payload))
    changed = SourcePayload(b"other bytes", "text/plain", "fixture")
    assert values.value_identity((payload, changed)) != values.value_identity((changed, payload))


def test_snapshot_adapter_is_cached_and_accounts_every_component():
    value = batch()
    snapshot = observation_snapshot(value)
    calls = []

    def adapter(item, invocation):
        calls.append(item)
        return snapshot

    invocation = Invocation()
    values.use_value(value, invocation, "batch", snapshot_factory=adapter)
    values.record_value(value, SimpleNamespace(format="csv"),
        SimpleNamespace(processing=SimpleNamespace(parameters=("format",))),
        invocation, snapshot_factory=adapter)
    assert calls == [value]
    assert invocation.budget.used("input_bytes") == values.snapshot_size(snapshot)
    assert invocation.budget.used("output_bytes") == values.snapshot_size(snapshot)
    assert invocation.budget.used("cells") == 2 * values.snapshot_cells(snapshot)
    assert invocation.recorded[0] == snapshot.identity
    assert invocation.recorded[1]["parameters"] == {"format": "csv"}


def test_observation_identity_tracks_content_and_survives_snapshot_roundtrip():
    from stratbox.shared.data.observation_snapshots import observations_from_snapshot
    value = batch()
    retained = observations_from_snapshot(observation_snapshot(value))
    assert values.value_identity(value) == values.value_identity(retained)
    assert values.value_identity(value) != values.value_identity(batch(2))


def test_control_values_preserve_decimal_literal_without_fixed_point_expansion():
    assert values.plain(Decimal("1e999999")) == {"type": "decimal", "literal": "1E+999999"}
    assert values.plain({"ids": frozenset({"b", "a"})}) == {"ids": ["a", "b"]}


def test_timezone_controls_preserve_named_zone_and_fixed_offset_semantics():
    from zoneinfo import ZoneInfo
    assert values.plain(timezone.utc) == {"type": "timezone", "offset_seconds": 0, "name": "UTC"}
    assert values.plain(ZoneInfo("Europe/Helsinki")) == {"type": "timezone", "key": "Europe/Helsinki"}


def test_dataframe_arguments_retain_dtype_order_missing_values_and_attributes():
    pd = pytest.importorskip("pandas")
    frame = pd.DataFrame({"count": pd.array([1, None], dtype="Int64"), "name": ["a", "b"]})
    identity = values.argument_identity(frame)
    assert identity == values.argument_identity(frame.copy(deep=True))
    assert identity != values.argument_identity(frame.iloc[::-1])
    assert identity != values.argument_identity(frame.astype({"count": "Float64"}))
    assert identity != values.argument_identity(frame.fillna({"count": 0}))
    frame.attrs["meaning"] = "independent source"
    assert identity != values.argument_identity(frame)


def test_semantic_dataclass_arguments_exclude_typed_computation_ancestry():
    from stratbox.shared.data.datasets import ComputationReceipt, build_dataset_version
    from stratbox.shared.identity import ByteIdentity
    from stratbox.shared.evidence import UsedInputReceipt

    @dataclass
    class Value:
        amount: Decimal
        evidence: ComputationReceipt | None = None
        lineage: tuple[UsedInputReceipt, ...] = ()

    output = ByteIdentity.of(b"output")
    version = build_dataset_version("fixture", "capture", "method", (), output)
    receipt = ComputationReceipt(version, output, (), output)
    value = Value(Decimal("1.00"))
    traced = replace(value, evidence=receipt,
        lineage=(UsedInputReceipt.for_payload(SourcePayload(b"source"), "source"),))
    assert values.argument_identity(value) == values.argument_identity(traced)
    assert values.argument_identity(value) != values.argument_identity(replace(value, amount=Decimal("2.00")))

    @dataclass
    class Mixed:
        pair: tuple[str, ComputationReceipt | None]
        content: Decimal | ComputationReceipt

    mixed = Mixed(("first", None), Decimal("1.00"))
    assert values.argument_identity(mixed) == values.argument_identity(replace(mixed, pair=("first", receipt)))
    assert values.argument_identity(mixed) != values.argument_identity(replace(mixed, pair=("second", receipt)))
    assert values.argument_identity(mixed) != values.argument_identity(replace(mixed, content=Decimal("2.00")))

    from stratbox.shared.materials import MaterialArtifact
    from stratbox.shared.data.processing import DataContract
    from stratbox.shared.data.representation import Representation
    artifact = MaterialArtifact(DataContract("fixture"), Representation("fixture", 1, "text/plain", b"output"))
    assert values.argument_identity(artifact) == values.argument_identity(replace(artifact, computation=receipt))


def test_numpy_and_pandas_scalar_controls_preserve_missing_and_submicrosecond_values():
    pd = pytest.importorskip("pandas")
    np = pytest.importorskip("numpy")
    assert values.plain(pd.NA) != values.plain(pd.NaT)
    assert values.plain(pd.Timedelta(1, unit="ns")) != values.plain(pd.Timedelta(0))
    assert values.plain(np.int64(1))["value"] == 1
    assert values.plain(np.array([[1, 2], [3, 4]]))["shape"] == [2, 2]
