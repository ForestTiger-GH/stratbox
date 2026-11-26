"""The same numerical stages compose through the actual standard execution path."""
from dataclasses import replace

import pytest

from stratbox.capabilities.model.targets import CalculationTarget, ProductTarget
from stratbox.domains.cbr.calculations.sors import stages
from stratbox.domains.cbr.calculations.sors.assembly import _identities
from stratbox.domains.cbr.calculations.sors.contracts import SorsRunConfig, SorsOptimizationConfig, SorsCrosswalkConfig
from stratbox.domains.cbr.calculations.sors.identity import seal_content, validate_content
from stratbox.domains.cbr.calculations.sors.serialization import encode, decode
from stratbox.sdk import StrategyBox
from test_snapshots import small_complete_bundle, strict_context
from support import execute_model_methods


def test_real_solver_numerical_route_rechecks_every_phase_before_certification():
    pytest.importorskip('highspy')
    bundle = small_complete_bundle()
    config = SorsRunConfig('2026-06-01', optimization=SorsOptimizationConfig(mode='priority', max_targets=2))
    admitted = stages.SorsModelInputs(bundle, config, _identities(bundle, config))
    result = execute_model_methods(admitted, config)
    assert result.summary.strict_status == 'OPTIMAL'
    assert tuple(result.optimization_rounds_grid['phase']) == ('strict', 'rounding', 'selection')
    assert len(result.regional_okved2_grid) == 6
    debt = result.regional_okved2_grid.query("class_code == '01' and metric == 'debt_rub'").iloc[0]
    assert debt['value'] == 100 and bool(debt['is_primary_fact'])
    assert set(result.source_bundle.source_grid['portfolio_scope']) == {'CORPORATE_TOTAL', 'SME', 'SME_IE'}
    validate_content(result)
    restored = decode(encode(result))
    assert restored.fingerprint == result.fingerprint
    assert restored.summary == result.summary


def test_exact_compiled_problem_can_be_retained_without_solver_session():
    bundle = small_complete_bundle()
    config = SorsRunConfig('2026-06-01')
    built = stages.constraints_build({'bundle': stages.SorsModelInputs(bundle, config, _identities(bundle, config))}, None, None)
    state = built['state']
    while not state.converged:
        state = stages.bounds_propagate({'state': state}, None, None)['state']
        candidates = stages.facts_inherit({'state': state}, None, None)['candidates']
        state = stages.facts_reconcile({'state': state, 'candidates': candidates}, None, None)['state']
    compiled = stages.model_compile({'state': state}, None, None)['problem']
    restored = decode(encode(compiled))
    assert restored.fingerprint == compiled.fingerprint
    assert not hasattr(restored, 'session')
    assert stages.model_feasibility({'problem': restored}, None, None)['feasibility'].success


def test_sdk_uses_standard_operation_for_crosswalk_and_product_commands():
    pytest.importorskip('highspy')
    strict = strict_context()
    with StrategyBox() as box:
        restored = box.invoke('operation.constraints.restore', inputs={'datasets': strict},
            parameters={'config': SorsCrosswalkConfig(mode='feasibility')},
            target=CalculationTarget('cbr.sors.crosswalk'))
        assert restored.outcome == 'succeeded', restored.diagnostics
        dataset = restored.output('dataset')
        facts = dataset.native.crosswalk_facts_grid.set_index(['class_code', 'metric'])
        assert facts.loc[('01', 'overdue_rub'), 'value'] == 90
        assert facts.loc[('02', 'overdue_rub'), 'value'] == 10
        prepared = box.invoke('command.view.prepare', inputs={'dataset': dataset}, target=ProductTarget('cbr.sors.workbook'))
        assert prepared.outcome == 'succeeded', prepared.diagnostics
        encoded = box.invoke('command.value.encode', inputs={'value': prepared.output('view')}, target=ProductTarget('cbr.sors.workbook'))
        assert encoded.outcome == 'succeeded', encoded.diagnostics
        decoded = box.invoke('command.value.decode', inputs={'representation': encoded.output('representation')}, target=ProductTarget('cbr.sors.workbook'))
        assert decoded.outcome == 'succeeded', decoded.diagnostics
        rendered = box.invoke('command.product.render', inputs={'view': decoded.output('value')}, target=ProductTarget('cbr.sors.workbook'))
        assert rendered.outcome == 'succeeded', rendered.diagnostics
        assert rendered.output('product').data.startswith(b'PK')


def test_sdk_executes_strict_kernel_with_actual_named_command_contracts():
    from stratbox.capabilities.operations.standard import RESTORE
    from stratbox.capabilities.model import GraphBody, InputRef, PortContract
    bundle = small_complete_bundle()
    config = SorsRunConfig('2026-06-01')
    # A bounded numerical fixture enters after publisher-specific admission.
    # Every subsequent command and both loops are the actual standard graph.
    built_step = replace(RESTORE.body.steps[1], inputs={'bundle': InputRef('bundle')})
    fixture_operation = replace(RESTORE, id='operation.test.sors.kernel',
        inputs={'bundle': PortContract('model_inputs')},
        body=replace(RESTORE.body, steps=(built_step, *RESTORE.body.steps[2:])))
    admitted = stages.SorsModelInputs(bundle, config, _identities(bundle, config))
    with StrategyBox() as box:
        outcome = box.invoke(fixture_operation, inputs={'bundle': admitted},
                             target=CalculationTarget('cbr.sors'))
        assert outcome.outcome == 'succeeded', outcome.diagnostics
        dataset = outcome.output('dataset')
        assert dataset.native.summary.strict_status == 'OPTIMAL'
        assert dataset.native.source_bundle.source_grid['portfolio_scope'].nunique() == 3
        assert len(dataset.rows) == 6
