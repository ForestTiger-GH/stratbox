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

def retained_dataset(source):
    from stratbox.shared.data.values import SourceDataset
    from stratbox.shared.data.source_context import SourceUse, SourceCoordinate
    from stratbox.shared.identity import ByteIdentity
    use=SourceUse(SourceCoordinate(source, material_identity=ByteIdentity.of(source.encode())),
                  'interpreted_source', 'domain_validated')
    return SourceDataset(source, (), source_uses=(use,))

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


def demo_domain():
    spec=CommandSpec(M)
    series=SeriesSpec('A',PublicationSpec('A',formats=frozenset({'xlsx'})),ObservationSemantics(),{
        'command.publication.scan':spec,'command.table.extract':spec,'command.table.interpret':spec})
    return DomainCatalog({'demo':DomainSpec('demo',{}, {'A':series})})


def test_full_refresh_contains_source_assessment_acquisition_and_two_bounded_maps():
    plan=prepare('scenario.series.refresh',target='A',domains=demo_domain())
    assert any(isinstance(t,CommandTask) and t.command.id=='command.source.assess' for t in plan.tasks)
    maps=[t for t in plan.tasks if isinstance(t,MapTask)]
    assert len(maps)==2
    transport=next(t for t in maps[0].template.tasks if t.kind=='dispatch')
    assert transport.selector_kind=='acquisition_kind'
    assert any(t.command.id=='command.material.fetch' for t in transport.alternatives['http'].tasks)
    assert any(t.command.id=='command.material.read' for t in transport.alternatives['file'].tasks)
    assert any(t.command.id=='command.workbook.decode' for t in maps[1].template.tasks)
    assert any(isinstance(t,CommandTask) and t.command.id=='command.observations.merge' for t in plan.tasks)


def test_supplied_listing_and_retained_dataset_eliminate_network():
    from stratbox.shared.data.values import PublicationListing, SourceDataset
    listing=PublicationListing('demo',())
    check=prepare('operation.source.check',inputs={'listing':listing},target='A',domains=demo_domain())
    assert not any(t.command.id=='command.material.fetch' for t in check.tasks)
    retained=prepare('scenario.series.refresh',inputs={'dataset':retained_dataset('A')},target='A',domains=demo_domain())
    assert [t.command.id for t in retained.tasks]==['command.observations.validate']
    assert retained.outputs['dataset'].task_id=='root/retained/validate'


def test_retention_goal_survives_selecting_only_dataset():
    from stratbox.shared.data.values import SourceDataset
    plan=prepare('scenario.series.refresh',inputs={'dataset':retained_dataset('A'),'destination':'saved.json'},
        target='A',domains=demo_domain(),outputs=('dataset',))
    assert {task.command.id for task in plan.tasks}=={'command.observations.validate','command.value.encode','command.artifact.commit'}
    assert plan.outputs.keys()=={'dataset'}


def test_network_read_has_observation_reuse_but_writes_do_not():
    catalog=standard_catalog()
    fetch=catalog.get('command.material.fetch')
    save=catalog.get('command.artifact.commit')
    assert fetch.reuse.observation_scoped and fetch.reuse.inflight_eligible
    assert not fetch.reuse.completed_eligible
    assert not save.reuse.inflight_eligible
    assert catalog.get('command.calculate.formula').resources=={'cpu':1}
    assert catalog.get('command.model.feasibility').resources=={'cpu':1,'solver':1}


