"""Invoke a temporary operation and a public command through one local session."""
from stratbox.capabilities.commands import MATERIAL, MATERIAL_INPUT
from stratbox.capabilities.model import Call, GraphBody, InputRef, OperationDefinition, OutputRef
from stratbox.composition.requests import InvocationRequest
from stratbox.sdk import StrategyBox


def main():
    operation = OperationDefinition("example.prepare_material", GraphBody((
        Call("read", "material.read", {"material": InputRef("material")}),
    ), {"material": OutputRef("read")}),
        inputs={"material": MATERIAL_INPUT}, outputs={"material": MATERIAL})
    with StrategyBox() as box:
        plan = box.prepare(operation, inputs={"material": b"source data"})
        print(plan.explain()["root_kind"])
        result = box.run(plan)
        command = box.run(InvocationRequest("material.read", inputs={"material": b"source data"}))
        assert result.outcome == command.outcome == "succeeded"
        assert result.output("material").identity == command.output("value").identity
        print(result.output("material").identity.sha256)
    # Returned values retain their own lifetime after the session closes.
    assert result.output("material").data == b"source data"
    result.close()
    command.close()


if __name__ == "__main__":
    main()
