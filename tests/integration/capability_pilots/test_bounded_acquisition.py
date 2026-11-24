"""Pre-admitted byte claims precede network actions and materialization."""
import pytest

from stratbox.core.execution.session import ExecutionSettings
from stratbox.shared.evidence import SourcePayload
from stratbox.sdk import StrategyBox
from .conftest import FixtureHttp


def test_declared_acquisition_exceeds_capacity_before_network(profiled_catalog):
    url = "https://fixture.example/large"
    provider = FixtureHttp({url: SourcePayload(b"small")})
    with StrategyBox(capabilities=profiled_catalog, providers={"http": provider},
            settings=ExecutionSettings(staging_bytes=4096, temporary_bytes=4096)) as box:
        with pytest.raises(ValueError, match="resource.unsatisfiable"):
            box.invoke("http.acquire", inputs={"url": url}, parameters={"max_bytes": 8192}, timeout=5)
        assert not provider.calls
        assert not any(box.session.ledger.snapshot().occupied.values())


def test_declared_max_equal_capacity_does_not_double_reserve_transport_stage(profiled_catalog):
    url = "https://fixture.example/small"
    payload = SourcePayload(b"x" * 1024)
    provider = FixtureHttp({url: payload})
    with StrategyBox(capabilities=profiled_catalog, providers={"http": provider},
            settings=ExecutionSettings(max_workers=1, staging_bytes=4096, temporary_bytes=4096)) as box:
        result = box.invoke("http.acquire", inputs={"url": url}, parameters={"max_bytes": 4096}, timeout=5)
        assert result.outcome == "succeeded", [(value.outcome, value.diagnostics) for value in result.results.values()]
        assert result.output("value").identity == payload.identity
        ledger = box.session.ledger.snapshot()
        assert ledger.spent["temporary_bytes"] == len(payload.data)
        assert ledger.peak["staging_bytes"] <= 4096
        assert ledger.occupied.get("staging_bytes", 0) == ledger.occupied.get("temporary_bytes", 0) == 0


def test_oversized_stream_releases_claims_and_never_accepts_body(profiled_catalog):
    url = "https://fixture.example/oversized"
    # The injected provider deliberately violates its request bound. The
    # receiving stage still rejects it before constructing a SourcePayload.
    provider = FixtureHttp({url: SourcePayload(b"x" * 1024)})
    with StrategyBox(capabilities=profiled_catalog, providers={"http": provider},
            settings=ExecutionSettings(max_workers=1, staging_bytes=4096, temporary_bytes=4096)) as box:
        result = box.invoke("http.acquire", inputs={"url": url}, parameters={"max_bytes": 512}, timeout=5)
        assert result.outcome == "failed"
        assert "value" not in result.outputs
        ledger = box.session.ledger.snapshot()
        assert ledger.occupied.get("staging_bytes", 0) == 0
        assert ledger.occupied.get("temporary_bytes", 0) == 0
        assert ledger.occupied.get("retained_bytes", 0) == 0
