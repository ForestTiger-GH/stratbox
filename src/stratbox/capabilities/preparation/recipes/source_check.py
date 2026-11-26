"""Pure topology-aware finite source checks with reusable acquired evidence."""
from dataclasses import replace
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from stratbox.shared.data.values import Assessment, PublicationAsset, PublicationListing, UpdateAssessment
from ...model import Call, GraphBody, InputRef, OutputRef
from ...commands.standard import P, READABLE


def _direct(definition, values, parameters, publication, descriptor):
    settings = getattr(publication,'settings',None)
    locator = getattr(publication,'locator',None) or getattr(settings,'locator',None) or getattr(publication,'landing_url',None)
    if locator is None:
        raise ValueError('source.declared_locator_required')
    source_id = descriptor.source_id
    suffix = PurePosixPath(urlsplit(locator).path).suffix.lstrip('.').lower()
    fmt = suffix if suffix in descriptor.formats else next(iter(descriptor.formats)) if len(descriptor.formats) == 1 else 'unknown'
    asset = PublicationAsset(source_id,'','main',locator,fmt,{'discovery':'declared_candidate'})
    listing = PublicationListing(descriptor.publisher_id,(asset,),
        Assessment(qualifications=frozenset({'declared_candidate','remote_listing_unobserved'})))
    # A resolved empty request is a finite no-work selection. Checking a known
    # fixed endpoint must not download an explicitly excluded publication.
    from stratbox.shared.data.selection import select_publication_assets
    from ...plan import TemplateInput, ValueRef
    query = values.get('query')
    if not isinstance(query, (TemplateInput, ValueRef)):
        selected, report = select_publication_assets(listing,query,source_ids=(source_id,))
        if not selected.entries:
            outputs = {'assessment':UpdateAssessment('unknown','declared_candidate',
                ('source.selected_scope_empty','source.remote_unobserved'),evidence=report),
                'evidence':listing,'listing':listing,'selection':OutputRef('select','selection'),
                'report':OutputRef('select','report')}
            return replace(definition,outputs={**definition.outputs,'evidence':P('listing',PublicationListing),
                'listing':P('listing',PublicationListing),'report':P('selection_report',required=False)},
                body=GraphBody((Call('select','command.issue.select',{'listing':listing,'query':InputRef('query')}),),
                    outputs,required_completions=('select',)))
    steps = [Call('select','command.issue.select',{'listing':listing,'query':InputRef('query')}),
        Call('request','command.request.prepare',{'locator':InputRef('locator'),'query':InputRef('query')},{'role':'asset'})]
    if 'material' in values:
        carrier = InputRef('material')
        identify = {'material':carrier,'inspection':OutputRef('inspect','inspection')}
    else:
        steps.append(Call('fetch','command.material.fetch',{'request':OutputRef('request','request'),'retained':InputRef('retained')}))
        carrier = OutputRef('fetch','material')
        identify = {'material':carrier,'request':OutputRef('fetch','request'),
            'evidence':OutputRef('fetch','evidence'),'inspection':OutputRef('inspect','inspection')}
    assess = {'evidence':OutputRef('identify','material'),'baseline':InputRef('baseline'),'query':InputRef('query')}
    if 'material' not in values:
        assess['acquisition_evidence'] = OutputRef('fetch','evidence')
    steps.extend((Call('inspect','command.material.inspect',{'material':carrier}),
        Call('identify','command.material.identify',identify),
        Call('assess','command.source.assess',assess)))
    outputs = {'assessment':OutputRef('assess','assessment'),'evidence':OutputRef('identify','material'),
        'material':OutputRef('identify','material'),'listing':listing,
        'selection':OutputRef('select','selection'),'report':OutputRef('select','report')}
    return replace(definition,outputs={**definition.outputs,'evidence':READABLE,'material':READABLE,
        'listing':P('listing',PublicationListing),'report':P('selection_report',required=False)},
        body=GraphBody(tuple(steps),outputs,required_completions=('assess','identify','select')))


def source(definition, values, parameters, record, catalog=None):
    from ...commands.standard import BY_ID
    definition=replace(definition,inputs={**definition.inputs,'index':P('index',required=False),
        'listing':P('listing',required=False),'location':P('location',required=False),
        'material':replace(READABLE,required=False),'retained':BY_ID['command.material.fetch'].inputs['retained']})
    publication = getattr(record,'publication',record)
    descriptor = getattr(publication,'descriptor',None)
    if (descriptor is not None and descriptor.delivery_mode == 'fixed_url'
            and not {'index','listing','location'} & values.keys()):
        return _direct(definition,values,parameters,publication,descriptor)
    steps=[]
    if 'listing' in values:
        listing=InputRef('listing');evidence=InputRef('listing')
    else:
        if 'index' in values:
            index=InputRef('index')
        elif 'location' in values:
            steps.append(Call('list','command.material.list',{'location':InputRef('location'),'query':InputRef('query')}))
            index=OutputRef('list','inventory')
        else:
            steps.extend((Call('request','command.request.prepare',{'locator':InputRef('locator'),'query':InputRef('query')},{'role':'index'}),
                Call('fetch','command.material.fetch',{'request':OutputRef('request','request')},{'placement':'buffered'})))
            index=OutputRef('fetch','material')
        steps.append(Call('scan','command.publication.scan',{'index':index}))
        listing=OutputRef('scan','listing');evidence=index
    steps.extend((Call('select','command.issue.select',{'listing':listing,'query':InputRef('query')}),
        Call('assess','command.source.assess',{'evidence':listing,'baseline':InputRef('baseline'),'query':InputRef('query')})))
    return replace(definition,outputs={**definition.outputs,
        'evidence':P('listing' if 'listing' in values else 'inventory' if 'location' in values else 'material'),
        'listing':P('listing',PublicationListing),'report':P('selection_report',required=False)},
        body=GraphBody(tuple(steps),{'assessment':OutputRef('assess','assessment'),'evidence':evidence,
            'listing':listing,'selection':OutputRef('select','selection'),'report':OutputRef('select','report')},required_completions=('assess',)))
