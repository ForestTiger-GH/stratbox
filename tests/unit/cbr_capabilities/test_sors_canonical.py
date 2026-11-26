"""A narrow product keeps the complete coupled model and source evidence."""
from dataclasses import replace
from pathlib import Path
import sys

import pytest
from stratbox.capabilities.model import OperationDefinition, GraphBody, Call, InputRef, OutputRef, ParameterRef, PortContract
from stratbox.capabilities.model.targets import CalculationTarget, ProductTarget
from stratbox.capabilities.operations.standard import RESTORE
from stratbox.domains.cbr.calculations.sors import stages
from stratbox.domains.cbr.calculations.sors.contracts import SorsRunConfig
from stratbox.domains.cbr.calculations.sors.assembly import _identities
from stratbox.domains.cbr.calculations.sors.identity import seal_content
from stratbox.domains.cbr.calculations.sors.inputs.dependencies import DEPENDENCIES, source_uses
from stratbox.domains.cbr.products.corporate_lending.sors.contracts import SorsPivotRequest, SorsWorkbookRequest
from stratbox.sdk import StrategyBox
from stratbox.sdk.bootstrap import default_catalog
from stratbox.shared.data.values import View

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'cbr_sors_restoration'))
from test_snapshots import small_complete_bundle, source_inputs


@pytest.fixture
def bounded_model():
    bundle = small_complete_bundle()
    bundle = seal_content(replace(bundle,source_uses=source_uses(source_inputs())))
    config = SorsRunConfig('2026-06-01')
    admitted = stages.SorsModelInputs(bundle,config,_identities(bundle,config))
    build = replace(RESTORE.body.steps[1],inputs={'bundle':InputRef('bundle')})
    # This bounded numerical fixture enters after publisher-scope admission.
    # All equations, loops, solver checks and fact qualifications are production code.
    kernel = replace(RESTORE,id='operation.test.sors.kernel',inputs={'bundle':PortContract('model_inputs')},
        body=replace(RESTORE.body,steps=(build,*RESTORE.body.steps[2:])))
    return admitted,kernel


def test_narrow_projection_keeps_ten_sources_and_both_auxiliary_cubes(bounded_model,monkeypatch):
    admitted,kernel = bounded_model
    certified=[]
    original = stages.values_certify
    def capture(inputs,settings,context):
        output=original(inputs,settings,context)
        certified.append(output['values'].result)
        return output
    monkeypatch.setattr(stages,'values_certify',capture)
    narrow = OperationDefinition('operation.test.sors.narrow',inputs={'bundle':PortContract('model_inputs')},
        outputs={'view':PortContract('view',View)},body=GraphBody((
            Call('restore',kernel.id,{'bundle':InputRef('bundle')},target=CalculationTarget('cbr.sors')),
            Call('view','command.view.prepare',{'dataset':OutputRef('restore','dataset')},
                 {'request':ParameterRef('request')},target=ProductTarget('cbr.sors.workbook')),
        ),{'view':OutputRef('view','view')},required_checks=('restore','view')))
    request=SorsWorkbookRequest(include_primary_grid=False,include_restored_facts=False,
        include_fact_ledger=False,include_validation=False,include_conflicts=False,
        include_metadata_sheet=False,include_dimensions=False,
        pivots=(SorsPivotRequest(region_code='r1',metrics=('debt_rub',)),))
    with StrategyBox(catalog=default_catalog().with_definitions(kernel)) as box:
        plan=box.prepare(narrow,inputs={'bundle':admitted},parameters={'request':request},outputs=('view',))
        outcome=box.run(plan)
        assert outcome.outcome=='succeeded',outcome.diagnostics
        view=outcome.output('view')
    assert len(view.value.tables)==1
    pivot=view.value.tables[0][1]
    assert pivot['class_code'].tolist()==['01']
    assert pivot.iloc[0]['debt_rub']==100 and 'debt_fx' not in pivot.columns
    numerical=certified[0]
    assert numerical.summary.strict_status=='OPTIMAL'
    assert numerical.summary.primary_component_quantities==4
    assert numerical.summary.auxiliary_component_quantities==8
    assert numerical.summary.latent_component_quantities==12
    assert set(numerical.variables_grid['portfolio_scope'])=={'CORPORATE_TOTAL','SME','SME_IE'}
    assert len(numerical.source_bundle.source_manifest_grid)==10
    assert len(numerical.source_bundle.source_grid)==10
    assert len(numerical.source_bundle.source_uses)==10
    assert view.source_uses==numerical.source_bundle.source_uses
    assert all(len(getattr(numerical.source_bundle,dependency.input_name+'_grid'))==1
               for dependency in DEPENDENCIES if dependency.required)


def test_missing_solver_keeps_full_nonaccepted_problem_and_blocks_product(bounded_model,monkeypatch):
    admitted,kernel=bounded_model
    import stratbox.domains.cbr.calculations.sors.linear.highs as highs
    checks=[]
    original=stages.model_feasibility
    def unavailable():
        raise highs.SorsSolverDependencyError('Controlled missing official HiGHS backend')
    def capture(inputs,settings,context):
        output=original(inputs,settings,context)
        checks.append(output['feasibility'])
        return output
    monkeypatch.setattr(highs,'_load_highs',unavailable)
    monkeypatch.setattr(stages,'model_feasibility',capture)
    with StrategyBox() as box:
        outcome=box.invoke(kernel,inputs={'bundle':admitted},target=CalculationTarget('cbr.sors'))
        assert outcome.outcome=='failed'
        assert 'dataset' not in outcome.outputs
    assert checks and checks[0].status=='SOLVER_UNAVAILABLE' and not checks[0].success
    state=checks[0].problem.state
    assert set(state.quantities['portfolio_scope'])=={'CORPORATE_TOTAL','SME','SME_IE'}
    assert len(state.model.inputs.bundle.source_manifest_grid)==10
    assert not state.facts['is_accepted_fact'].any()
