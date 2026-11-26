from dataclasses import replace
from decimal import Decimal, localcontext
from io import BytesIO
from threading import Lock
from time import sleep

import pytest

from stratbox.capabilities.model import MethodRef, PortContract, ReuseContract, SourceRequirement, SemanticPredicate
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, PreparedPlan, ValueRef, MapTask, RepeatTask, TemplateInput
from stratbox.core.execution.service import ExecutionService, ExecutionSettings, ExecutionFailure
from stratbox.shared.data.values import Material, SourceDataset, FormulaSpec, fingerprint, RequestSpec, FetchEvidence

COUNTS = {}
LOCK = Lock()


def echo(inputs, settings, context):
    return {"value": inputs["value"]}


def counted(inputs, settings, context):
    with LOCK:
        COUNTS["calls"] = COUNTS.get("calls", 0) + 1
        COUNTS["active"] = COUNTS.get("active", 0) + 1
        COUNTS["max"] = max(COUNTS.get("max", 0), COUNTS["active"])
    sleep(.02)
    with LOCK: COUNTS["active"] -= 1
    return {"value": inputs["value"]}


def decode_counted(inputs, settings, context):
    from stratbox.core.commands.decoding import workbook_decode
    with LOCK: COUNTS["decode"] = COUNTS.get("decode", 0) + 1
    sleep(.02)
    return workbook_decode(inputs, settings, context)


def interpret(inputs, settings, context):
    physical = inputs["physical"]
    assert physical.material.source_id == settings["source"]
    from stratbox.shared.data.source_context import SourceUse, SourceCoordinate
    return {"dataset": SourceDataset(settings["source"], ({"value": physical.workbook.sheets[0].cells[0].value},),
        source_uses=(SourceUse(SourceCoordinate(settings["source"], material_identity=physical.material.identity), "material", "recognized"),))}


def twice(inputs, settings, context):
    if inputs["value"] < 0: raise ValueError("negative")
    return {"value": inputs["value"] * 2}


def increment(inputs, settings, context):
    return {"state": inputs["state"] + 1}


def effect_once(inputs, settings, context):
    def action():
        COUNTS["effects"] = COUNTS.get("effects", 0) + 1
        if settings.get("lose_reply"): raise OSError("lost reply")
        return "stored"
    receipt = context.effect("storage.write", "effect-one", action, resource="one")
    return {"value": receipt}


def command(name="echo", inputs=None, outputs=None, *, settings=None, resources=None, reuse=None, effects=()):
    return BoundCommand("command." + name, MethodRef(__name__ + ":" + name), settings,
        inputs or {"value": PortContract("value", int)}, outputs or {"value": PortContract("value", int)},
        resources=resources or {"cpu": 1}, reuse=reuse or ReuseContract(), effects=frozenset(effects))


def plan(tasks, outputs=None):
    return PreparedPlan("test", tuple(tasks), (), outputs or {"value": ValueRef(tasks[-1].task_id)}, "test", "build")


def test_direct_dependencies_and_result_lifetime():
    first = CommandTask("first", command(), {"value": 3})
    second = CommandTask("second", command(), {"value": ValueRef("first")}, ("first",))
    with ExecutionService() as service:
        result = service.run(plan([first, second]), timeout=3)
        assert result.outcome == "succeeded" and result.output() == 3
        assert service._retained_bytes > 0
        result.close()
        assert service._retained_bytes == 0
        with pytest.raises(ExecutionFailure, match="result_closed"): result.output()


def test_resources_shared_across_runs_and_exact_work_reused():
    COUNTS.clear()
    settings = ExecutionSettings(max_workers=4, capacities={"cpu": 1})
    with ExecutionService(settings=settings) as service:
        handles = [service.submit(plan([CommandTask("work", command("counted", reuse=ReuseContract(shareable=False)), {"value": i})])) for i in range(4)]
        assert [handle.result(3).output() for handle in handles] == list(range(4))
        assert COUNTS["max"] == 1 and COUNTS["calls"] == 4
        identical = [service.submit(plan([CommandTask("work", command("counted"), {"value": 50})])) for _ in range(2)]
        assert [handle.result(3).output() for handle in identical] == [50, 50]
        assert COUNTS["calls"] == 5


def test_source_neutral_decode_has_independent_logical_attribution():
    from openpyxl import Workbook
    book = Workbook(); book.active["A1"] = 42
    stream = BytesIO(); book.save(stream)
    COUNTS.clear()
    tasks = []
    for source in ("A", "B"):
        decode = replace(command("decode_counted", {"material": PortContract("material", Material)}, {"physical": PortContract("physical")}), id="command.workbook.decode")
        tasks.append(CommandTask("decode" + source, decode, {"material": Material(stream.getvalue(), source_id=source)}))
        semantic = command("interpret", {"physical": PortContract("physical")},
            {"dataset": PortContract("dataset", SourceDataset, source=SourceRequirement(frozenset({source})))}, settings={"source": source})
        tasks.append(CommandTask("interpret" + source, semantic, {"physical": ValueRef("decode" + source, "physical")}, ("decode" + source,)))
    with ExecutionService() as service:
        result = service.run(plan(tasks, {"A": ValueRef("interpretA", "dataset"), "B": ValueRef("interpretB", "dataset")}), timeout=5)
        assert result.outcome == "succeeded", result.diagnostics
        assert result.output("A").source_id == "A" and result.output("B").source_id == "B"
        assert COUNTS["decode"] == 1