def test_document_conversion_and_archive_collection_are_visible_standard_steps():
    from dataclasses import dataclass
    @dataclass(frozen=True)
    class Publication:
        id: str
        formats: frozenset
        archive_mode: str = 'single'
    specs={name:CommandSpec(M) for name in ('command.table.extract','command.table.interpret')}
    doc=SeriesSpec('DOC',Publication('DOC',frozenset({'doc'})),ObservationSemantics(),specs)
    archive=SeriesSpec('ZIP',Publication('ZIP',frozenset({'zip'}),'workbook_collection'),ObservationSemantics(),specs)
    domains=DomainCatalog({'demo':DomainSpec('demo',{}, {'DOC':doc,'ZIP':archive})})
    converted=prepare('operation.series.extract_document',inputs={'material':Material(b'doc',source_id='DOC')},target='DOC',domains=domains)
    assert [t.command.id for t in converted.tasks][:2]==['command.document.convert','command.document.decode']
    packed=prepare('operation.series.extract_archive',inputs={'material':Material(b'zip',source_id='ZIP')},target='ZIP',domains=domains)
    maps=[t for t in packed.tasks if isinstance(t,MapTask)]
    assert len(maps)==1 and maps[0].template.tasks[0].command.id=='command.workbook.decode'
    assert sum(getattr(getattr(t,'command',None),'id',None)=='command.table.interpret' for t in packed.tasks)==1


def test_unused_nested_output_does_not_keep_unrequested_backend():
    pure=leaf('command.test.pure')
    expensive=CommandDefinition('command.test.expensive',inputs={'value':INT},outputs={'value':INT},specification_required=True)
    child=OperationDefinition('operation.child',inputs={'value':INT},outputs={'primary':INT,'extra':INT},body=GraphBody((
        Call('p',pure.id,{'value':InputRef('value')}),Call('x',expensive.id,{'value':InputRef('value')})),
        {'primary':OutputRef('p'),'extra':OutputRef('x')}))
    parent=OperationDefinition('operation.parent',inputs={'value':INT},outputs={'value':INT},body=GraphBody((
        Call('c',child.id,{'value':InputRef('value')}),Call('unused',pure.id,{'value':OutputRef('c','extra')})),
        {'value':OutputRef('c','primary')}))
    plan=prepare(parent.id,inputs={'value':1},catalog=Catalog({d.id:d for d in (pure,expensive,child,parent)}))
    assert [t.command.id for t in plan.tasks]==[pure.id]


def test_retained_dataset_cannot_bypass_target_and_cascade_freezes_member_targets():
    from stratbox.capabilities.preparation import InvocationRequest
    from stratbox.shared.data.values import SourceDataset
    domains=demo_domain()
    with pytest.raises(ValueError,match='context_conflict'):
        prepare('scenario.series.refresh',inputs={'dataset':SourceDataset('B',())},target='A',domains=domains)
    spec=SeriesSpec('B',PublicationSpec('B'),ObservationSemantics(),{})
    original=domains.domains['demo']
    domains=DomainCatalog({'demo':DomainSpec('demo',{}, {'A':original.series['A'],'B':spec})})
    members=(InvocationRequest('scenario.series.refresh',inputs={'dataset':retained_dataset('A')},target='A'),
             InvocationRequest('scenario.series.refresh',inputs={'dataset':retained_dataset('B')},target='B'))
    plan=prepare('cascade.sources.refresh',inputs={'members':members},domains=domains)
    commands=[t.command for t in plan.tasks if isinstance(t,CommandTask)]
    assert [c.parameters['source_id'] for c in commands]==['A','B']
    assert len([s for s in plan.scopes if s.kind=='scenario'])==2


def test_nested_conditions_are_conjoined_and_keep_condition_producers_in_closure():
    command=leaf('command.test')
    child=OperationDefinition('operation.child',inputs={'value':INT},outputs={'value':INT},body=GraphBody((
        Call('x',command.id,{'value':InputRef('value')},condition=Condition(True)),),{'value':OutputRef('x')}))
    parent=OperationDefinition('operation.parent',inputs={'value':INT},outputs={'value':INT},body=GraphBody((
        Call('flag',command.id,{'value':InputRef('value')}),
        Call('child',child.id,{'value':InputRef('value')},condition=Condition(OutputRef('flag'),equals=1))),{'value':OutputRef('child')}))
    plan=prepare(parent.id,inputs={'value':1},catalog=Catalog({d.id:d for d in (command,child,parent)}))
    nested=next(t for t in plan.tasks if t.task_id.endswith('/x'))
    assert len(nested.condition)==2
    assert 'root/flag' in nested.deps


