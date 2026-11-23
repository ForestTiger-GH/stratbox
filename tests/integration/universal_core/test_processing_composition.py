"""The catalog supports independent local processing with existing execution truth."""

from datetime import date
from pathlib import Path

from stratbox.core.execution import ExecutionContext, InMemorySink
from stratbox.shared.data.operations import assess_input
from stratbox.core.operations.source.originals import (
    OriginalDestination,
    ReadOriginalRequest,
    SaveOriginalRequest,
    read_original,
    save_original,
)
from stratbox.core.storage.filestore import LocalFileStore
import stratbox.domains.cbr.operations.service_network.bank_offices as bank_offices
from stratbox.domains.registry import operation_catalog
from stratbox.shared.data.releases import CompareReleaseRequest
from stratbox.shared.evidence import SourcePayload


def test_retained_original_can_be_read_parsed_and_compared_without_acquisition(
    tmp_path,
):
    fixture = (
        Path(__file__).resolve().parents[2]
        / "fixtures/universal_core/offices-basic.html"
    )
    payload = SourcePayload(fixture.read_bytes(), "text/html")
    (tmp_path / "scrolls").mkdir()
    store = LocalFileStore(str(tmp_path))
    saved = save_original(
        SaveOriginalRequest(payload, OriginalDestination("scrolls/source.html")),
        store=store,
    )
    assert saved.outcome == "succeeded"
    restored = read_original(ReadOriginalRequest(saved.value.material), store=store)
    assert (
        restored.outcome == "succeeded" and restored.value.identity == payload.identity
    )

    sink = InMemorySink()
    parsed = bank_offices.parse(
        bank_offices.ParseOfficesRequest(restored.value, date(2026, 11, 12)),
        context=ExecutionContext(sink=sink),
    )
    assert parsed.outcome == "succeeded"
    assert all(item.role != "http" for item in parsed.definition.runtime_dependencies)
    assert not parsed.effects and parsed.used_inputs
    assert parsed.value.inputs[0].identity == payload.identity

    catalog = operation_catalog()
    compare_input = next(
        port
        for port in catalog.get("cbr.offices.compare", 2).processing.inputs
        if port.name == "candidate"
    )
    release_port = next(
        port for port in parsed.definition.processing.outputs if port.name == "release"
    )
    assert assess_input(
        compare_input, release_port.contract, outcome=parsed.outcome
    ).compatible
    compared = bank_offices.compare(CompareReleaseRequest(parsed.value, parsed.value))
    assert compared.outcome == "succeeded" and compared.value.state == "unchanged"
    assert catalog.compatible_next("cbr.offices.parse", 1)
    assert (tmp_path / "scrolls/source.html").read_bytes() == payload.data
