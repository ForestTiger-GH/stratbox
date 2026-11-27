"""Every statistical boundary uses prepared methods, factual journals and bounded execution."""
from dataclasses import replace

import pytest

from stratbox.core.execution.service import ExecutionFailure, ExecutionSettings
from stratbox.core.limits import ExecutionBudget
from stratbox.core.observability.journal.stream import MemoryJournal
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material, fingerprint
from .test_workbook_replay import SERIES, XLSX, action, context, flake, interpret, prepare, workbook


@pytest.fixture(scope="module")
def materials():
    material=Material(workbook(exact="123.00"),XLSX,SERIES,metadata={"issue_id":"capture-1","asset_id":"main"})
    tables=flake(material.data);dataset=interpret(tables);view=prepare(dataset)
    encoded=action("value.encode",{"value":dataset})["representation"]
    from stratbox.core.commands.decoding import workbook_decode
    physical=workbook_decode({"material":material},None,context())["physical"]
    physical=replace(physical,material=material)
    return {
        "decode":("command.workbook.decode",{"material":material},"physical"),
        "extract":("command.table.extract",{"physical":physical},"tables"),
        "interpret":("command.table.interpret",{"tables":tables},"dataset"),
        "encode":("command.value.encode",{"value":dataset},"representation"),
        "replay":("command.value.decode",{"representation":encoded},"value"),
        "validate":("command.observations.validate",{"dataset":dataset},"dataset"),
        "compare":("command.source.assess",{"evidence":flake(workbook(exact="124.00")),"baseline":tables},"assessment"),
        "render":("command.product.render",{"view":view},"product"),
    }


@pytest.mark.parametrize("name",("decode","extract","interpret","encode","replay","validate","compare"))
def test_each_boundary_records_exact_inputs_bound_method_and_accepted_output(materials,name):
    identifier,inputs,output=materials[name]
    journal=MemoryJournal()
    with StrategyBox(journal=journal) as box:
        plan=box.prepare(identifier,target=SERIES,inputs=inputs)
        task,=plan.tasks
        assert task.command.id==identifier and fingerprint(task.inputs)==fingerprint(inputs)
        result=box.run(plan)
        assert result.outcome=="succeeded",result.diagnostics
        value=result.output(output)
        assert fingerprint(value)
        facts=journal.read(run_id=result.run_id)
        accepted=[fact for fact in facts if fact.kind=="output.accepted" and fact.output_name==output
            and fact.command_id==identifier and fact.physical_work_id]
        assert len(accepted)==1 and accepted[0].physical_work_id
        assert any(fact.kind=="run.finished" and fact.data["outcome"]=="succeeded" for fact in facts)
        assert result.effects=={}


def test_identical_bytes_under_distinct_asset_contexts_have_different_semantic_work(materials):
    _,inputs,_=materials["extract"];physical=inputs["physical"]
    journal=MemoryJournal()
    with StrategyBox(journal=journal) as box:
        first=box.invoke("command.table.extract",target=SERIES,inputs=inputs,parameters={"issue_id":"capture-1","asset_id":"main"})
        second=box.invoke("command.table.extract",target=SERIES,inputs=inputs,parameters={"issue_id":"capture-1","asset_id":"appendix"})
        assert first.outcome==second.outcome=="succeeded"
        assert first.output("tables").tables==second.output("tables").tables
        assert fingerprint(first.output("tables"))!=fingerprint(second.output("tables"))
        ids=[next(f.physical_work_id for f in journal.read(run_id=r.run_id) if f.kind=="output.accepted") for r in (first,second)]
        assert ids[0]!=ids[1]


def test_interpretation_request_parameters_remain_in_prepared_command_identity(materials):
    _,inputs,_=materials["interpret"]
    with StrategyBox() as box:
        first=box.prepare("command.table.interpret",target=SERIES,inputs=inputs,parameters={"row_bindings":()})
        second=box.prepare("command.table.interpret",target=SERIES,inputs=inputs,parameters={"row_bindings":(),"audit_label":"reviewed"})
        assert first.tasks[0].command.parameters["row_bindings"]==()
        assert second.tasks[0].command.parameters["audit_label"]=="reviewed"
        assert fingerprint(first.tasks[0].command.parameters)!=fingerprint(second.tasks[0].command.parameters)


def test_renderer_reads_only_prepared_view_and_retention_bound_is_enforced(materials,monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError("Rendering must not decode or interpret source material")
    monkeypatch.setattr("stratbox.core.formats.spreadsheets.cells.read_workbook_cells",forbidden)
    monkeypatch.setattr("stratbox.domains.cbr.methods.actions.statistics.interpret",forbidden)
    identifier,inputs,output=materials["render"]
    with StrategyBox() as box:
        result=box.invoke(identifier,target="cbr.statistics.table",inputs=inputs,parameters={"format":"csv"})
        assert result.outcome=="succeeded" and result.output(output).data
    with StrategyBox(settings=ExecutionSettings(max_retained_bytes=1)) as box:
        # Private input ownership is admitted before any execution. A budget
        # smaller than the input is rejected at that boundary, with no run or
        # effect accepted and no partially retained input left behind.
        with pytest.raises(ValueError,match="value.retention_capacity_exhausted"):
            box.invoke(identifier,target="cbr.statistics.table",inputs=inputs,parameters={"format":"csv"})
        assert box.session.quiescent and not box.session.journal.read()
        assert box.session.value_statistics()['resident_bytes']==0


def test_physical_evidence_encoding_checks_cancellation_before_work(materials):
    _,inputs,_=materials["extract"]
    class Cancelled:
        parameters={}
        def checkpoint(self):
            raise ExecutionFailure("execution.cancelled",outcome="cancelled")
    from stratbox.domains.cbr.methods.actions.serialization import encode
    with pytest.raises(ExecutionFailure,match="execution.cancelled"):
        encode({"value":inputs["physical"]},None,Cancelled())


@pytest.mark.parametrize("name,resource",(
    ("decode","input_bytes"),("extract","cells"),("interpret","cells"),
    ("encode","output_bytes"),("replay","input_bytes"),
    ("validate","output_bytes"),("compare","input_bytes"),("render","output_bytes"),
))
def test_cumulative_budget_protects_each_independent_boundary(materials,name,resource):
    identifier,inputs,_=materials[name]
    target="cbr.statistics.table" if name=="render" else SERIES
    with StrategyBox(settings=ExecutionSettings(run_limits=ExecutionBudget(**{resource:1}))) as box:
        result=box.invoke(identifier,target=target,inputs=inputs,parameters={"format":"csv"} if name=="render" else {})
        assert result.outcome=="failed",result.diagnostics
        assert any("budget."+resource in str(item) for item in result.diagnostics)
        assert not result.outputs and not result.effects


def test_complete_value_payload_is_charged_to_boundary_input_and_output(materials):
    identifier,inputs,output=materials["decode"]
    with StrategyBox() as box:
        result=box.invoke(identifier,target=SERIES,inputs=inputs)
        assert result.outcome=="succeeded"
        assert result.resources["input_bytes"]>=len(inputs["material"].data)
        assert result.resources["output_bytes"]>0 and result.resources["cells"]>0