def test_seasonal_provider_requirement_is_declared_before_execution():
    assert standard_catalog().get('command.timeseries.adjust').required_providers==frozenset({'seasonal_adjustment'})
    assert standard_catalog().get('command.notification.prepare').effects==frozenset({'notification.state'})


def test_refresh_assessment_can_be_requested_without_exporting_dataset():
    plan=prepare('scenario.series.refresh',inputs={'dataset':retained_dataset('A')},
        target='A',domains=demo_domain(),outputs=('assessment',))
    assert plan.outputs.keys()=={'assessment'}
    assert plan.outputs['assessment'].path=='assessment'
    assert [task.command.id for task in plan.tasks]==['command.observations.validate']


def test_supplied_table_entrance_needs_no_transport_or_physical_decoder():
    table=TableEvidenceSet((),material=Material(b'table',source_id='A'),source_id='A')
    plan=prepare('scenario.series.refresh',inputs={'tables':table},target='A',domains=demo_domain())
    assert [task.command.id for task in plan.tasks]==['command.table.interpret','command.observations.validate']


def test_incomplete_selected_publication_cannot_be_acquired():
    from stratbox.shared.data.values import AssetSelection, PublicationAsset, Assessment
    asset=PublicationAsset('A','2026-11-01','main','https://example.org/table.xlsx','xlsx')
    selection=AssetSelection((asset,),Assessment('partial',('index.unresolved',)))
    with pytest.raises(ValueError,match='selection_incomplete'):
        prepare('operation.series.acquire',inputs={'selection':selection},target='A',domains=demo_domain())


def test_map_parameter_limits_cannot_deadlock_or_remove_bounds():
    command=leaf('command.test')
    operation=OperationDefinition('operation.test', outputs={'items':PortContract('result_collection',tuple)},
        body=GraphBody((MapCall('map',command.id,(1,),item_input='value',output_port='value'),),
            {'items':OutputRef('map','items')}))
    catalog=Catalog({d.id:d for d in (command,operation)})
    for parameters in ({'window':0},{'max_items':-1},{'completion':'anything'}):
        with pytest.raises(ValueError,match='invalid_map'):
            prepare(operation.id,catalog=catalog,parameters=parameters)


def test_feed_and_series_targets_resolve_their_actual_record_kinds():
    from stratbox.capabilities.model.targets import FeedTarget, SeriesTarget
    publication=PublicationSpec('A',commands={'command.publication.scan':CommandSpec(M)})
    series=SeriesSpec('A',publication,ObservationSemantics(),{'command.table.interpret':CommandSpec(M)})
    domains=DomainCatalog({'demo':DomainSpec('demo',{'publications':{'A':publication}}, {'A':series})})
    assert domains.get('A',kind='feed') is domains.domains['demo'].common['publications']['A']
    assert domains.get('A',kind='series') is domains.domains['demo'].series['A']
    assert prepare('operation.source.check',inputs={'index':Material(b'index')},target=FeedTarget('A'),domains=domains)
    with pytest.raises(ValueError,match='specification_required'):
        prepare('command.table.interpret',inputs={'tables':TableEvidenceSet(())},target=FeedTarget('A'),domains=domains)


def test_every_standard_command_has_one_reference_route_stage():
    from stratbox.capabilities.route.stages import STAGES
    from stratbox.capabilities.commands.standard import COMMANDS
    classified=tuple(command for stage in STAGES.values() for command in stage)
    assert len(classified)==len(set(classified))
    assert set(classified)=={command.id for command in COMMANDS}


def test_notification_delivery_can_acknowledge_state_without_requiring_a_subscription():
    delivery=standard_catalog().get('command.notification.deliver')
    assert delivery.effects==frozenset({'notification.deliver','notification.state'})
    assert delivery.required_providers==frozenset({'notification'})
    assert delivery.optional_providers==frozenset({'notification_state'})
