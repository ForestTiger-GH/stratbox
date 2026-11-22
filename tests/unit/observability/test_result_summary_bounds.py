"""Large operation envelopes produce bounded, truthful portable observations."""
from datetime import datetime, timezone

import pytest

from stratbox.core.execution import (
    Completion, EffectReceipt, ExecutionContext, InMemorySink,
    OperationDefinition, run,
)
from stratbox.core.observability import (
    decode_records, encode_records, record_from_result,
)
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import UsedInputReceipt


OP = OperationDefinition(
    "test.large_execution_evidence", 1, "v1", int, int,
    possible_effects=frozenset({"storage.write"}),
)


def _run_effects(count, *, sink=None, reverse=False):
    def handler(value, invocation):
        indexes = range(count - 1, -1, -1) if reverse else range(count)
        for index in indexes:
            invocation.effect(EffectReceipt(
                "storage.write", "confirmed", effect_id=f"effect_{index}",
            ))
        return value
    return run(OP, 1, handler, context=ExecutionContext(sink=sink))


@pytest.mark.parametrize("count", [100, 1000, 4096, 4097, 10_000])
def test_large_effects_have_bounded_truthful_summary(count):
    result = _run_effects(count)
    assert result.outcome == "succeeded"
    assert len(result.effects) == count
    record = record_from_result(result, observation_id="large")
    assert record.payload["details_counts"]["effects"] == count
    assert record.payload["details_counts"]["confirmed"] == count
    assert record.payload["details_counts"]["failed"] == 0
    assert record.payload["details_counts"]["unknown"] == 0
    assert len(record.payload["effects"]) <= 128
    assert len(record.references) <= 128
    assert record.payload["details_included"]["effects"] == len(record.payload["effects"])
    assert record.payload["details_coverage"] == (
        "complete" if count <= 128 else "summarized"
    )
    assert len(record.payload["details_digest"]) == 64
    restored, = decode_records(encode_records((record,)))
    assert restored == record


def test_large_fully_qualified_diagnostics_preserve_total_count():
    values = tuple(f"domain.issue_{i}" for i in range(10_000))
    def worker(value, invocation):
        return Completion(value, "failed", *values)
    result = run(OP, 1, worker)
    assert result.outcome == "failed"
    assert len(result.diagnostics) == 10_000
    record = record_from_result(result, observation_id="diags")
    assert record.payload["details_counts"]["diagnostics"] == 10_000
    assert record.payload["details_coverage"] == "summarized"
    assert record.payload["details_included"]["diagnostics"] <= 128
    assert len(record.payload["diagnostics"]) <= 128


def test_large_used_input_set_preserves_full_count_without_large_payload():
    def worker(value, invocation):
        for i in range(4_097):
            invocation.use(UsedInputReceipt(
                "source", ByteIdentity.of(str(i).encode()), "text/plain", "inline",
            ))
        return value
    result = run(OP, 1, worker)
    record = record_from_result(result, observation_id="inputs")
    assert len(result.used_inputs) == 4097
    assert record.payload["details_counts"]["inputs"] == 4097
    assert record.payload["details_coverage"] == "summarized"
    assert len(record.payload["inputs"]) <= 128


def test_canonical_finish_link_remains_deterministic_for_large_result():
    sink = InMemorySink()
    result = _run_effects(4_097, sink=sink)
    final = sink.events[-1]
    record = record_from_result(result, finished_event=final)
    again = record_from_result(result, finished_event=final)
    assert record == again
    assert record.payload["data_version"] == 3
    assert record.payload["details_coverage"] == "summarized"
    assert len(record.cause_record_ids) == 1
    assert record.record_id == again.record_id


def test_full_safe_detail_hash_is_order_sensitive():
    before = _run_effects(200, reverse=False)
    after = _run_effects(200, reverse=True)
    a = record_from_result(before, observation_id="same")
    b = record_from_result(after, observation_id="same")
    assert a.payload["details_counts"] == b.payload["details_counts"]
    assert a.payload["details_digest"] != b.payload["details_digest"]


def test_private_resource_reference_never_enters_portable_summary():
    def worker(value, invocation):
        invocation.effect(EffectReceipt(
            "storage.write", "confirmed", reference="/secret/account/credentials",
            effect_id="effect_1",
        ))
        return value
    result = run(OP, 1, worker)
    record = record_from_result(result, observation_id="private")
    assert "credentials" not in encode_records((record,)).decode("utf-8")


def test_oversized_individual_field_degrades_detail_coverage_without_false_success():
    def worker(value, invocation):
        invocation.use(UsedInputReceipt(
            "source", ByteIdentity.of(b"ok"), "application/" + "x" * 20_000, "inline",
            source_id="bounded-source",
        ))
        return value
    result = run(OP, 1, worker)
    record = record_from_result(result, observation_id="oversized")
    assert result.outcome == "succeeded"
    assert record.payload["details_counts"]["inputs"] == 1
    assert record.payload["details_coverage"] == "summarized"
    assert record.payload["details_included"]["inputs"] == 0
