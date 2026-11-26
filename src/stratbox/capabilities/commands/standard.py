"""Authored standard actions. Domain tables never generate definitions."""
from stratbox.shared.data import values as v
from stratbox.shared.data.journal import JournalPage
from ..model import CommandDefinition, PortContract, MethodRef, ReuseContract


def P(name, cls=object, *, required=True, role=None):
    return PortContract(name, cls, role=role, required=required)

MATERIAL = P('material', (v.Material, v.IdentifiedMaterial))
DATASET = P('dataset', v.SourceDataset)
PHYSICAL = PortContract('physical',(v.WorkbookEvidence,v.DocumentEvidence,v.JsonEvidence,v.DbfEvidence,v.TableEvidenceSet,tuple),alternatives=frozenset({'result_collection'}),element_types=(v.WorkbookEvidence,v.DocumentEvidence,v.JsonEvidence,v.DbfEvidence,v.TableEvidenceSet))
ASSESSMENT = P('assessment', v.Assessment, required=False)


def C(identifier, inputs, outputs, *, handler, resource='cpu', resources=None, effects=(), providers=(), optional_providers=(), specialize=False, parameters=None, observes_mutable_state=False):
    return CommandDefinition(
        identifier, inputs=inputs, outputs=outputs, parameters=parameters or {},
        method=MethodRef(handler),
        specification_required=specialize,
        optional_providers=frozenset(optional_providers),
        resources=resources if resources is not None else ({'cpu':1,'parse':1,'converter':1} if resource=='converter' else {'cpu': 1} if resource == 'calculate' else {resource: 1, 'cpu': 1} if resource in {'parse','solver','render'} else {resource: 1}), effects=frozenset(effects), required_providers=frozenset(providers),
        reuse=ReuseContract(deterministic=not bool(effects) and not observes_mutable_state,
            shareable=(not bool(effects) or effects == ('network.read',)) and not observes_mutable_state,
            completed=not bool(effects) and not observes_mutable_state, observation_scoped=effects == ('network.read',)),
    )

