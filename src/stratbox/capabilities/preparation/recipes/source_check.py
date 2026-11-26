"""Pure authoring-time graph recipes for source check purposes."""

from dataclasses import replace

from ...model import Call, GraphBody, InputRef, OutputRef

from ...commands.standard import P

def source(definition, values, parameters, record, catalog=None):
    definition=replace(definition,inputs={**definition.inputs,'index':P('index',required=False),'listing':P('listing',required=False),'location':P('location',required=False)})
    # Supplied listing and index are legal entrances, including delivered inventories.
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
                Call('fetch','command.material.fetch',{'request':OutputRef('request','request')})))
            index=OutputRef('fetch','material')
        steps.append(Call('scan','command.publication.scan',{'index':index}))
        listing=OutputRef('scan','listing');evidence=index
    steps.extend((Call('select','command.issue.select',{'listing':listing,'query':InputRef('query')}),
        Call('assess','command.source.assess',{'evidence':listing,'baseline':InputRef('baseline')})))
    return replace(definition,outputs={**definition.outputs,'evidence':P('listing' if 'listing' in values else 'inventory' if 'location' in values else 'material')},body=GraphBody(tuple(steps),{'assessment':OutputRef('assess','assessment'),'evidence':evidence,'selection':OutputRef('select','selection')},required_completions=('assess',)))