def test_map_window_and_every_selected_unit_outcome():
    template = plan([CommandTask("twice", command("twice"), {"value": TemplateInput("item")})])
    mapped = MapTask("map", template, (1, -1, 3), item_output="value", completion="eligible_subset", window=1)
    with ExecutionService(settings=ExecutionSettings(max_workers=1)) as service:
        result = service.run(plan([mapped], {"items": ValueRef("map", "items"), "outcomes": ValueRef("map", "outcomes")}), timeout=3)
        assert result.outcome == "succeeded", result.diagnostics
        assert result.output("items") == (2, 6)
        assert result.output("outcomes") == ((0, "succeeded"), (1, "failed"), (2, "succeeded"))


def test_iteration_converges_and_limit_never_claims_completion():
    work = command("increment", {"state": PortContract("state", int)}, {"state": PortContract("state", int)})
    template = plan([CommandTask("increment", work, {"state": TemplateInput("state")})], {"state": ValueRef("increment", "state")})
    repeat = RepeatTask("repeat", template, 0, stop=SemanticPredicate("", "minimum", 3), max_passes=5)
    with ExecutionService(settings=ExecutionSettings(max_workers=1)) as service:
        result = service.run(plan([repeat], {"state": ValueRef("repeat", "state")}), timeout=3)
        assert result.outcome == "succeeded" and result.output("state") == 3
        limited = replace(repeat, max_passes=2)
        rejected = service.run(plan([limited], {"state": ValueRef("repeat", "state")}), timeout=3)
        assert rejected.outcome == "failed" and "iteration.limit_without_convergence" in rejected.diagnostics


def test_effect_identity_prevents_blind_retry_after_lost_reply():
    COUNTS.clear()
    work = command("effect_once", outputs={"value": PortContract("receipt")}, settings={"lose_reply": True}, effects=("storage.write",), reuse=ReuseContract(shareable=False))
    with ExecutionService() as service:
        first = service.run(plan([CommandTask("effect", work, {"value": 1})]), timeout=3)
        second = service.run(plan([CommandTask("effect", work, {"value": 1})]), timeout=3)
        assert first.outcome == second.outcome == "unknown"
        assert COUNTS["effects"] == 1


def test_numeric_precision_and_formula_contracts():
    from stratbox.core.commands.calculations import calculate_change, calculate_formula, calculate_flow
    class Context:
        parameters = {}
    common = dict(metric="balance", subject="RU", unit="RUB", scale=1, perimeter="all", measure_kind="stock", value_status="reported")
    rows = ({**common, "period": "2026-01", "value": Decimal("1234567890123456789012345678901234567890.0001")},
            {**common, "period": "2026-02", "value": Decimal("1234567890123456789012345678901234567890.0003")})
    with localcontext() as context:
        context.prec = 3
        result = calculate_change({"observations": SourceDataset("test", rows)}, {}, Context())["dataset"]
        assert result.rows[0]["value"] == Decimal(".0002")
    input_rows = ({**common, "metric": "total", "period": "2026-01", "value": Decimal(130)},
                  {**common, "metric": "other", "period": "2026-01", "value": Decimal(40)})
    formula = FormulaSpec("total - other", {"total": "total", "other": "other"}, "liquid", "RUB")
    assert calculate_formula({"dataset": SourceDataset("nwf", input_rows)}, formula, Context())["dataset"].rows[0]["value"] == 90
    with pytest.raises(ExecutionFailure, match="dimension"):
        calculate_formula({"dataset": SourceDataset("nwf", input_rows)}, replace(formula, expression="total * other"), Context())
    flows = tuple({**row, "measure_kind": "flow", "basis": "ytd", "frequency": "monthly"} for row in rows)
    gap = (flows[0], {**flows[1], "period": "2026-03"})
    with pytest.raises(ExecutionFailure, match="gap"):
        calculate_flow({"observations": SourceDataset("budget", gap)}, {}, Context())


def test_mapping_key_identity_does_not_collapse_types():
    assert fingerprint({1: "value"}) != fingerprint({"1": "value"})


def test_journal_facts_retain_output_and_effect_distinctions():
    with ExecutionService() as service:
        result = service.run(plan([CommandTask("work", command(), {"value": 9})]), timeout=3)
        facts = service.journal.read(run_id=result.run_id)
        assert [fact.kind for fact in facts].count("output.accepted") == 1
        assert any(fact.kind == "run.finished" for fact in facts)
        assert not any(fact.kind.startswith("effect.") for fact in facts)
