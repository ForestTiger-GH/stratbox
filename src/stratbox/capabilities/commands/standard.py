"""Authored standard actions. Domain tables never generate definitions."""
from stratbox.shared.data import values as v
from ..model import CommandDefinition, PortContract, MethodRef, ReuseContract


def P(name, cls=object, *, required=True, role=None):
    return PortContract(name, cls, role=role, required=required)

MATERIAL = P('material', (v.Material, v.IdentifiedMaterial))
DATASET = P('dataset', v.SourceDataset)
PHYSICAL = P('physical', (v.WorkbookEvidence, v.DocumentEvidence, v.JsonEvidence, v.DbfEvidence, v.TableEvidenceSet))
ASSESSMENT = P('assessment', v.Assessment, required=False)


def C(identifier, inputs, outputs, *, resource='cpu', effects=(), providers=(), specialize=False, parameters=None):
    return CommandDefinition(
        identifier, inputs=inputs, outputs=outputs, parameters=parameters or {},
        method=MethodRef('stratbox.core.commands.standard:' + identifier.removeprefix('command.').replace('.', '_')),
        specification_required=specialize,
        resources=({resource: 1, 'cpu': 1} if resource in {'parse','solver','calculate','render'} else {resource: 1}), effects=frozenset(effects), required_providers=frozenset(providers),
        reuse=ReuseContract(deterministic=not bool(effects), shareable=not bool(effects), completed=not bool(effects)),
    )

