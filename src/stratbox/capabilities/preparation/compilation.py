"""Dependency closure and domain-neutral lowering into one physical handoff."""
from dataclasses import replace
from collections.abc import Mapping
from ..model import *
from ..model.contracts import field
from ..model.domains import SeriesSpec, CalculationSpec
from ..catalog import standard_catalog, DomainCatalog, load_domains
from ..plan import *
from .requests import InvocationRequest

_MISSING = object()


def _target_id(target):
    return target if isinstance(target, str) else getattr(target, 'id', None)


def _refs(value):
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


class Compiler:
    def __init__(self, catalog, domains, build_identity):
        self.catalog, self.domains, self.build_identity = catalog, domains, build_identity
        self.tasks, self.scopes, self.ports = [], [], {}
        self.stack = []

    def resolve(self, value, inputs, parameters, results, target):
        if isinstance(value, InputRef):
            result = inputs.get(value.name, _MISSING)
            if result is not _MISSING and value.path:
                if isinstance(result, ValueRef): return replace(result,path='.'.join(filter(None,(result.path,value.path))))
                return field(result,value.path)
            return result
        if isinstance(value, ParameterRef):
            result = parameters.get(value.name, _MISSING)
            return field(result,value.path) if result is not _MISSING and value.path else result
        if isinstance(value, TargetRef): return target
        if isinstance(value, OutputRef):
            if value.step not in results: raise ValueError('graph.forward_or_unknown_reference:' + value.step)
            if value.port not in results[value.step]: raise ValueError('graph.unknown_output:' + value.port)
            result=results[value.step][value.port]
            if value.path:
                return replace(result,path='.'.join(filter(None,(result.path,value.path)))) if isinstance(result,ValueRef) else field(result,value.path)
            return result
        if isinstance(value, Condition):
            return replace(value,value=self.resolve(value.value,inputs,parameters,results,target))
        if isinstance(value, Mapping):
            values={k:self.resolve(v,inputs,parameters,results,target) for k,v in value.items()}
            return {k:v for k,v in values.items() if v is not _MISSING}
        if isinstance(value, tuple): return tuple(self.resolve(v,inputs,parameters,results,target) for v in value)
        return value

    def bind(self, definition, target, parameters):
        record = self.domains.get(_target_id(target)) if target is not None else None
        spec = getattr(record,'commands',{}).get(definition.id) if record is not None else None
        if spec:
            spec.applicability.assess({'source_id':_target_id(target),'format':parameters.get('format')})
            method,settings=spec.method,spec.settings
            providers=definition.required_providers | spec.applicability.required_providers
        else:
            if definition.specification_required:
                raise ValueError('command.specification_required:' + definition.id)
            method,settings=definition.method,getattr(record,'settings',None)
            providers=definition.required_providers
        if method is None: raise ValueError('command.method_required:' + definition.id)
        ins,outs=dict(definition.inputs),dict(definition.outputs)
        requirements=()
        if isinstance(record,SeriesSpec) and definition.id in {'command.table.extract','command.table.interpret','command.observations.validate','command.observations.align'}:
            permitted={record.id}
            publication=record.publication
            for key in ('id','series_id'):
                v=getattr(publication,key,None)
                if v: permitted.add(v)
            req=SourceRequirement(frozenset(permitted),parameters.get('issue_id'), 'identified')
            # Physical evidence retains its material source; semantic outputs additionally establish table membership.
            ins={name:replace(port,source=req) if name in {'physical','tables','dataset'} else port for name,port in ins.items()}
            outs={name:replace(port,source=SourceRequirement(frozenset({record.id}),parameters.get('issue_id'),'identified')) if name=='dataset' else port for name,port in outs.items()}
            requirements=(req,)
        effective={**definition.parameters,**parameters}
        if target is not None: effective.setdefault('source_id',_target_id(target))
        for name in definition.required_parameters:
            if name not in effective: raise ValueError('command.parameter_required:' + name)
        return BoundCommand(definition.id,method,settings,ins,outs,effective,definition.resources,definition.effects,
                            providers,definition.reuse,requirements,definition.acceptance)

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
        parameters={**definition.parameters,**parameters}
        if selected is None: selected=tuple(definition.outputs)
        if not set(selected)<=definition.outputs.keys(): raise ValueError('invocation.unknown_output')
        if isinstance(definition,CommandDefinition):
            bound=self.bind(definition,target,parameters)
            self.validate_inputs(bound.inputs,values)
            task=CommandTask(prefix,bound,values,tuple(sorted(_refs(values))),prefix,required=required)
            self.tasks.append(task)
            for name,port in bound.outputs.items(): self.ports[(prefix,name)]=port
            outputs={name:ValueRef(prefix,name) for name in selected}
            self.scopes.append(PreparedScope(prefix,identifier,'command',parent,outputs,{name:bound.outputs[name] for name in selected},bound.acceptance,(prefix,),required=required))
            return outputs
        self.stack.append(identifier)
        try:
            return self.graph(definition,values,parameters,target,selected,prefix,parent,required)
        finally: self.stack.pop()

    def graph(self, definition, values, parameters, target, selected, prefix, parent, required):
        body=definition.body
        steps={step.step_id:step for step in body.steps}
        results={}
        cut={}
        for name,reference in definition.entrances.items():
            if name in values:
                cut.setdefault(reference.step,{})[reference.port]=values[name]
        roots=set(body.required_checks)|set(body.required_effects)|set(body.required_completions)
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
            dependencies=_author_refs(getattr(step,'inputs',{})) | set(getattr(step,'depends_on',())) | _author_refs(getattr(step,'condition',None))
            if isinstance(step,MapCall): dependencies |= _author_refs(step.items)
            if isinstance(step,RepeatUntil): dependencies |= _author_refs(step.initial)
            if isinstance(step,CollectCall): dependencies |= _author_refs(step.items)
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
                dependencies=_author_refs(getattr(step,'inputs',{}))|set(getattr(step,'depends_on',()))|_author_refs(getattr(step,'condition',None))
                if isinstance(step,MapCall): dependencies|=_author_refs(step.items)
                if isinstance(step,RepeatUntil): dependencies|=_author_refs(step.initial)
                if isinstance(step,CollectCall): dependencies|=_author_refs(step.items)
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
                args=resolve(step.inputs);params={**parameters,**resolve(step.parameters)}
                child_target=resolve(step.target)
                # Determine only the output ports actually read or explicitly promised.
                used=set()
                for output in body.outputs.values():
                    if isinstance(output,OutputRef) and output.step==name: used.add(output.port)
                for candidate in body.steps:
                    def scan(v):
                        if isinstance(v,OutputRef) and v.step==name: used.add(v.port)
                        elif isinstance(v,Mapping):
                            for x in v.values(): scan(x)
                        elif isinstance(v,(tuple,list)):
                            for x in v: scan(x)
                    for attribute in ('inputs','items','initial','condition'): scan(getattr(candidate,attribute,None))
                if not used: used=set(child.outputs)
                results[name]=self.compile(step.capability_id,args,params,child_target,tuple(used),path,prefix,required and step.required)
                extra=set()
                for dependency in step.depends_on:
                    extra |= set().union(*(_refs(v) for v in results.get(dependency,{}).values())) if results.get(dependency) else set()
                condition=resolve(step.condition) if step.condition else None
                for i in range(before,len(self.tasks)):
                    t=self.tasks[i]
                    if isinstance(t,CommandTask): self.tasks[i]=replace(t,deps=tuple(sorted(set(t.deps)|extra)),condition=condition or t.condition)
            elif isinstance(step,CollectCall):
                items=resolve(step.items)
                self.tasks.append(CollectTask(path,items,tuple(sorted(_refs(items))),prefix,step.required))
                results[name]={'items':ValueRef(path,'items')};self.ports[(path,'items')]=PortContract('result_collection',tuple)
            elif isinstance(step,MapCall):
                items=resolve(step.items);args=resolve(step.inputs)
                args[step.item_input]=TemplateInput(step.item_input)
                nested=Compiler(self.catalog,self.domains,self.build_identity)
                out=nested.compile(step.capability_id,args,{**parameters,**resolve(step.parameters)},resolve(step.target),None,'template')
                template=nested.finish(step.capability_id,out,target)
                self.tasks.append(MapTask(path,template,items,step.item_input,step.output_port,step.window,step.max_items,step.completion,tuple(sorted(_refs(items))),prefix,step.required))
                results[name]={'items':ValueRef(path,'items')};self.ports[(path,'items')]=PortContract('result_collection',tuple)
            elif isinstance(step,RepeatUntil):
                initial=resolve(step.initial)
                environment={**values,**resolve(step.inputs),step.state_input:TemplateInput(step.state_input)}
                nested=Compiler(self.catalog,self.domains,self.build_identity)
                temporary=OperationDefinition('operation.internal.iteration',body=step.body,outputs={step.state_output:PortContract('inference_state')})
                out=nested.graph(temporary,environment,parameters,target,(step.state_output,),'template',None,True)
                template=nested.finish(temporary.id,out,target)
                deps=_refs(initial)|_refs(resolve(step.inputs))
                self.tasks.append(RepeatTask(path,template,initial,step.state_input,step.state_output,step.stop,step.max_passes,tuple(sorted(deps)),prefix,step.required))
                results[name]={step.state_output:ValueRef(path,'state')};self.ports[(path,'state')]=PortContract('inference_state')
            else: raise TypeError('graph.unsupported_node')
        outputs={name:self.resolve(body.outputs[name],values,parameters,results,target) for name in selected}
        tasks=tuple(t.task_id for t in self.tasks[initial_tasks:] if t.required)
        children=tuple(s.scope_id for s in self.scopes[initial_scopes:] if s.parent_id==prefix and s.required)
        def roots_tasks(names):
            return tuple(sorted(set().union(*(_refs(v) for name in names for v in results.get(name,{}).values()))))
        self.scopes.append(PreparedScope(prefix,definition.id,definition.kind,parent,outputs,
            {name:definition.outputs[name] for name in selected},definition.acceptance,tasks,children,required,
            roots_tasks(body.required_checks),roots_tasks(body.required_effects)))
        return outputs

    def finish(self, identifier, outputs, target):
        identity=fingerprint({'definition':identifier,'tasks':tuple(self.tasks),'outputs':outputs,'build':self.build_identity,'target':target})
        return PreparedPlan(identifier,tuple(self.tasks),tuple(self.scopes),outputs,identity,self.build_identity,target)


def prepare(capability_id, *, inputs=None, parameters=None, target=None, outputs=None, catalog=None, domains=None, build_identity=None):
    from stratbox import __version__
    catalog=catalog or standard_catalog()
    domains=domains if domains is not None else load_domains() if target is not None else DomainCatalog({})
    if build_identity is None:
        from pathlib import Path
        from hashlib import sha256
        package=Path(__file__).parents[2]
        digest=sha256()
        for file in sorted(package.rglob('*.py')):
            digest.update(str(file.relative_to(package)).encode());digest.update(file.read_bytes())
        build_identity='stratbox:'+__version__+':'+digest.hexdigest()
    compiler=Compiler(catalog,domains,build_identity)
    result=compiler.compile(capability_id,dict(inputs or {}),dict(parameters or {}),target,outputs,'root')
    return compiler.finish(capability_id,result,target)


def prepare_request(request, **kwargs):
    if not isinstance(request,InvocationRequest): raise TypeError('invocation.request_required')
    return prepare(request.capability_id,inputs=request.inputs,parameters=request.parameters,target=request.target,outputs=request.outputs,**kwargs)
