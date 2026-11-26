"""Dependency closure and domain-neutral lowering into one physical handoff."""
from dataclasses import replace, dataclass
from collections.abc import Mapping
from ..model import *
from ..model.contracts import field
from ..model.domains import SeriesSpec, CalculationSpec
from ..catalog import standard_catalog, DomainCatalog, load_domains
from ..plan import *
from .requests import InvocationRequest

_MISSING = object()

@dataclass(frozen=True)
class GuardedValue:
    value: object
    guards: tuple[OutputGuard, ...]


def _unwrap(value):
    if isinstance(value,GuardedValue): return _unwrap(value.value)
    if isinstance(value,Condition): return replace(value,value=_unwrap(value.value))
    if isinstance(value,Mapping): return {k:_unwrap(v) for k,v in value.items()}
    if isinstance(value,tuple): return tuple(_unwrap(v) for v in value)
    return value


def _guards(value):
    if isinstance(value,GuardedValue): return set(value.guards)|_guards(value.value)
    if isinstance(value,Condition): return _guards(value.value)
    if isinstance(value,Mapping): return set().union(*(_guards(v) for v in value.values())) if value else set()
    if isinstance(value,tuple): return set().union(*(_guards(v) for v in value)) if value else set()
    return set()


def _path(value,path):
    if isinstance(value,GuardedValue): return GuardedValue(_path(value.value,path),value.guards)
    if isinstance(value,ValueRef): return replace(value,path='.'.join(filter(None,(value.path,path))))
    return field(value,path)



def _target_id(target):
    return target if isinstance(target, str) else getattr(target, 'id', None)


def _record(domains, target):
    if target is None: return None
    kind={'SeriesTarget':'series','CalculationTarget':'calculation','ProductTarget':'product','FeedTarget':'feed'}.get(type(target).__name__)
    return domains.get(_target_id(target), kind=kind)


def _refs(value):
    if isinstance(value,GuardedValue): return _refs(value.value)
    if isinstance(value, ValueRef): return {value.task_id}
    if isinstance(value, Mapping): return set().union(*(_refs(v) for v in value.values())) if value else set()
    if isinstance(value, (tuple,list)): return set().union(*(_refs(v) for v in value)) if value else set()
    if isinstance(value, Condition): return _refs(value.value)
    return set()


def _author_refs(value):
    if isinstance(value, OutputRef): return {value.step}
    if isinstance(value, Mapping): return set().union(*(_author_refs(v) for v in value.values())) if value else set()
    if isinstance(value, (tuple,list)): return set().union(*(_author_refs(v) for v in value)) if value else set()
    if isinstance(value, Condition): return _author_refs(value.value)
    return set()


def _step_values(step):
    """Every expression-bearing field participates in dependency closure."""
    return tuple(getattr(step, name, None) for name in
                 ('inputs', 'parameters', 'condition', 'items', 'initial', 'selector'))


def _step_dependencies(step):
    return set(getattr(step, 'depends_on', ())).union(
        *(_author_refs(value) for value in _step_values(step)))


def _bounded_integer(parameters, name, ceiling, minimum, code):
    supplied = parameters.get(name, ceiling)
    if type(supplied) is not int or supplied < minimum:
        raise ValueError(code)
    return min(ceiling, supplied)


