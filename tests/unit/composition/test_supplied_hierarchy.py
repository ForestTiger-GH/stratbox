"""Exact reusable scenarios, frozen selectors and independent cascade goals."""
from dataclasses import replace
from threading import Event
from time import monotonic, sleep

import pytest

from stratbox.capabilities.catalog import CatalogContribution
from stratbox.capabilities.manifest import catalog_snapshot
from stratbox.capabilities.model import CapabilityRef
from stratbox.capabilities.scenarios.workflows import (
    ScenarioMember, cascade_definition, operation_scenario, scenario_members,
)
from stratbox.core.execution.session import ExecutionSettings
from stratbox.sdk import StrategyBox


def test_reused_scenario_retains_occurrences_and_exact_input_version_vector():
    snapshot = catalog_snapshot()
    scenario = operation_scenario(snapshot, 'accept.original', scenario_id='source.preserve_candidate')
    snapshot = snapshot.overlay(CatalogContribution(definitions=(scenario,)))
    members = tuple(ScenarioMember(name, CapabilityRef(scenario.id, scenario.revision, scenario.fingerprint),
        parameters={'source_id': source}) for name, source in (('first', 'example.a'), ('second', 'example.b')))
    cascade = cascade_definition(snapshot, 'report.originals', members)
    snapshot = snapshot.overlay(CatalogContribution(definitions=(cascade,)))
    with StrategyBox(capabilities=snapshot) as box:
        plan = box.prepare(cascade.id, inputs={'first__material': b'a', 'second__material': b'b'})
        changed = box.prepare(cascade.id, inputs={'first__material': b'a', 'second__material': b'c'})
        assert plan.plan_id != changed.plan_id
        result = box.run(plan, timeout=10)
        assert result.outcome == 'succeeded', result.diagnostics
        assert result.output('first__original').source_id == 'example.a'
        assert result.output('second__original').source_id == 'example.b'
        occurrences = [scope for scope in plan.scopes if scope.definition_id == scenario.id]
        assert len(occurrences) == 2 and occurrences[0].scope_id != occurrences[1].scope_id


def test_membership_selector_is_frozen_and_revision_checked():
    snapshot = catalog_snapshot()
    selected = scenario_members(snapshot, capability_ids=('scenario.source_original',))
    added = replace(snapshot.definition('scenario.source_original'), capability_id='scenario.another_original')
    expanded = snapshot.overlay(CatalogContribution(definitions=(added,)))
    cascade = cascade_definition(expanded, 'report.fixed', selected)
    assert cascade.membership.members == ('member_0',)
    changed = replace(snapshot.definition('scenario.source_original'), revision='2')
    replaced = snapshot.overlay(CatalogContribution(definitions=(changed,)), replace_ids=(changed.id,))
    with pytest.raises(ValueError, match='workflow.definition_changed'):
        cascade_definition(replaced, 'report.stale', selected)


def test_required_completion_survives_output_projection_without_blocking_early_output(monkeypatch):
    import stratbox.core.capabilities.materials as materials
    waiting, release = Event(), Event()
    original = materials.material_read
    def read(request, invocation):
        if request.get('material') == b'slow':
            waiting.set()
            while not release.wait(.002):
                invocation.check_cancelled()
            raise ValueError('fixture.late_failure')
        return original(request, invocation)
    monkeypatch.setattr(materials, 'material_read', read)
    snapshot = catalog_snapshot()
    cascade = cascade_definition(snapshot, 'report.independent', (
        ScenarioMember('fast', CapabilityRef('scenario.source_original')),
        ScenarioMember('slow', CapabilityRef('scenario.source_original'))))
    with StrategyBox(capabilities=snapshot, settings=ExecutionSettings(max_workers=2)) as box:
        plan = box.prepare(cascade, inputs={'fast__material': b'fast', 'slow__material': b'slow'},
                           outputs=('fast__original',))
        assert any('slow' in task.scope_id for task in plan.tasks)
        handle = box.submit(plan)
        try:
            assert waiting.wait(3)
            deadline = monotonic() + 3
            while monotonic() < deadline:
                try:
                    assert handle.output('fast__original').data == b'fast'
                    break
                except ValueError:
                    sleep(.002)
            else:
                pytest.fail('independent output remained blocked by another completion')
            assert not handle.done()
        finally:
            release.set()
        result = handle.result(5)
        assert result.outcome == 'failed'
        assert result.output('fast__original').data == b'fast'


def test_optional_goal_failure_keeps_required_product_accepted():
    snapshot = catalog_snapshot()
    cascade = cascade_definition(snapshot, 'report.optional', (
        ScenarioMember('original', CapabilityRef('scenario.source_original')),
        ScenarioMember('preview', CapabilityRef('scenario.observation_view'), required=False)))
    with StrategyBox(capabilities=snapshot) as box:
        result = box.run(cascade, inputs={'original__material': b'original', 'preview__material': b'bad workbook'}, timeout=10)
        assert result.outcome == 'partial', result.diagnostics
        assert result.output('original__original').data == b'original'
        assert 'preview__view' not in result.outputs