# Each row is a distinct, reviewed action promise; the helper only normalizes syntax.
COMMANDS = (
    C('command.request.prepare', {'locator': P('locator', required=False), 'query': P('query', required=False)}, {'request': P('request', v.RequestSpec)}),
    C('command.material.list', {'location': P('location'), 'query': P('query', required=False)}, {'inventory': P('inventory', tuple)}, resource='storage_read', providers=('filestore',)),
    C('command.material.fetch', {'request': P('request', v.RequestSpec)}, {'material': MATERIAL, 'evidence': P('fetch_evidence', v.FetchEvidence, required=False)}, resource='network', effects=('network.read',), providers=('http',)),
    C('command.material.read', {'location': P('location')}, {'material': MATERIAL, 'evidence': P('read_evidence', required=False)}, resource='storage_read', providers=('filestore',)),
    C('command.material.identify', {'material': MATERIAL, 'claim': P('claim', v.SourceClaim, required=False)}, {'material': MATERIAL, 'assessment': ASSESSMENT}),
    C('command.publication.scan', {'index': P('index', (v.Material, v.IdentifiedMaterial, tuple))}, {'listing': P('listing', v.PublicationListing), 'coverage': ASSESSMENT}, specialize=True),
    C('command.issue.select', {'listing': P('listing', v.PublicationListing), 'query': P('query', required=False)}, {'selection': P('selection', v.AssetSelection)}),
    C('command.source.assess', {'evidence': P('source_evidence'), 'baseline': P('baseline', required=False)}, {'assessment': P('update_assessment', v.UpdateAssessment)}),
    C('command.archive.unpack', {'material': MATERIAL}, {'members': P('materials', tuple)}, resource='parse'),
    C('command.archive.pack', {'members': P('materials', tuple)}, {'material': MATERIAL}),
    C('command.workbook.decode', {'material': MATERIAL}, {'physical': P('physical', v.WorkbookEvidence)}, resource='parse'),
    C('command.document.decode', {'material': MATERIAL}, {'physical': P('physical', v.DocumentEvidence)}, resource='parse'),
    C('command.json.decode', {'material': MATERIAL}, {'physical': P('physical', v.JsonEvidence)}, resource='parse'),
    C('command.csv.decode', {'material': MATERIAL}, {'physical': P('physical', v.TableEvidenceSet)}, resource='parse'),
    C('command.dbf.decode', {'material': MATERIAL}, {'physical': P('physical', v.DbfEvidence)}, resource='parse'),
    C('command.document.convert', {'material': MATERIAL}, {'material': MATERIAL, 'evidence': P('conversion_evidence', required=False)}, resource='parse', providers=('document_converter',)),
    C('command.publication.transcribe', {'physical': PHYSICAL}, {'publication': P('readable')}),
    C('command.table.extract', {'physical': PHYSICAL}, {'tables': P('tables', v.TableEvidenceSet), 'coverage': ASSESSMENT}, resource='parse', specialize=True),
    C('command.table.interpret', {'tables': P('tables', v.TableEvidenceSet), 'issue': P('issue', required=False)}, {'dataset': DATASET, 'assessment': ASSESSMENT}, specialize=True),
    C('command.observations.validate', {'dataset': DATASET}, {'dataset': DATASET, 'assessment': ASSESSMENT}),
    C('command.observations.align', {'dataset': DATASET}, {'dataset': P('dataset', v.IntegratedDataset), 'assessment': ASSESSMENT}),
    C('command.observations.compare', {'before': DATASET, 'after': DATASET}, {'changes': P('changes'), 'assessment': ASSESSMENT}),
    C('command.dataset.query', {'reference': P('snapshot', v.SnapshotRef), 'query': P('query', required=False)}, {'observations': DATASET}, resource='storage_read', providers=('dataset_reader',)),
    C('command.timeseries.partition', {'dataset': DATASET}, {'items': P('timeseries_collection', tuple)}),
    C('command.timeseries.prepare', {'observations': DATASET}, {'series': P('timeseries', v.TimeSeries), 'assessment': ASSESSMENT}),
    C('command.timeseries.validate', {'series': P('timeseries', v.TimeSeries)}, {'assessment': P('assessment', v.Assessment)}),
    C('command.timeseries.adjust', {'series': P('timeseries', v.TimeSeries)}, {'adjustment': P('adjustment')}, resource='calculate'),
    C('command.timeseries.diagnose', {'adjustment': P('adjustment')}, {'diagnostics': P('diagnostics')}),
    C('command.calculate.change', {'observations': DATASET}, {'dataset': P('dataset', v.DerivedDataset)}, resource='calculate'),
    C('command.calculate.ratio', {'numerator': DATASET, 'denominator': DATASET}, {'dataset': P('dataset', v.DerivedDataset)}, resource='calculate'),
    C('command.calculate.index', {'observations': DATASET}, {'dataset': P('dataset', v.DerivedDataset)}, resource='calculate'),
    C('command.calculate.flow', {'observations': DATASET}, {'dataset': P('dataset', v.DerivedDataset)}, resource='calculate'),
    C('command.calculate.formula', {'dataset': DATASET}, {'dataset': P('dataset', v.DerivedDataset)}, resource='calculate'),
    C('command.model.inputs', {'datasets': P('model_sources')}, {'bundle': P('model_inputs')}, specialize=True),
    C('command.constraints.build', {'bundle': P('model_inputs')}, {'graph': P('constraint_graph'), 'state': P('inference_state')}, specialize=True),
    C('command.bounds.propagate', {'graph': P('constraint_graph'), 'state': P('inference_state')}, {'state': P('inference_state'), 'derivations': P('derivations', required=False)}, specialize=True),
    C('command.facts.inherit', {'graph': P('constraint_graph'), 'state': P('inference_state')}, {'candidates': P('candidate_facts')}, specialize=True),
    C('command.facts.reconcile', {'state': P('inference_state'), 'candidates': P('candidate_facts', required=False), 'optimization': P('optimization', required=False)}, {'state': P('inference_state'), 'assessment': ASSESSMENT}, specialize=True),
    C('command.model.compile', {'graph': P('constraint_graph'), 'state': P('inference_state')}, {'problem': P('compiled_problem')}, specialize=True),
    C('command.model.feasibility', {'problem': P('compiled_problem')}, {'feasibility': P('feasibility')}, resource='solver', specialize=True),
    C('command.bounds.optimize', {'problem': P('compiled_problem'), 'feasibility': P('feasibility'), 'state': P('inference_state', required=False), 'targets': P('targets', required=False)}, {'optimization': P('optimization')}, resource='solver', specialize=True),
    C('command.values.certify', {'state': P('inference_state'), 'feasibility': P('feasibility'), 'optimization': P('optimization', required=False)}, {'values': P('certified_values')}, specialize=True),
    C('command.observations.assemble', {'values': P('certified_values')}, {'dataset': P('dataset', v.DerivedDataset)}, specialize=True),
    C('command.view.prepare', {'dataset': DATASET}, {'view': P('view', v.View)}),
    C('command.product.render', {'view': P('view', v.View)}, {'product': P('product', v.EncodedProduct)}, resource='render'),
    C('command.value.encode', {'value': P('typed_value')}, {'representation': P('representation', (v.EncodedProduct, v.Material, bytes))}),
    C('command.value.decode', {'representation': P('representation', (v.EncodedProduct, v.Material, bytes))}, {'value': P('typed_value')}),
    C('command.artifact.commit', {'material': P('encoded_material', (v.EncodedProduct, v.Material, bytes)), 'destination': P('destination', required=False)}, {'reference': P('artifact', v.ImmutableMaterialRef), 'receipt': P('receipt', required=False)}, resource='storage_write', effects=('storage.write',), providers=('filestore',)),
    C('command.artifact.reconcile', {'effect': P('effect')}, {'assessment': P('effect_assessment')}, resource='storage_read', providers=('filestore',)),
    C('command.dataset.ingest', {'dataset': DATASET, 'destination': P('destination', required=False)}, {'reference': P('snapshot', v.SnapshotRef), 'receipt': P('receipt', required=False)}, resource='storage_write', effects=('dataset.write',), providers=('dataset_writer',)),
    C('command.release.assemble', {'members': P('accepted_members', tuple)}, {'manifest': P('release_manifest')}),
    C('command.release.publish', {'manifest': P('release_manifest'), 'expected_token': P('state_token', required=False)}, {'receipt': P('publication_receipt')}, resource='storage_write', effects=('publication.write',), providers=('filestore',)),
    C('command.material.maintenance_plan', {'inventory': P('inventory', tuple)}, {'plan': P('maintenance_plan')}),
    C('command.material.maintenance_apply', {'plan': P('maintenance_plan')}, {'receipts': P('effect_receipts', tuple)}, resource='storage_write', effects=('storage.write',), providers=('filestore',)),
    C('command.notification.prepare', {'facts': P('journal_facts', tuple)}, {'intents': P('notification_intents', tuple)}),
    C('command.notification.deliver', {'intent': P('notification_intent')}, {'receipt': P('delivery_receipt')}, resource='network', effects=('notification.deliver',), providers=('notification',)),
    C('command.notification.reconcile', {'receipt': P('delivery_receipt')}, {'assessment': P('delivery_assessment')}, providers=('notification',)),
)
BY_ID = {item.id: item for item in COMMANDS}
