"""Finite retention and requested delivery graphs with explicit late entrances."""
from dataclasses import replace

from ...commands.standard import BY_ID, P
from ...model import Call, GraphBody, InputRef, OutputRef


def _named(definition, values, *, reference):
    if 'named_destination' not in values:
        return definition
    step = Call('materialize','command.artifact.materialize',{
        'material':reference,'destination':InputRef('named_destination'),
        'expected_destination':InputRef('expected_destination'),'retained_ancestor':reference})
    return replace(definition,inputs={**definition.inputs,
        'named_destination':P('destination'),'expected_destination':P('byte_identity',required=False)},
        outputs={**definition.outputs,'delivery_receipt':P('receipt')},
        body=replace(definition.body,steps=(*definition.body.steps,step),
            outputs={**definition.body.outputs,'delivery_receipt':OutputRef('materialize','receipt')},
            required_effects=(*definition.body.required_effects,'materialize')))


def archive(definition, values, parameters, record, catalog=None):
    return _named(definition,values,reference=OutputRef('save','reference'))


def product(definition, values, parameters, record, catalog=None):
    # Retained products can be delivered without loading a dataset or rendering.
    if 'reference' in values:
        definition = replace(definition,inputs={
            'reference':BY_ID['command.artifact.commit'].outputs['reference'],
            'named_destination':P('destination'),'expected_destination':P('byte_identity',required=False)},
            entrances={},outputs={'reference':BY_ID['command.artifact.commit'].outputs['reference']},
            body=GraphBody((),{'reference':InputRef('reference')}))
        if 'named_destination' not in values:
            raise ValueError('publication.named_destination_required')
        return _named(definition,values,reference=InputRef('reference'))
    entrances = {**definition.entrances,'product':OutputRef('render','product')}
    inputs = {**definition.inputs,'product':replace(BY_ID['command.product.render'].outputs['product'],required=False)}
    definition = replace(definition,inputs=inputs,entrances=entrances)
    return _named(definition,values,reference=OutputRef('save','reference'))


def history(definition, values, parameters, record, catalog=None):
    if 'query' not in values:
        return definition
    select = Call('select','command.observations.select',{
        'dataset':OutputRef('merge','dataset'),'query':InputRef('query')})
    validate = replace(definition.body.steps[-1],inputs={'dataset':OutputRef('select','dataset')})
    return replace(definition,body=replace(definition.body,
        steps=(*definition.body.steps[:-1],select,validate)))