def test_frozen_member_reference_survives_cascade_authoring_and_rejects_later_replacement():
    snapshot = catalog_snapshot()
    original = snapshot.definition('scenario.source_original')
    cascade = cascade_definition(snapshot, 'report.pinned', (
        ScenarioMember('source', CapabilityRef(original.id, original.revision, original.fingerprint)),))
    authored = snapshot.overlay(CatalogContribution(definitions=(cascade,)))
    changed = replace(original, revision='2')
    with pytest.raises(ValueError, match='catalog.definition_reference_changed'):
        authored.overlay(CatalogContribution(definitions=(changed,)), replace_ids=(changed.id,))


def test_source_recipe_rejects_conflicting_source_identity():
    from stratbox.composition.source import source_workflow
    from stratbox.sdk.bootstrap import default_snapshot
    with pytest.raises(ValueError, match='workflow.source_mismatch'):
        source_workflow('frg.express.issuance', payload=b'original', output='original',
            parameters={'source_id': 'frg.express.portfolios'}, catalog=default_snapshot())


def test_coherent_required_member_preserves_optional_output_status():
    from stratbox.capabilities.commands import MATERIAL, MATERIAL_INPUT
    from stratbox.capabilities.model import ScenarioDefinition, GraphBody, Call, InputRef, OutputRef, Condition
    snapshot = catalog_snapshot()
    scenario = ScenarioDefinition('fixture.optional_port', GraphBody((
        Call('read', 'accept.original', {'material': InputRef('material')}),
        Call('conditional', 'accept.original', {'material': InputRef('material')},
            condition=Condition('read', 'original', field='data', equals=b'emit_optional'), required=False),
    ), {'needed': OutputRef('read', 'original'), 'optional': OutputRef('conditional', 'original')}),
        inputs={'material': MATERIAL_INPUT}, outputs={'needed': MATERIAL, 'optional': replace(MATERIAL, required=False)})
    snapshot = snapshot.overlay(CatalogContribution(definitions=(scenario,)))
    cascade = cascade_definition(snapshot, 'report.coherent', (
        ScenarioMember('source', CapabilityRef(scenario.id, scenario.revision, scenario.fingerprint)),), coherent=True)
    with StrategyBox(capabilities=snapshot) as box:
        result = box.invoke(cascade, inputs={'source__material': b'required_only'}, timeout=10)
        assert result.outcome == 'succeeded', result.diagnostics
        assert result.output('source__needed').data == b'required_only'
        assert 'source__optional' not in result.outputs


def test_exact_scenario_pins_resolved_method_across_catalog_reconstruction():
    snapshot = catalog_snapshot()
    scenario = operation_scenario(snapshot, 'extract.observations', method_id='extract.rows')
    snapshot = snapshot.overlay(CatalogContribution(definitions=(scenario,)))
    with pytest.raises(ValueError, match='catalog.binding_reference_changed'):
        replace(snapshot, methods=tuple(replace(method, revision='2')
            if method.method_id == 'extract.rows' else method for method in snapshot.methods))


def test_required_completion_root_cannot_silently_be_optional():
    from stratbox.capabilities.model import Call, GraphBody
    with pytest.raises(ValueError, match='capability.optional_completion_root'):
        GraphBody((Call('goal', 'scenario.source_original', required=False),),
                  required_completions=('goal',))


def test_same_scenario_definition_is_reused_by_two_live_cascades():
    snapshot = catalog_snapshot()
    members = (ScenarioMember('member', CapabilityRef('scenario.source_original')),)
    first = cascade_definition(snapshot, 'report.first', members)
    second = cascade_definition(snapshot, 'report.second', members)
    with StrategyBox(capabilities=snapshot, settings=ExecutionSettings(max_workers=1, active_runs=2)) as box:
        a = box.submit(first, inputs={'member__material': b'same'}, parameters={'member__source_id': 'example.a'})
        b = box.submit(second, inputs={'member__material': b'same'}, parameters={'member__source_id': 'example.b'})
        ra, rb = a.result(5), b.result(5)
        assert ra.outcome == rb.outcome == 'succeeded'
        assert ra.output('member__original').source_id == 'example.a'
        assert rb.output('member__original').source_id == 'example.b'
        assert 'report.first/member' in ra.scopes and 'report.second/member' in rb.scopes


def test_live_catalog_addition_cannot_widen_frozen_selector_membership(monkeypatch):
    import stratbox.core.capabilities.materials as materials
    waiting, release = Event(), Event()
    original = materials.material_read
    def gated(request, invocation):
        waiting.set()
        while not release.wait(.002):
            invocation.check_cancelled()
        return original(request, invocation)
    monkeypatch.setattr(materials, 'material_read', gated)
    snapshot = catalog_snapshot()
    selected = scenario_members(snapshot, query='scenario.source_original')
    cascade = cascade_definition(snapshot, 'report.frozen_selector', selected)
    with StrategyBox(capabilities=snapshot) as box:
        handle = box.submit(cascade, inputs={'member_0__material': b'original'})
        try:
            assert waiting.wait(3)
            later = replace(snapshot.definition('scenario.source_original'), capability_id='scenario.source_original.later')
            box.prepare(later, inputs={'material': b'later'})
            assert later.id in {item.id for item in box.scenarios}
        finally:
            release.set()
        result = handle.result(5)
        assert result.outcome == 'succeeded', result.diagnostics
        assert cascade.membership.members == ('member_0',)
        assert not any('later' in identifier for identifier in result.scopes)