class Compiler:
    def __init__(self, catalog, domains, build_identity):
        self.catalog, self.domains, self.build_identity = catalog, domains, build_identity
        self.tasks, self.scopes, self.ports = [], [], {}
        self.stack = []

    def resolve(self, value, inputs, parameters, results, target):
        if isinstance(value, InputRef):
            result = inputs.get(value.name, _MISSING)
            if result is not _MISSING and value.path:
                return _path(result,value.path)
            return result
        if isinstance(value, ParameterRef):
            result = parameters.get(value.name, _MISSING)
            return _path(result,value.path) if result is not _MISSING and value.path else result
        if isinstance(value, TargetRef): return target
        if isinstance(value, OutputRef):
            if value.step not in results: raise ValueError('graph.forward_or_unknown_reference:' + value.step)
            if value.port not in results[value.step]: raise ValueError('graph.unknown_output:' + value.port)
            result=results[value.step][value.port]
            if value.path:
                return _path(result,value.path)
            return result
        if isinstance(value, Condition):
            return replace(value,value=self.resolve(value.value,inputs,parameters,results,target))
        if isinstance(value, Mapping):
            values={k:self.resolve(v,inputs,parameters,results,target) for k,v in value.items()}
            return {k:v for k,v in values.items() if v is not _MISSING}
        if isinstance(value, tuple): return tuple(self.resolve(v,inputs,parameters,results,target) for v in value)
        return value

    def bind(self, definition, target, parameters, values=None):
        record = _record(self.domains,target)
        spec = getattr(record,'commands',{}).get(definition.id) if record is not None else None
        owner=record
        if spec is None and isinstance(record,SeriesSpec):
            owner=record.publication
            spec=getattr(owner,'commands',{}).get(definition.id)
        if spec:
            source_id = None
            if isinstance(record, SeriesSpec):
                source_id = getattr(owner, 'id', getattr(owner, 'series_id', record.id))
            else:
                for value in (values or {}).values():
                    value = getattr(value, 'value', value)
                    source_id = getattr(value, 'source_id', None)
                    if source_id: break
            spec.applicability.assess({'source_id':source_id,'format':parameters.get('format')})
            method,settings=spec.method,spec.settings
            providers=definition.required_providers | spec.applicability.required_providers
            optional_providers=definition.optional_providers | spec.applicability.optional_providers
        else:
            if definition.specification_required:
                raise ValueError('command.specification_required:' + definition.id)
            method,settings=definition.method,getattr(record,'settings',None)
            providers=definition.required_providers
            optional_providers=definition.optional_providers
        if method is None: raise ValueError('command.method_required:' + definition.id)
        ins,outs=dict(definition.inputs),dict(definition.outputs)
        if spec and spec.applicability.source_ids and not isinstance(record, SeriesSpec):
            requirement = SourceRequirement(spec.applicability.source_ids)
            ins = {name:replace(port, source=requirement) if name in {'dataset', 'view'} else port
                   for name,port in ins.items()}
        requirements=()
        if isinstance(record,SeriesSpec) and definition.id in {'command.table.extract','command.table.interpret','command.observations.validate','command.observations.align','command.view.prepare','command.product.render'}:
            permitted={record.id}
            publication=record.publication
            for key in ('id','series_id'):
                v=getattr(publication,key,None)
                if v: permitted.add(v)
            req=SourceRequirement(frozenset(permitted),parameters.get('issue_id'), 'identified')
            # Physical evidence retains its material source; semantic outputs additionally establish table membership.
            ins={name:replace(port,source=replace(req,attribution='asserted') if name in {'physical','tables'} else req)
                 if name in {'physical','tables','dataset','view'} else port for name,port in ins.items()}
            outs={name:replace(port,source=SourceRequirement(frozenset({record.id}),parameters.get('issue_id'),'identified')) if name=='dataset' else port for name,port in outs.items()}
            requirements=(req,)
        effective={**definition.parameters,**parameters}
        if target is not None: effective.setdefault('source_id',_target_id(target))
        for name in definition.required_parameters:
            if name not in effective: raise ValueError('command.parameter_required:' + name)
        return BoundCommand(definition.id,method,settings,ins,outs,effective,definition.resources,definition.effects,
                            providers,definition.reuse,requirements,definition.acceptance,
                            optional_providers=optional_providers-providers,target=target)

    def validate_inputs(self, contracts, values):
        unknown=set(values)-contracts.keys()
        if unknown: raise ValueError('invocation.unknown_input:' + sorted(unknown)[0])
        for name,contract in contracts.items():
            if name not in values:
                if contract.required: raise ValueError('invocation.input_required:' + name)
                continue
            value=values[name]
            if isinstance(value,ValueRef):
                producer=self.ports.get((value.task_id,value.port))
                if not value.path and producer is not None and not (replace(contract,source=None) if contract.source and producer.source is None else contract).compatible_with(producer):
                    raise TypeError('graph.port_mismatch:' + name)
            elif not isinstance(value,TemplateInput): contract.validate(value)

    def compile(self, identifier, values, parameters, target, selected, prefix, parent=None, required=True):
        if identifier in self.stack: raise ValueError('graph.definition_cycle:' + identifier)
        definition=self.catalog.get(identifier)
        from .recipes import resolve_recipe
        record=_record(self.domains,target)
        definition=resolve_recipe(definition,_unwrap(values),_unwrap(parameters),record,self.catalog)
        parameters={**definition.parameters,**parameters}
        if selected is None: selected=tuple(definition.outputs)
        if not set(selected)<=definition.outputs.keys(): raise ValueError('invocation.unknown_output')
        requested=tuple(selected)
        acceptance_outputs=set(definition.acceptance.coherent_outputs)
        for predicate in definition.acceptance.predicates:
            first=predicate.path.split('.',1)[0]
            acceptance_outputs.update((first,) if first in definition.outputs else definition.outputs)
        selected=tuple(dict.fromkeys((*selected,*sorted(acceptance_outputs))))
        if isinstance(definition,CommandDefinition):
            bound=self.bind(definition,target,_unwrap(parameters),_unwrap(values))
            self.validate_inputs(bound.inputs,_unwrap(values))
            guards=tuple(sorted(_guards(values)|_guards(parameters),key=lambda g:(g.scope_id,g.port)))
            task=CommandTask(prefix,bound,_unwrap(values),tuple(sorted(_refs(values)|_refs(parameters))),prefix,required=required,guards=guards)
            self.tasks.append(task)
            for name,port in bound.outputs.items(): self.ports[(prefix,name)]=port
            outputs={name:ValueRef(prefix,name) for name in selected}
            self.scopes.append(PreparedScope(prefix,identifier,'command',parent,outputs,{name:bound.outputs[name] for name in selected},bound.acceptance,(prefix,),required=required))
            return {name:outputs[name] for name in requested}
        unknown=set(values)-set(definition.inputs)-set(definition.entrances)
        if unknown: raise ValueError('invocation.unknown_input:'+sorted(unknown)[0])
        supplied={name:value for name,value in values.items() if name in definition.inputs}
        contracts={name:replace(definition.inputs[name],required=False) for name in supplied}
        if isinstance(record,SeriesSpec):
            permitted={record.id}
            for name in ('id','series_id'):
                identity=getattr(record.publication,name,None)
                if identity: permitted.add(identity)
            for name in {'material','physical','tables','dataset','view'} & contracts.keys():
                contracts[name]=replace(contracts[name],source=SourceRequirement(frozenset(permitted),
                    parameters.get('issue_id'),'identified' if name in {'dataset','view'} else 'asserted'))
        self.validate_inputs(contracts,_unwrap(supplied))
        input_guards=tuple(InputGuard(_unwrap(value),contracts[name]) for name,value in supplied.items())
        first_task=len(self.tasks)
        self.stack.append(identifier)
        try:
            outputs=self.graph(definition,values,parameters,target,selected,prefix,parent,required)
            for index in range(first_task,len(self.tasks)):
                task=self.tasks[index]
                self.tasks[index]=replace(task,
                    deps=tuple(sorted(set(task.deps)|_refs(supplied))),
                    input_guards=(*task.input_guards,*input_guards))
            return {name:GuardedValue(_unwrap(outputs[name]),tuple(sorted(_guards(outputs[name])|{OutputGuard(prefix,name)},key=lambda g:(g.scope_id,g.port)))) for name in requested}
        finally: self.stack.pop()

    def graph(self, definition, values, parameters, target, selected, prefix, parent, required):
        body=definition.body
        steps={step.step_id:step for step in body.steps}
        results={}
        cut={}
        for name,reference in definition.entrances.items():
            if name in values:
                if name in definition.inputs and not isinstance(values[name],(ValueRef,TemplateInput)):
                    definition.inputs[name].validate(_unwrap(values[name]))
                cut.setdefault(reference.step,{})[reference.port]=values[name]
        checks=set(body.required_checks)|set(definition.acceptance.required_checks)
        effects=set(body.required_effects)|set(definition.acceptance.required_effects)
        roots=checks|effects|set(body.required_completions)
        for name in selected: roots |= _author_refs(body.outputs[name])
        needed=set()
        active=set()
        def visit(name):
            if name in cut: return
            if name in active: raise ValueError('graph.cycle')
            if name in needed: return
            if name not in steps: raise ValueError('graph.unknown_step:'+name)
            active.add(name)
            step=steps[name]
            dependencies=_step_dependencies(step)
            for dep in dependencies: visit(dep)
            active.remove(name);needed.add(name)
        for name in roots: visit(name)
        # Prepare in topological order, independent of authoring order.
        ordered=[]; remaining=set(needed)
        while remaining:
            progress=False
            for step in body.steps:
                name=step.step_id
                if name not in remaining: continue
                dependencies=_step_dependencies(step)
                if dependencies <= set(ordered)|set(cut): ordered.append(name);remaining.remove(name);progress=True
            if not progress: raise ValueError('graph.cycle')
        results.update(cut)
        initial_tasks=len(self.tasks); initial_scopes=len(self.scopes)
        for name in ordered:
            step=steps[name]; path=prefix+'/'+name
            resolve=lambda v:self.resolve(v,values,parameters,results,target)
            if isinstance(step,Call):
                child=self.catalog.get(step.capability_id)
                allowed={'operation':{'command','operation'},'scenario':{'operation','scenario'},'cascade':{'scenario'}}[definition.kind]
                if child.kind not in allowed: raise ValueError('graph.invalid_kind:'+definition.kind+'>'+child.kind)
                before=len(self.tasks)
                first_scope=len(self.scopes)
                args=resolve(step.inputs);params={**parameters,**resolve(step.parameters)}
                child_target=resolve(step.target)
                # Determine only the output ports actually read or explicitly promised.
                used=set()
                for output in (body.outputs[key] for key in selected):
                    if isinstance(output,OutputRef) and output.step==name: used.add(output.port)
                for candidate in body.steps:
                    if candidate.step_id not in needed: continue
                    def scan(v):
                        if isinstance(v,OutputRef) and v.step==name: used.add(v.port)
                        elif isinstance(v,Condition): scan(v.value)
                        elif isinstance(v,Mapping):
                            for x in v.values(): scan(x)
                        elif isinstance(v,(tuple,list)):
                            for x in v: scan(x)
                    for expression in _step_values(candidate): scan(expression)
                if not used: used=set(child.outputs)
                results[name]=self.compile(step.capability_id,args,params,child_target,tuple(used),path,prefix,required and step.required)
                extra=_refs(resolve(step.condition)) if step.condition else set()
                for dependency in step.depends_on:
                    extra |= set().union(*(_refs(v) for v in results.get(dependency,{}).values())) if results.get(dependency) else set()
                condition=resolve(step.condition) if step.condition else None
                for index in range(first_scope,len(self.scopes)):
                    scope=self.scopes[index]
                    inherited=tuple(c for group in (condition,scope.condition)
                        for c in (group if isinstance(group,tuple) else (group,)) if c is not None)
                    self.scopes[index]=replace(scope,required_checks=tuple(sorted(set(scope.required_checks)|extra)),
                        condition=_unwrap(inherited) or None)
                for i in range(before,len(self.tasks)):
                    t=self.tasks[i]
                    inherited=tuple(c for group in (condition,getattr(t,'condition',None)) for c in (group if isinstance(group,tuple) else (group,)) if c is not None)
                    self.tasks[i]=replace(t,deps=tuple(sorted(set(t.deps)|extra)),condition=_unwrap(inherited) or None,
                        guards=tuple(sorted(set(t.guards)|_guards(condition),key=lambda g:(g.scope_id,g.port))))
            elif isinstance(step,CollectCall):
                items=resolve(step.items)
                mandatory=tuple(value for index,value in enumerate(items) if index not in step.optional_items)
                optional_guards={index:tuple(sorted(_guards(items[index]),key=lambda g:(g.scope_id,g.port))) for index in step.optional_items}
                self.tasks.append(CollectTask(path,_unwrap(items),tuple(sorted(_refs(items)|_refs(resolve(step.condition)))),prefix,required and step.required,
                    _unwrap(resolve(step.condition)),tuple(sorted(_guards(mandatory),key=lambda g:(g.scope_id,g.port))),
                    optional_items=step.optional_items,min_items=step.min_items,item_guards=optional_guards))
                results[name]={'items':ValueRef(path,'items'),'outcomes':ValueRef(path,'outcomes')}
                self.ports[(path,'items')]=PortContract('result_collection',tuple)
                self.ports[(path,'outcomes')]=PortContract('unit_outcomes',tuple)
            elif isinstance(step,MapCall):
                allowed={'operation':{'command','operation'},'scenario':{'operation','scenario'},'cascade':{'scenario'}}[definition.kind]
                if self.catalog.get(step.capability_id).kind not in allowed: raise ValueError('graph.invalid_map_kind')
                items=resolve(step.items);args=resolve(step.inputs)
                args[step.item_input]=TemplateInput(step.item_input)
                nested=Compiler(self.catalog,self.domains,self.build_identity)
                out=nested.compile(step.capability_id,args,{**parameters,**resolve(step.parameters)},resolve(step.target),None,'template')
                template=nested.finish(step.capability_id,out,target)
                if step.output_port not in template.outputs: raise ValueError('graph.map_output_required:'+step.output_port)
                window=_bounded_integer(parameters,'window',step.window,1,'graph.invalid_map_limits')
                max_items=_bounded_integer(parameters,'max_items',step.max_items,0,'graph.invalid_map_limits')
                completion=parameters.get('completion',step.completion)
                if window<1 or max_items<0 or completion not in {'all_selected','eligible_subset'}:
                    raise ValueError('graph.invalid_map_limits')
                self.tasks.append(MapTask(path,template,_unwrap(items),step.item_input,step.output_port,window,max_items,completion,tuple(sorted(_refs(items)|_refs(resolve(step.inputs))|_refs(resolve(step.condition)))),prefix,required and step.required,_unwrap(resolve(step.condition)),tuple(sorted(_guards(items),key=lambda g:(g.scope_id,g.port)))))
                results[name]={'items':ValueRef(path,'items'),'outcomes':ValueRef(path,'outcomes')};self.ports[(path,'items')]=PortContract('result_collection',tuple);self.ports[(path,'outcomes')]=PortContract('unit_outcomes',tuple)
            elif isinstance(step,DispatchCall):
                selector=resolve(step.selector)
                alternatives={}
                for fmt,capability in step.alternatives.items():
                    nested=Compiler(self.catalog,self.domains,self.build_identity)
                    args={**resolve(step.inputs),step.input_name:TemplateInput(step.input_name)}
                    try:
                        branch_parameters=({'format':fmt,'archive_depth':int(parameters.get('archive_depth',0))+(1 if fmt in {'zip','rar'} else 0)}
                            if step.selector_kind=='material_format' else {'acquisition_kind':fmt})
                        out=nested.compile(capability,args,{**parameters,**resolve(step.parameters),**branch_parameters},resolve(step.target),None,'template')
                    except ValueError as error:
                        if str(error).startswith('applicability.'): continue
                        raise
                    alternatives[fmt]=nested.finish(capability,out,target)
                if not alternatives: raise ValueError('recipe.no_supported_representation')
                self.tasks.append(DispatchTask(path,_unwrap(selector),freeze(alternatives),step.input_name,step.output_port,step.selector_kind,tuple(sorted(_refs(selector)|_refs(resolve(step.inputs)))),prefix,required and step.required,_unwrap(resolve(step.condition)),tuple(sorted(_guards(selector),key=lambda g:(g.scope_id,g.port)))))
                results[name]={step.output_port:ValueRef(path,step.output_port)}
                self.ports[(path,step.output_port)]=self.catalog.get(next(iter(step.alternatives.values()))).outputs[step.output_port]
            elif isinstance(step,RepeatUntil):
                initial=resolve(step.initial)
                environment={**values,**resolve(step.inputs),step.state_input:TemplateInput(step.state_input)}
                nested=Compiler(self.catalog,self.domains,self.build_identity)
                temporary=OperationDefinition('operation.internal.iteration',body=step.body,outputs={step.state_output:PortContract('inference_state')})
                out=nested.graph(temporary,environment,parameters,target,(step.state_output,),'template',None,True)
                template=nested.finish(temporary.id,out,target)
                deps=_refs(initial)|_refs(resolve(step.inputs))
                limit=_bounded_integer(parameters,'max_passes',step.max_passes,1,'graph.invalid_repeat_limit')
                if limit<1: raise ValueError('graph.invalid_repeat_limit')
                self.tasks.append(RepeatTask(path,template,_unwrap(initial),step.state_input,step.state_output,step.stop,limit,tuple(sorted(deps|_refs(resolve(step.condition)))),prefix,required and step.required,_unwrap(resolve(step.condition)),tuple(sorted(_guards(initial),key=lambda g:(g.scope_id,g.port)))))
                results[name]={step.state_output:ValueRef(path,'state')};self.ports[(path,'state')]=PortContract('inference_state')
            else: raise TypeError('graph.unsupported_node')
        outputs={name:self.resolve(body.outputs[name],values,parameters,results,target) for name in selected}
        tasks=tuple(t.task_id for t in self.tasks[initial_tasks:] if t.required)
        children=tuple(s.scope_id for s in self.scopes[initial_scopes:] if s.parent_id==prefix and s.required)
        def roots_tasks(names):
            return tuple(sorted(set().union(*(_refs(v) for name in names for v in results.get(name,{}).values()))))
        self.scopes.append(PreparedScope(prefix,definition.id,definition.kind,parent,_unwrap(outputs),
            {name:definition.outputs[name] for name in selected},definition.acceptance,tasks,children,required,
            roots_tasks(checks),roots_tasks(effects)))
        return outputs

    def finish(self, identifier, outputs, target):
        outputs=_unwrap(outputs)
        identity=fingerprint({'definition':identifier,'tasks':tuple(self.tasks),'outputs':outputs,'build':self.build_identity,'target':target})
        return PreparedPlan(identifier,tuple(self.tasks),tuple(self.scopes),outputs,identity,self.build_identity,target)


def prepare(capability_id, *, inputs=None, parameters=None, target=None, outputs=None, catalog=None, domains=None, build_identity=None):
    catalog=catalog or standard_catalog()
    if domains is None:
        identifiers=[_target_id(target)]
        for item in (inputs or {}).get('members',()):
            identifiers.append(_target_id(item.get('target') if isinstance(item,Mapping) else getattr(item,'target',getattr(item,'source_id',None))))
        # Target identifiers are opaque; their spelling does not select a
        # publisher or execution route. The explicit manifest owns discovery.
        domains=load_domains() if any(identifiers) else DomainCatalog({})
    if build_identity is None:
        from stratbox.shared.build import implementation_identity
        build_identity=implementation_identity()
    compiler=Compiler(catalog,domains,build_identity)
    result=compiler.compile(capability_id,dict(inputs or {}),dict(parameters or {}),target,outputs,'root')
    return compiler.finish(capability_id,result,target)


def prepare_request(request, **kwargs):
    if not isinstance(request,InvocationRequest): raise TypeError('invocation.request_required')
    return prepare(request.capability_id,inputs=request.inputs,parameters=request.parameters,target=request.target,outputs=request.outputs,**kwargs)
