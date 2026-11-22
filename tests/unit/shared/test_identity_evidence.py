"""Identity and material lineage contracts must retain their exact semantics."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import importlib.util
import json

import pytest

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt, AcquiredSource, AcquisitionReceipt
from stratbox.shared.data.datasets import build_dataset_version, computation_identity
from stratbox.shared.data.observations import SubjectRef, MetricRef, PeriodRef, Observation, ObservationBatch
from stratbox.shared.data.representation import Representation


def test_canonical_bytes_deterministic_and_timezone_aware():
    left = canonical_manifest_bytes({"b": Decimal("1.20"), "a": date(2024, 2, 29)})
    right = canonical_manifest_bytes({"a": date(2024, 2, 29), "b": Decimal("1.20")})
    assert left == right
    assert json.loads(left) == {"a": "2024-02-29", "b": "1.20"}
    with pytest.raises(ValueError, match="timezone"):
        canonical_manifest_bytes({"at": datetime(2026, 1, 1)})
    with pytest.raises(TypeError):
        canonical_manifest_bytes({"invalid": object()})


def test_byte_identity_and_source_receipt_do_not_disagree():
    payload = SourcePayload(b"example", "text/csv", "source:fixture")
    assert payload.identity == ByteIdentity.of(b"example")
    assert payload.identity.size == len(payload.data)
    with pytest.raises(ValueError, match="digest"):
        SourcePayload(b"example", expected_sha256="0" * 64)
    receipt = AcquisitionReceipt("source:fixture", payload.identity,
                                 datetime(2026, 11, 18, tzinfo=timezone.utc),
                                 payload.media_type, 200, "test://source")
    assert AcquiredSource(payload, receipt).payload is payload
    with pytest.raises(ValueError, match="disagrees"):
        AcquiredSource(SourcePayload(b"modified", "text/csv", "source:fixture"), receipt)


@pytest.mark.parametrize("size", [False, True, 1.0, 1.5])
def test_byte_identity_size_is_an_exact_integer(size):
    with pytest.raises(ValueError, match="Invalid byte identity"):
        ByteIdentity("0" * 64, size)


def test_dataset_and_computation_identity_are_resource_sensitive():
    source = SourcePayload(b"123", "text/plain", "source:fixture")
    used = (UsedInputReceipt.for_payload(source, "source"),)
    version = build_dataset_version("example.dataset", "2026-11-18", "method.v1",
                                    used, ByteIdentity.of(b"output"), resources={"dictionary": "A"})
    changed = build_dataset_version("example.dataset", "2026-11-18", "method.v1",
                                    used, ByteIdentity.of(b"output"), resources={"dictionary": "B"})
    assert version.identity != changed.identity
    assert computation_identity("example.read", 1, "v1", used, resources={"reference": "A"}) != (
        computation_identity("example.read", 1, "v1", used, resources={"reference": "B"})
    )


def test_observation_period_and_missing_value_are_distinct():
    period = PeriodRef("interval", start=date(2026, 1, 1), end=date(2026, 3, 31))
    assert period.kind == "interval"
    assert Observation(SubjectRef("test", "A"), MetricRef("stock", "RUB"), period, (),
                       "publisher", Decimal(0), "reported", "proof").value == 0
    with pytest.raises(ValueError):
        Observation(SubjectRef("test", "A"), MetricRef("stock", "RUB"), period, (),
                    "publisher", None, "reported", "proof")
    with pytest.raises(ValueError):
        PeriodRef("interval", start=date(2026, 3, 31), end=date(2026, 1, 1))


def test_obsolete_owner_paths_are_removed():
    assert importlib.util.find_spec("stratbox.shared.registries") is None
    assert importlib.util.find_spec("stratbox.shared.text") is None
    assert importlib.util.find_spec("stratbox.shared.data.identity") is None
    assert importlib.util.find_spec("stratbox.shared.data.evidence") is None
    assert ByteIdentity.__module__ == "stratbox.shared.identity"
    assert UsedInputReceipt.__module__ == "stratbox.shared.evidence"


def test_observation_statuses_reject_unrecognized_values_and_bool():
    from stratbox.shared.data.observations import (
        SubjectRef, MetricRef, PeriodRef, Observation,
    )
    subject = SubjectRef("fixture", "x")
    metric = MetricRef("metric", "count")
    period = PeriodRef("as_of", as_of=date(2026, 11, 18))
    def fact(value, status):
        return Observation(subject, metric, period, (), "scope", value, status, "source")
    for status in ("missing", "blank", "dash", "not_applicable", "withheld"):
        assert fact(None, status).value is None
    for status in ("reported", "derived", "reconstructed"):
        assert fact(0, status).value == 0
    with pytest.raises(ValueError, match="Unknown"):
        fact(None, "silent_error")
    with pytest.raises(TypeError, match="value"):
        fact(True, "reported")
    with pytest.raises(TypeError, match="value"):
        fact(1.5, "reported")
    with pytest.raises(ValueError):
        fact(None, "reported")
    with pytest.raises(ValueError):
        fact(0, "missing")


def test_manifest_canonical_bytes_match_independent_golden_vector():
    from hashlib import sha256
    payload = {"b": Decimal("1.20"), "a": date(2024, 2, 29)}
    encoded = canonical_manifest_bytes(payload)
    assert encoded == b'{"a":"2024-02-29","b":"1.20"}'
    assert sha256(encoded).hexdigest() == (
        "d0dbabdc74a9c9f617dbdebbd160c4719d5ebaf8bb1856e5616e7428ca710332"
    )


def test_dataset_content_projection_and_computation_origin_are_distinct():
    left = UsedInputReceipt.for_payload(
        SourcePayload(b"same", "text/csv", "publisher:A"), "source"
    )
    right = UsedInputReceipt.for_payload(
        SourcePayload(b"same", "text/csv", "publisher:B"), "source"
    )
    result = ByteIdentity.of(b"result")
    a = build_dataset_version("fixture", "2026-11-18", "method-1", (left,), result)
    b = build_dataset_version("fixture", "2026-11-18", "method-1", (right,), result)
    assert a.identity == b.identity  # Dataset projection is byte/method-oriented.
    assert computation_identity("fixture.parse", 1, "method-1", (left,)) != (
        computation_identity("fixture.parse", 1, "method-1", (right,))
    )  # Execution identity includes source_id.


def test_release_facts_are_order_invariant_but_preserve_status_difference():
    from stratbox.shared.data.releases import build_release
    from stratbox.shared.data.observations import (
        Observation, SubjectRef, MetricRef, PeriodRef,
    )
    subject = SubjectRef("fixture", "A")
    metric = MetricRef("balance", "RUB")
    period = PeriodRef("as_of", as_of=date(2026, 11, 18))
    def obs(name, value, status):
        return Observation(subject, metric, period, (("type", name),),
                           "fixture", value, status, "fixture:1")
    a = obs("one", 0, "reported")
    b = obs("two", None, "missing")
    def build(values):
        return build_release("fixture", "profile", "method",
                             date(2026, 11, 18), b"test", len(values),
                             (), observations=values)
    assert build((a, b)).facts_identity == build((b, a)).facts_identity
    assert build((a, b)).facts_identity != build((a, obs("two", None, "withheld"))).facts_identity
