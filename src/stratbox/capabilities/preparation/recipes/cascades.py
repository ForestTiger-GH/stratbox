"""Pure authoring-time graph recipes for cascades purposes."""

from dataclasses import replace

from ...model import Call, CollectCall, GraphBody, InputRef, OutputRef

from ...commands.standard import P

def _compose(definition, values, parameters, record, catalog, *, publish_release):
    members=values.get('members')
    if isinstance(members,(tuple,list)) and not members:
        if not parameters.get('allow_empty',False) or publish_release: raise ValueError('cascade.members_required')
        return replace(definition,body=GraphBody((),{'results':(),'outcomes':()}))
    if publish_release and isinstance(members,(tuple,list)) and members and all(hasattr(item,'rows') for item in members):
        members=tuple({'target':parameters.get('analysis_target',getattr(item,'source_id',None)), 'inputs':{'dataset':item,'destination':values.get('member_destination')}, 'parameters':{'product':True}} for item in members)
    if isinstance(members,(tuple,list)) and members and all(hasattr(item,'capability_id') or isinstance(item,dict) or hasattr(item,'items') and 'target' in item for item in members):
        from ..requests import InvocationRequest
        steps=[];outputs=[];required=[];optional=[]
        for ordinal,item in enumerate(members):
            if isinstance(item,InvocationRequest):
                capability=item.capability_id;args=item.inputs;params=item.parameters;chosen=item.target;is_required=True
            else:
                capability=item.get('capability_id','scenario.series.refresh' if (not publish_release) else 'scenario.analysis.prepare')
                args=item.get('inputs',{});params=item.get('parameters',{});chosen=item.get('target');is_required=item.get('required',True)
            if publish_release:
                params={**params,'product':True}
                if 'destination' not in args and 'member_destination' in values: args={**args,'destination':values['member_destination']}
            if catalog.get(capability).kind!='scenario': raise ValueError('cascade.scenario_required')
            name='member'+str(ordinal)
            steps.append(Call(name,capability,args,params,target=chosen,required=is_required))
            outputs.append(OutputRef(name,'reference' if publish_release else params.get('result_port','dataset')))
            if is_required: required.append(name)
            else: optional.append(ordinal)
        steps.append(CollectCall('results',tuple(outputs),optional_items=frozenset(optional),
            min_items=0 if parameters.get('allow_empty',False) and (not publish_release) else 1))
        result={'results':OutputRef('results','items'),'outcomes':OutputRef('results','outcomes')}
        ports={'results':P('result_collection',tuple),'outcomes':P('unit_outcomes',tuple)}
        if publish_release:
            steps.append(Call('release','scenario.release.publish',{'members':InputRef('release_members') if 'release_members' in values else OutputRef('results','items'),'expected_token':InputRef('expected_token')}))
            result['receipt']=OutputRef('release','receipt');ports['receipt']=P('publication_receipt');result['manifest']=OutputRef('release','manifest');ports['manifest']=P('release_manifest');required.append('release')
        return replace(definition,inputs={**definition.inputs,'release_members':P('accepted_members',tuple,required=False),'member_destination':P('destination',required=False),'expected_token':P('state_token',required=False)},outputs=ports,body=GraphBody(tuple(steps),result,required_completions=tuple(required)))
    return definition

def sources_refresh(definition, values, parameters, record, catalog=None):
    return _compose(definition, values, parameters, record, catalog, publish_release=False)

def analysis_release(definition, values, parameters, record, catalog=None):
    return _compose(definition, values, parameters, record, catalog, publish_release=True)
