"""Target contracts are exercised through observable preparation behavior."""
from dataclasses import dataclass
from types import MappingProxyType
import pytest
from stratbox.capabilities.model import *
from stratbox.capabilities.catalog import Catalog, DomainCatalog, standard_catalog
from stratbox.capabilities.preparation import prepare
from stratbox.capabilities.plan import CommandTask, MapTask, RepeatTask
from stratbox.shared.data.values import Material, SourceClaim, IdentifiedMaterial, TableEvidenceSet

INT=PortContract('integer',int)
M=MethodRef('operator:neg')

def leaf(name, *, effects=frozenset()):
    return CommandDefinition(name,inputs={'value':INT},outputs={'value':INT},method=M,effects=effects)


def test_required_effect_survives_output_pruning_and_unused_method_is_not_bound():
    pure=leaf('command.test.pure')
    save=leaf('command.test.save',effects=frozenset({'write'}))
    missing=CommandDefinition('command.test.unavailable',inputs={'value':INT},outputs={'value':INT},specification_required=True)
    operation=OperationDefinition('operation.test',inputs={'value':INT},outputs={'result':INT},body=GraphBody((
        Call('compute',pure.id,{'value':InputRef('value')}),
        Call('save',save.id,{'value':OutputRef('compute','value')}),
        Call('unused',missing.id,{'value':InputRef('value')}),
    ),{'result':OutputRef('compute','value')},required_effects=('save',)))
    plan=prepare(operation.id,inputs={'value':2},catalog=Catalog({d.id:d for d in (pure,save,missing,operation)}))
    assert {t.command.id for t in plan.tasks}=={pure.id,save.id}
    assert plan.scopes[-1].required_effects==('root/save',)
    assert plan.outputs['result'].task_id=='root/compute'


def test_port_connection_rejects_wrong_type_before_method_loading():
    producer=leaf('command.test.source')
    consumer=CommandDefinition('command.test.text',inputs={'value':PortContract('text',str)},outputs={'value':INT},method=M)
    graph=OperationDefinition('operation.test',inputs={'value':INT},outputs={'value':INT},body=GraphBody((
        Call('a',producer.id,{'value':InputRef('value')}),Call('b',consumer.id,{'value':OutputRef('a')})),{'value':OutputRef('b')}))
    with pytest.raises(TypeError,match='port_mismatch'):
        prepare(graph.id,inputs={'value':3},catalog=Catalog({d.id:d for d in (producer,consumer,graph)}))


def test_runtime_type_covariance_and_source_guarantees_are_checked():
    assert not PortContract('n',int).compatible_with(PortContract('n',bool))
    assert PortContract('n',object).compatible_with(PortContract('n',int))
    a=SourceRequirement(frozenset({'A'}))
    b=SourceRequirement(frozenset({'B'}))
    assert not PortContract('d',source=a).compatible_with(PortContract('d',source=b))
    assert not PortContract('d',source=a).compatible_with(PortContract('d'))


def test_identified_requirement_rejects_assertion_and_missing_required_issue():
    material=Material(b'x',source_id='A')
    with pytest.raises(ValueError,match='identified_attribution'):
        SourceRequirement(frozenset({'A'})).validate(IdentifiedMaterial(material,SourceClaim('A')))
    with pytest.raises(ValueError,match='issue_conflict'):
        SourceRequirement(frozenset({'A'}),'2026-10').validate(material)


def test_known_source_b_cannot_fulfill_a_table_interpretation():
    spec=CommandSpec(MethodRef('operator:neg'))
    series=SeriesSpec('A',PublicationSpec('A'),ObservationSemantics(),{'command.table.interpret':spec})
    domain=DomainSpec('demo',{}, {'A':series})
    with pytest.raises(ValueError,match='context_conflict'):
        prepare('command.table.interpret',inputs={'tables':TableEvidenceSet((),source_id='B')},target='A',domains=DomainCatalog({'demo':domain}))


def test_frozen_settings_recursively_detach_mutable_children():
    @dataclass(frozen=True)
    class Settings:
        rules: object
    original={'units':['RUB']}
    spec=CommandSpec(M,Settings(original))
    original['units'].append('USD')
    assert spec.settings.rules['units']==('RUB',)
    with pytest.raises(TypeError): spec.settings.rules['other']='x'


def test_supplied_physical_cut_eliminates_material_and_decoder_requirements():
    from stratbox.shared.data.values import WorkbookEvidence
    spec=CommandSpec(M)
    series=SeriesSpec('A',PublicationSpec('A'),ObservationSemantics(),{
        'command.table.extract':spec,'command.table.interpret':spec})
    domain=DomainSpec('demo',{}, {'A':series})
    physical=WorkbookEvidence(Material(b'x',source_id='A'),None)
    plan=prepare('operation.series.extract_workbook',inputs={'physical':physical},target='A',domains=DomainCatalog({'demo':domain}))
    assert not any(t.command.id in {'command.workbook.decode','command.material.fetch'} for t in plan.tasks)
    assert plan.tasks[0].inputs['physical'].material.source_id=='A'


def test_kind_rules_and_graph_cycles_are_explicit():
    command=leaf('command.test')
    scenario=ScenarioDefinition('scenario.test',inputs={'value':INT},outputs={'value':INT},body=GraphBody((Call('a',command.id,{'value':InputRef('value')}),),{'value':OutputRef('a')}))
    with pytest.raises(ValueError,match='invalid_kind'):
        prepare(scenario.id,inputs={'value':1},catalog=Catalog({d.id:d for d in (command,scenario)}))
    operation=OperationDefinition('operation.test',inputs={},outputs={'value':INT},body=GraphBody((Call('a',command.id,{'value':OutputRef('b')}),Call('b',command.id,{'value':OutputRef('a')})),{'value':OutputRef('a')}))
    with pytest.raises(ValueError,match='cycle'):
        prepare(operation.id,catalog=Catalog({d.id:d for d in (command,operation)}))


def test_map_and_repeat_lower_to_bounded_structures_with_templates():
    command=leaf('command.test')
    graph=OperationDefinition('operation.test',outputs={'value':PortContract('result_collection',tuple)},body=GraphBody((MapCall('mapped',command.id,(1,2),item_input='value',output_port='value',max_items=3,window=1),),{'value':OutputRef('mapped','items')}))
    plan=prepare(graph.id,catalog=Catalog({d.id:d for d in (command,graph)}))
    assert isinstance(plan.tasks[0],MapTask)
    assert plan.tasks[0].window==1 and plan.tasks[0].max_items==3
    repeat=OperationDefinition('operation.repeat',inputs={'state':INT},outputs={'value':INT},body=GraphBody((RepeatUntil('r',GraphBody((Call('next',command.id,{'value':InputRef('state')}),),{'state':OutputRef('next')}),InputRef('state'),max_passes=2),),{'value':OutputRef('r','state')}))
    repeated=prepare(repeat.id,inputs={'state':1},catalog=Catalog({d.id:d for d in (command,repeat)}))
    assert isinstance(repeated.tasks[0],RepeatTask)
    assert repeated.tasks[0].max_passes==2


def test_catalog_has_explicit_structured_formula_and_no_component_versions():
    from dataclasses import fields
    catalog=standard_catalog()
    for name in ('command.calculate.formula','command.json.decode','command.dbf.decode','operation.series.extract_structured.json'):
        assert catalog.get(name).id==name
    assert not any('version' in f.name or 'revision' in f.name for f in fields(CommandDefinition))
    with pytest.raises(ValueError,match='conflicting_definition'):
        catalog.with_definitions(CommandDefinition('command.json.decode',outputs={'value':INT},method=M))