# Each row is a distinct, reviewed action promise; the helper only normalizes syntax.
COMMANDS = (
    C('command.request.prepare', {'locator': P('locator', required=False), 'query': P('query', required=False), 'selection':P('selection',v.AssetSelection,required=False)}, {'request': P('request', v.RequestSpec)}, handler='stratbox.core.commands.materials:request_prepare'),
    C('command.material.list', {'location': P('location'), 'query': P('query', required=False)}, {'inventory': P('inventory', tuple)}, resource='storage_read', providers=('filestore',), observes_mutable_state=True, handler='stratbox.core.commands.materials:material_list'),
    C('command.material.fetch', {'request': P('request', v.RequestSpec)}, {'material': MATERIAL, 'evidence': P('fetch_evidence', v.FetchEvidence, required=False)}, resource='network', effects=('network.read',), providers=('http',), handler='stratbox.core.commands.materials:material_fetch'),
    C('command.material.receive', {'request':P('request',v.RequestSpec),'destination':P('destination')},
        {'reference':P('artifact',v.ImmutableMaterialRef),'evidence':P('fetch_evidence',v.FetchEvidence),'receipt':P('receipt')},
        resources={'network':1,'storage_write':1},effects=('network.read','storage.write'),providers=('http','filestore'), handler='stratbox.core.commands.materials:material_receive'),
    C('command.material.select', {'materials':P('materials',tuple)}, {'materials':P('materials',tuple),'assessment':ASSESSMENT}, handler='stratbox.core.commands.materials:material_select'),
    C('command.material.read', {'location':PortContract('location',alternatives=frozenset({'artifact'}))}, {'material': MATERIAL, 'evidence': P('read_evidence',v.ReadEvidence,required=False)}, resource='storage_read', providers=('filestore',), observes_mutable_state=True, handler='stratbox.core.commands.materials:material_read'),
    C('command.material.identify', {'material': MATERIAL, 'claim': P('claim', v.SourceClaim, required=False),'request':P('request',v.RequestSpec,required=False),'evidence':PortContract('acquisition_evidence',(v.FetchEvidence,v.ReadEvidence),required=False,alternatives=frozenset({'fetch_evidence','read_evidence'})),'asset':P('asset',v.PublicationAsset,required=False)}, {'material': MATERIAL, 'assessment': ASSESSMENT}, handler='stratbox.core.commands.materials:material_identify'),
    C('command.publication.scan', {'index': PortContract('index',(v.Material,v.IdentifiedMaterial,tuple),alternatives=frozenset({'material','inventory'}))}, {'listing': P('listing', v.PublicationListing), 'coverage': ASSESSMENT}, specialize=True, handler='stratbox.core.commands.publications:publication_scan'),
    C('command.issue.select', {'listing': P('listing', v.PublicationListing), 'query': P('query', required=False)}, {'selection': P('selection', v.AssetSelection)}, handler='stratbox.core.commands.publications:issue_select'),
    C('command.source.assess', {'evidence': PortContract('source_evidence',alternatives=frozenset({'material','listing','selection','inventory'})), 'baseline': P('baseline', required=False)}, {'assessment': P('update_assessment', v.UpdateAssessment)}, handler='stratbox.core.commands.publications:source_assess'),
    C('command.archive.unpack', {'material': MATERIAL}, {'members': P('materials', tuple)}, resource='parse',optional_providers=('archive_reader',), handler='stratbox.core.commands.archives:archive_unpack'),
    C('command.archive.pack', {'members': P('materials', tuple)}, {'material': MATERIAL}, handler='stratbox.core.commands.archives:archive_pack'),
    C('command.workbook.decode', {'material': MATERIAL}, {'physical': P('physical', v.WorkbookEvidence)}, resource='parse', handler='stratbox.core.commands.decoding:workbook_decode'),
    C('command.document.decode', {'material': MATERIAL}, {'physical': P('physical', v.DocumentEvidence)}, resource='parse', handler='stratbox.core.commands.decoding:document_decode'),
    C('command.json.decode', {'material': MATERIAL}, {'physical': P('physical', v.JsonEvidence)}, resource='parse', handler='stratbox.core.commands.decoding:json_decode'),
    C('command.csv.decode', {'material': MATERIAL}, {'physical': P('physical', v.TableEvidenceSet)}, resource='parse', handler='stratbox.core.commands.decoding:csv_decode'),
    C('command.dbf.decode', {'material': MATERIAL}, {'physical': P('physical', v.DbfEvidence)}, resource='parse', handler='stratbox.core.commands.decoding:dbf_decode'),
    C('command.document.convert', {'material': MATERIAL}, {'material': MATERIAL, 'evidence': P('conversion_evidence', required=False)}, resource='converter', providers=('document_converter',), handler='stratbox.core.commands.decoding:document_convert'),
    C('command.publication.transcribe', {'physical': PHYSICAL}, {'publication': P('readable')}, handler='stratbox.core.commands.publications:publication_transcribe'),
    C('command.table.extract', {'physical': PHYSICAL}, {'tables': P('tables', v.TableEvidenceSet), 'coverage': ASSESSMENT}, resource='parse', specialize=True, handler='stratbox.core.commands.observations:table_extract'),
    C('command.table.interpret', {'tables': P('tables', v.TableEvidenceSet), 'issue': P('issue', required=False)}, {'dataset': DATASET, 'assessment': ASSESSMENT}, specialize=True, handler='stratbox.core.commands.observations:table_interpret'),
    C('command.observations.validate', {'dataset': DATASET}, {'dataset': DATASET, 'assessment': ASSESSMENT}, handler='stratbox.core.commands.observations:observations_validate'),
    C('command.observations.align', {'dataset': DATASET}, {'dataset': P('dataset', v.IntegratedDataset), 'assessment': ASSESSMENT}, handler='stratbox.core.commands.observations:observations_align'),
    C('command.observations.merge', {'datasets':PortContract('datasets',tuple,alternatives=frozenset({'result_collection'}))}, {'dataset': DATASET, 'assessment': ASSESSMENT}, handler='stratbox.core.commands.observations:observations_merge'),
    C('command.observations.compare', {'before': DATASET, 'after': DATASET}, {'changes': P('changes'), 'assessment': ASSESSMENT}, handler='stratbox.core.commands.calculations:observations_compare'),
    C('command.dataset.query', {'reference': P('snapshot', v.SnapshotRef), 'query': P('query', required=False)}, {'observations': DATASET}, resource='storage_read', providers=('dataset_reader',), handler='stratbox.core.commands.datasets:dataset_query'),
    C('command.timeseries.partition', {'dataset': DATASET}, {'items': P('timeseries_collection', tuple)}, handler='stratbox.core.commands.timeseries:timeseries_partition'),
    C('command.timeseries.prepare', {'observations': DATASET}, {'series': P('timeseries', v.TimeSeries), 'assessment': ASSESSMENT}, handler='stratbox.core.commands.timeseries:timeseries_prepare'),
    C('command.timeseries.validate', {'series': P('timeseries', v.TimeSeries)}, {'assessment': P('assessment', v.Assessment)}, handler='stratbox.core.commands.timeseries:timeseries_validate'),
    C('command.timeseries.adjust', {'series': P('timeseries', v.TimeSeries)}, {'adjustment': P('adjustment',v.TimeSeriesAdjustment)}, resource='calculate', providers=('seasonal_adjustment',), handler='stratbox.core.commands.timeseries:timeseries_adjust'),
    C('command.timeseries.diagnose', {'adjustment': P('adjustment',v.TimeSeriesAdjustment)}, {'diagnostics': P('diagnostics',v.AdjustmentDiagnostics)},optional_providers=('seasonal_adjustment',), handler='stratbox.core.commands.timeseries:timeseries_diagnose'),
    C('command.calculate.change', {'observations': DATASET}, {'dataset': P('dataset', v.DerivedDataset)}, resource='calculate', handler='stratbox.core.commands.calculations:calculate_change'),
    C('command.calculate.ratio', {'numerator': DATASET, 'denominator': DATASET}, {'dataset': P('dataset', v.DerivedDataset)}, resource='calculate', handler='stratbox.core.commands.calculations:calculate_ratio'),
    C('command.calculate.index', {'observations': DATASET}, {'dataset': P('dataset', v.DerivedDataset)}, resource='calculate', handler='stratbox.core.commands.calculations:calculate_index'),
    C('command.calculate.flow', {'observations': DATASET}, {'dataset': P('dataset', v.DerivedDataset)}, resource='calculate', handler='stratbox.core.commands.calculations:calculate_flow'),
    C('command.calculate.formula', {'dataset': DATASET}, {'dataset': P('dataset', v.DerivedDataset)}, resource='calculate', handler='stratbox.core.commands.calculations:calculate_formula'),
    C('command.model.inputs', {'datasets': P('model_sources')}, {'bundle': P('model_inputs')}, specialize=True, handler='stratbox.core.commands.models:model_specification_required'),
    C('command.constraints.build', {'bundle': P('model_inputs')}, {'graph': P('constraint_graph'), 'state': P('inference_state')}, specialize=True, handler='stratbox.core.commands.models:model_specification_required'),
    C('command.bounds.propagate', {'graph': P('constraint_graph'), 'state': P('inference_state')}, {'state': P('inference_state'), 'derivations': P('derivations', required=False)}, specialize=True, handler='stratbox.core.commands.models:model_specification_required'),
    C('command.facts.inherit', {'graph': P('constraint_graph'), 'state': P('inference_state')}, {'candidates': P('candidate_facts')}, specialize=True, handler='stratbox.core.commands.models:model_specification_required'),
    C('command.facts.reconcile', {'state': P('inference_state'), 'candidates': P('candidate_facts', required=False), 'optimization': P('optimization', required=False)}, {'state': P('inference_state'), 'assessment': ASSESSMENT}, specialize=True, handler='stratbox.core.commands.models:model_specification_required'),
    C('command.model.compile', {'graph': P('constraint_graph'), 'state': P('inference_state')}, {'problem': P('compiled_problem')}, specialize=True, handler='stratbox.core.commands.models:model_specification_required'),
    C('command.model.feasibility', {'problem': P('compiled_problem')}, {'feasibility': P('feasibility')}, resource='solver', specialize=True, handler='stratbox.core.commands.models:model_specification_required'),
    C('command.bounds.optimize', {'problem': P('compiled_problem'), 'feasibility': P('feasibility'), 'state': P('inference_state', required=False), 'targets': P('targets', required=False)}, {'optimization': P('optimization')}, resource='solver', specialize=True, handler='stratbox.core.commands.models:model_specification_required'),
    C('command.values.certify', {'state': P('inference_state'), 'feasibility': P('feasibility'), 'optimization': P('optimization', required=False)}, {'values': P('certified_values')}, specialize=True, handler='stratbox.core.commands.models:model_specification_required'),
    C('command.observations.assemble', {'values': P('certified_values')}, {'dataset': P('dataset', v.DerivedDataset)}, specialize=True, handler='stratbox.core.commands.models:model_specification_required'),
    C('command.view.prepare', {'dataset': DATASET}, {'view': P('view', v.View)}, handler='stratbox.core.commands.products:view_prepare'),
    C('command.product.render', {'view': P('view', v.View)}, {'product': P('product', v.EncodedProduct)}, resource='render',optional_providers=('renderer',), handler='stratbox.core.commands.products:product_render'),
    C('command.value.encode', {'value': PortContract('typed_value',alternatives=frozenset({'dataset','view','physical','tables','timeseries','certified_values'}))}, {'representation': P('representation', (v.EncodedProduct, v.Material, bytes))}, handler='stratbox.core.commands.serialization:value_encode'),
    C('command.value.decode', {'representation': P('representation', (v.EncodedProduct, v.Material, bytes))}, {'value': PortContract('typed_value',alternatives=frozenset({'dataset','view','physical','tables','timeseries','certified_values'}))}, handler='stratbox.core.commands.serialization:value_decode'),
    C('command.artifact.commit', {'material': PortContract('encoded_material',(v.EncodedProduct,v.Material,bytes),alternatives=frozenset({'product','representation','material'})), 'destination': P('destination', required=False)}, {'reference': P('artifact', v.ImmutableMaterialRef), 'receipt': P('receipt', required=False)}, resource='storage_write', effects=('storage.write',), providers=('filestore',), handler='stratbox.core.commands.artifacts:artifact_commit'),
    C('command.artifact.reconcile', {'effect': P('effect')}, {'assessment': P('effect_assessment')}, resource='storage_read', providers=('filestore',), observes_mutable_state=True, handler='stratbox.core.commands.artifacts:artifact_reconcile'),
    C('command.dataset.ingest', {'dataset': DATASET, 'destination': P('destination', required=False)}, {'reference': P('snapshot', v.SnapshotRef), 'receipt': P('receipt', required=False)}, resource='storage_write', effects=('dataset.write',), providers=('dataset_writer',), handler='stratbox.core.commands.datasets:dataset_ingest'),
    C('command.release.assemble', {'members': P('accepted_members', tuple)}, {'manifest': P('release_manifest')},providers=('filestore',), observes_mutable_state=True, handler='stratbox.core.commands.releases:release_assemble'),
    C('command.release.publish', {'manifest': P('release_manifest'), 'expected_token': P('state_token', required=False)}, {'receipt': P('publication_receipt')}, resource='storage_write', effects=('publication.write',), providers=('filestore',), handler='stratbox.core.commands.releases:release_publish'),
    C('command.material.maintenance_plan', {'inventory': P('inventory', tuple)}, {'plan': P('maintenance_plan')}, handler='stratbox.core.commands.maintenance:material_maintenance_plan'),
    C('command.material.maintenance_apply', {'plan': P('maintenance_plan')}, {'receipts': P('effect_receipts', tuple)}, resource='storage_write', effects=('storage.write',), providers=('filestore',), handler='stratbox.core.commands.maintenance:material_maintenance_apply'),
    C('command.notification.prepare', {'facts':P('journal_facts',(tuple,JournalPage),required=False),
        'page':P('journal_page',JournalPage,required=False)}, {'intents': P('notification_intents', tuple)},
        effects=('notification.state',), providers=('notification_state',), handler='stratbox.core.commands.notifications:notification_prepare'),
    C('command.notification.deliver', {'intent': P('notification_intent')}, {'receipt': P('delivery_receipt')},
        resource='network',effects=('notification.deliver','notification.state'),providers=('notification',),
        optional_providers=('notification_state',), handler='stratbox.core.commands.notifications:notification_deliver'),
    C('command.notification.reconcile', {'receipt': P('delivery_receipt')}, {'assessment': P('delivery_assessment')}, providers=('notification',), observes_mutable_state=True, handler='stratbox.core.commands.notifications:notification_reconcile'),
)
BY_ID = {item.id: item for item in COMMANDS}
