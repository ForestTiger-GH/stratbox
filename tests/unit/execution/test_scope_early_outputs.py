"""Semantic scope acceptance controls early release and rejected siblings."""
from threading import Event
from time import monotonic, sleep

import pytest

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import (
    AcceptanceContract, Call, CommandDefinition, GraphBody, OperationDefinition,
    OutputRef, PortContract, ScenarioDefinition, SemanticPredicate, InputRef, ReuseContract,
)
from stratbox.core.execution.session import ExecutionSettings
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract

class Gate:
    waiting, release = Event(), Event()


WAITING, RELEASE = Gate.waiting, Gate.release
NUMBER = PortContract(DataContract("early.number"), int)
ACCEPTED = PortContract(DataContract("early.number"), int,
    predicates=(SemanticPredicate(operator="minimum", expected=5, code="acceptance.number_too_small"),))


def produce(request, invocation):
    return request["value"]


def check(request, invocation):
    Gate.waiting.set()
    while not Gate.release.wait(.002):
        invocation.check_cancelled()
    return request["number"]


def snapshot():
    commands = (
        CommandDefinition("early.produce", __name__ + ":produce", parameters={"value": 3}, outputs={"value": NUMBER}),
        CommandDefinition("early.wait", __name__ + ":check", inputs={"number": NUMBER}, outputs={"value": NUMBER},
            reuse=ReuseContract(shareable=False)),
    )
    good = OperationDefinition("early.good", GraphBody((Call("number", "early.produce", parameters={"value": 9}),),
        {"number": OutputRef("number")}), outputs={"number": ACCEPTED})
    bad = OperationDefinition("early.bad", GraphBody((
        Call("number", "early.produce", parameters={"value": 3}),
        Call("check", "early.wait", {"number": OutputRef("number")}),
    ), {"number": OutputRef("number")}, required_checks=("check",)), outputs={"number": ACCEPTED})
    scenario = ScenarioDefinition("early.independent", GraphBody((
        Call("good", "early.good"), Call("bad", "early.bad"),
    ), {"good": OutputRef("good", "number"), "bad": OutputRef("bad", "number")}),
        outputs={"good": NUMBER, "bad": NUMBER})
    return CatalogSnapshot(definitions=(*commands, good, bad, scenario))


def test_unaccepted_nominal_value_cannot_escape_while_accepted_sibling_releases_early():
    WAITING.clear(); RELEASE.clear()
    with StrategyBox(capabilities=snapshot(), settings=ExecutionSettings(max_workers=2)) as box:
        handle = box.submit(box.prepare("early.independent"))
        try:
            assert WAITING.wait(3)
            deadline = monotonic() + 3
            while monotonic() < deadline and handle.scope_states().get("early.independent/good") != "succeeded":
                sleep(.002)
            assert handle.output("good") == 9
            with pytest.raises(ValueError, match="acceptance.output_unavailable"):
                handle.output("bad")
            assert not handle.done()
        finally:
            RELEASE.set()
        result = handle.result(3)
        assert result.outcome == "failed"
        assert result.output("good") == 9
        assert "bad" not in result.outputs
        assert result.scopes["early.independent/bad"] == "failed"
        assert "acceptance.number_too_small" in result.diagnostics
        result.close()
